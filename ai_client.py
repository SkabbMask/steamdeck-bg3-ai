import base64
from google import genai
from google.genai import types
import logging
import re
import json

log = logging.getLogger(__name__)

SYSTEM_PROMPT_ACTION = """You are an AI agent playing Baldur's Gate 3.
You receive a screenshot of the game and must decide the single best action to take.

Rules:
- Respond ONLY with a JSON object, nothing else.
- For mouse actions: {"action": "click", "button": "left", "x": 123, "y": 456, "reason": "short explanation"}
- For keyboard actions: {"action": "key", "key": "space", "reason": "short explanation"}
- For waiting: {"action": "wait", "reason": "explanation"}
- x and y are pixel integers based on 1024x640 resolution. Never use lists or floats.
- button can be: "left" (move/select/interact), "right" (context menu)
- Keep the "reason" field short — maximum 10 words.
- key can be:
    "space" (end turn in combat / skip / take all from container)
    "Escape" (close menus / cancel / exit turn-based mode)
    "shift+space" (enter or leave turn-based mode)
    "c" (toggle sneak)
    "z" (jump)
    "g" (toggle group mode)
    "i" (open inventory)
    "m" (open map)
    "j" (open journal)
    "F1" through "F4" (select party member 1-4)
    "Tab" (party overview)

Gameplay:
- You control the character that is typically in the middle of the screen.
- To move, left click on the ground at your destination, not on the character itself.
- If you see turn-based mode (as indicated by text at bottom right "Exit TB mode") active but no enemies are visible, press shift+space to exit it.
- If you see a dialogue, click the most interesting or story-advancing option.
- If you see a context menu after right-clicking, click the most relevant action.
- If combat is active and your turn is done, press space to end turn.
- If a menu or window is open that you want to close, press Escape.
- If you are unsure, explore by left clicking somewhere in the world.

IMPORTANT:
- ONLY use wait if the screen is entirely a cinematic with absolutely NO game UI visible.
- If you can see ANY of these: action bar, character portrait, health bar, inventory icon, or any HUD elements — the game is NOT in cinematic or cutscene and you MUST take an action. Do NOT wait.
- If you have been waiting and nothing has changed, press space or Escape to skip.
- The game is ALWAYS interactive when the UI is visible, even if dramatic things are happening on screen.
- Do NOT exit the game!
- ONLY ANSWER WITH THE JSON, NO OTHER TEXT! THAT WILL RESULT IN AN ERROR!

Character creation:
- Choose a class that you want to play and adapt skills.
- Make creative choices for your appearance.
- If you see an on-screen keyboard, click individual keys to type.
- Once satisfied with your choices, click whatever advances to play.
"""

SYSTEM_PROMPT_SUMMARY = """You are tracking the progress of an AI playing Baldur's Gate 3.
Create a concise summary (max 200 words) combining the existing summary with the new actions.
Focus on: where the player is, what they have done, and what they were trying to do last.
If the player seem stuck in a loop of the same kind of action for a long time without any results - make hints to switching tactics.
You have not found a bug in the game!
DO NOT use any special characters or emojis!
You receive a screenshot of where the player currently are for context

Respond with only the updated summary, no preamble.
"""

SUMMARY_REQUEST="""
Existing summary:
{previous_summary}

New actions:
{new_actions}
"""

class AIClient:
    def __init__(self, api_key: str, action_model: str, summary_model: str):
        self.client = genai.Client(api_key=api_key)
        self.action_model = action_model
        self.summary_model = summary_model

    def ask_model_summary(self, image_bytes: bytes, previous_summary: str, new_actions: list) -> str:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        
        prompt = SUMMARY_REQUEST.format(
            previous_summary=previous_summary or "None yet.",
            new_actions="\n".join(new_actions),
        )

        response = self.client.models.generate_content(
            model=self.summary_model,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT_SUMMARY,
            ),
            contents=[
                types.Part.from_bytes(
                    data=b64,
                    mime_type='image/jpeg',
                ),
                prompt,
            ]
        )
        return response.text.strip()

    def ask_model_action(self, image_bytes: bytes, summary: str, recent_actions: list, nudge: bool = False) -> dict:
        b64 = base64.b64encode(image_bytes).decode("utf-8")

        context_parts = []
        if summary:
            context_parts.append(f"Progress so far: {summary}")
        if recent_actions:
            context_parts.append("Last actions:\n" + "\n".join(recent_actions))
        if nudge:
            context_parts.append(
                "WARNING: You have been clicking the same spot repeatedly with no result. "
                "Try a completely different action or location."
            )
        context = "\n\n".join(context_parts) + "\n\nDecide the single best action to take."

        response = self.client.models.generate_content(
            model=self.action_model,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT_ACTION,
            ),
            contents=[
              types.Part.from_bytes(
                data=b64,
                mime_type='image/jpeg',
              ),
              context,
            ]
        )

        raw = response.text.strip()
        log.debug(f"Raw model response: {raw}")

        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON found in response: {raw}")
        return json.loads(match.group())

