from steamdeck_client import SteamdeckClient
from ai_client import AIClient
import config
import logging
import state
import utils
import time

config.LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_DIR / "agent.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

deck = SteamdeckClient(config.STEAMDECK_HOST, config.STEAMDECK_USER, config.STEAMDECK_PASSWORD, config.REMOTE_SCREENSHOT_PATH, config.LOCAL_SCREENSHOT_PATH, config.OVERLAY_REMOTE_PATH)
ai = AIClient(config.GEMINI_API_KEY, config.ACTION_MODEL, config.SUMMARY_MODEL)

def main():
    log.info("Starting BG3 agent...")

    summary, pending_actions, all_actions, last_step = state.load_state(config.STATE_FILE)
    last_screen_hash = ""
    start_step = last_step + 1
    consecutive_waits = 0

    if last_step > 0:
        log.info(f"Resuming from step {start_step}")

    for step in range(start_step, start_step + config.MAX_LOOPS):
        log.info(f"-- Step {step} ------------------")

        try:
            # 1. Screenshot
            log.info("Capturing screenshot...")
            image_bytes = deck.take_screenshot()
            log.info(f"Screenshot captured ({len(image_bytes)//1024} KB)")

            # 2. Resize
            resized_bytes = utils.resize_screenshot(image_bytes)
            log.info(f"Screenshot resized ({len(resized_bytes)//1024} KB)")

            # 3. Screen change detection
            changed, last_screen_hash = utils.screen_changed(resized_bytes, last_screen_hash)
            if not changed:
                log.info("Screen unchanged, skipping model call.")
                time.sleep(config.LOOP_INTERVAL)
                continue

            # 4. Loop detection
            nudge = utils.is_stuck(config.LOOP_DETECT_WINDOW, all_actions)
            if nudge:
                log.warning("Loop detected! Nudging model.")

            # 5. Build recent actions window
            recent_actions = all_actions[-config.RECENT_ACTIONS_KEEP:]

            # 6. Ask model for action
            log.info("Sending to model...")
            action = ai.ask_model_action(resized_bytes, summary, recent_actions, nudge)
            log.info(f"Action: {action}")

            # 7. Execute action
            if action.get("action") == "click" or action.get("action") == "left":
                x, y = utils.parse_coordinates(action)
                button = action.get("button", "left")
                log.info(f"Clicking {button} at ({x}, {y}) -- {action.get('reason', '')}")
                deck.execute_click(x, y, button)
                action_text = f"Step {step}: clicked {button} ({x}, {y}) - {action.get('reason', '')}"
                consecutive_waits = 0

            elif action.get("action") == "right":
                x, y = utils.parse_coordinates(action)
                button = action.get("button", "right")
                log.info(f"Clicking {button} at ({x}, {y}) -- {action.get('reason', '')}")
                deck.execute_click(x, y, button)
                action_text = f"Step {step}: clicked {button} ({x}, {y}) - {action.get('reason', '')}"
                consecutive_waits = 0

            elif action.get("action") == "wait":
                consecutive_waits += 1
                reason = action.get("reason", "")
                log.info(f"Waiting ({consecutive_waits}/{config.MAX_CONSECUTIVE_WAIT}) -- {reason}")
                action_text = f"Step {step}: waited - {reason}"

                if consecutive_waits >= config.MAX_CONSECUTIVE_WAIT:
                    log.warning(f"Too many consecutive waits, pressing Escape to skip")
                    deck.execute_key("Escape")
                    consecutive_waits = 0

            elif action.get("action") == "key":
                key = action.get("key", "Escape")
                log.info(f"Pressing key '{key}' -- {action.get('reason', '')}")
                deck.execute_key(key)
                action_text = f"Step {step}: pressed key '{key}' - {action.get('reason', '')}"
                consecutive_waits = 0

            else:
                log.warning(f"Unknown action type: {action}")
                action_text = f"Step {step}: unknown action - {action}"
                consecutive_waits = 0

            # 8. Record action
            all_actions.append(action_text)
            pending_actions.append(action_text)

            # 9. Save step log + write OBS overlay
            utils.save_step_log(config.LOG_DIR, step, resized_bytes, action, summary)
            deck.write_deck_overlay(step, action, summary)

            # 10. Rolling summary every SUMMARY_EVERY steps
            if len(pending_actions) >= config.SUMMARY_EVERY:
                log.info(f"-- Generating rolling summary at step {step}...")
                summary = ai.ask_model_summary(resized_bytes, summary, pending_actions)
                log.info(f"New summary: {summary}")
                with open(config.LOG_DIR / "summary.txt", "w") as f:
                    f.write(summary)
                pending_actions = []

            # 11. Save state after every step
            state.save_state(config.STATE_FILE, summary, pending_actions, all_actions, step)

        except Exception as e:
            log.error(f"Step {step} failed: {e}", exc_info=True)

        time.sleep(config.LOOP_INTERVAL)

    deck.close()
    log.info("Agent finished.")

if __name__ == "__main__":
    main()