import io
import hashlib
from PIL import Image
import logging
import json
from datetime import datetime

log = logging.getLogger(__name__)

def resize_screenshot(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    img = img.resize((1024, 640), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75)
    return buf.getvalue()


def screen_changed(new_bytes: bytes, last_hash: str) -> tuple:
    new_hash = hashlib.md5(new_bytes).hexdigest()
    return new_hash != last_hash, new_hash

def parse_coordinates(action: dict) -> tuple:
    x = action.get("x")
    y = action.get("y")

    if isinstance(x, list) and len(x) == 2 and y is None:
        x, y = int(x[0]), int(x[1])
    else:
        if isinstance(x, list):
            x = x[0]
        if isinstance(y, list):
            y = y[0]

        if x is None or y is None:
            raise ValueError(f"Cannot parse coordinates from action: {action}")

        x, y = float(x), float(y)

        # Handle normalized 0-1 coordinates
        if 0 <= x <= 1 and 0 <= y <= 1:
            log.warning("Normalized coordinates detected, converting to pixels")
            return int(x * 1280), int(y * 800)

    x = int(x * 1280 / 1024)
    y = int(y * 800 / 640)
    return x, y

def wrap_text(text: str, width: int = 200) -> str:
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = current + " " + word if current else word
    if current:
        lines.append(current)
    return "\n".join(lines)

def save_step_log(log_dir: str, step: int, image_bytes: bytes, action: dict, summary: str):
    step_dir = log_dir / f"step_{step:04d}"
    step_dir.mkdir(exist_ok=True)

    with open(step_dir / "screenshot.jpg", "wb") as f:
        f.write(image_bytes)

    with open(step_dir / "action.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "summary_at_step": summary,
        }, f, indent=2)

def is_stuck(loop_detect_window, all_actions: list) -> bool:
    click_actions = [a for a in all_actions if "clicked" in a]
    if len(click_actions) < loop_detect_window:
        return False
    last = click_actions[-loop_detect_window:]
    try:
        coords = [a.split("clicked ")[1].split(" -")[0] for a in last]
        return len(set(coords)) == 1
    except Exception:
        return False