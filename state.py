from datetime import datetime
import json
import logging

log = logging.getLogger(__name__)

def save_state(state_file_path: str, summary: str, pending_actions: list, all_actions: list, step: int):
    state = {
        "timestamp": datetime.now().isoformat(),
        "step": step,
        "summary": summary,
        "pending_actions": pending_actions,
        "all_actions": all_actions[-100:],
    }
    with open(state_file_path, "w") as f:
        json.dump(state, f, indent=2)


def load_state(state_file_path: str) -> tuple:
    if not state_file_path.exists():
        log.info("No saved state found, starting fresh.")
        return "", [], [], 0

    try:
        with open(state_file_path, "r") as f:
            state = json.load(f)
        summary = state.get("summary", "")
        pending_actions = state.get("pending_actions", [])
        all_actions = state.get("all_actions", [])
        last_step = state.get("step", 0)
        log.info(f"Loaded saved state from step {last_step}: {len(all_actions)} actions, summary length {len(summary)}")
        return summary, pending_actions, all_actions, last_step
    except Exception as e:
        log.warning(f"Failed to load saved state: {e} -- starting fresh.")
        return "", [], [], 0