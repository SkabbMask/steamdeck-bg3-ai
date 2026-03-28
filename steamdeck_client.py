import paramiko
import logging
from utils import wrap_text

log = logging.getLogger(__name__)

class SteamdeckClient:
    client: paramiko.SSHClient;
    xauth: str;
    remote_screenshot_path: str;
    local_screenshot_path: str;
    overlay_remote_path: str;
    
    def __init__(self, host: str, user: str, password: str, remote_screenshot_path: str, local_screenshot_path: str, overlay_remote_path: str):
        log.info(f"Connecting to Steam Deck at {host}")
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(host, username=user, password=password or None)
        self.xauth = self.get_xauth_path()
        self.remote_screenshot_path = remote_screenshot_path
        self.local_screenshot_path = local_screenshot_path
        self.overlay_remote_path = overlay_remote_path
        log.info("SSH connected.")

    def close(self):
        log.info("closing SSH.")
        self.client.close()

    def get_xauth_path(self) -> str:
        _, stdout, _ = self.client.exec_command("ls /run/user/1000/xauth_*")
        stdout.channel.recv_exit_status()
        path = stdout.read().decode().strip()
        if not path:
            raise RuntimeError("Could not find Xauthority file -- is the Deck in Desktop Mode?")
        log.info(f"Found Xauthority at: {path}")
        return path

    def take_screenshot(self) -> bytes:
        _, stdout, stderr = self.client.exec_command(
            f"DISPLAY=:0 XAUTHORITY={self.xauth} scrot -o {self.remote_screenshot_path}"
        )
        exit_status = stdout.channel.recv_exit_status()
        err = stderr.read().decode().strip()
        if err:
            log.warning(f"scrot stderr: {err}")
        if exit_status != 0:
            raise RuntimeError(f"scrot failed with exit status {exit_status}")
    
        sftp = self.client.open_sftp()
        sftp.get(self.remote_screenshot_path, str(self.local_screenshot_path))
        sftp.close()
    
        with open(self.local_screenshot_path, "rb") as f:
            return f.read()

    def execute_click(self, x: int, y: int, button: str = "left"):
        if button == "right":
            cmd = f"DISPLAY=:0 XAUTHORITY={self.xauth} xdotool mousemove {x} {y} click 3"
        else:
            cmd = f"DISPLAY=:0 XAUTHORITY={self.xauth} xdotool mousemove {x} {y} click 1"
    
        _, stdout, stderr = self.client.exec_command(cmd)
        stdout.channel.recv_exit_status()
        err = stderr.read().decode().strip()
        if err:
            log.warning(f"xdotool stderr: {err}")

    def execute_key(self, key: str):
        cmd = f"DISPLAY=:0 XAUTHORITY={self.xauth} xdotool key {key}"
        _, stdout, stderr = self.client.exec_command(cmd)
        stdout.channel.recv_exit_status()
        err = stderr.read().decode().strip()
        if err:
            log.warning(f"xdotool key stderr: {err}")

    def write_deck_overlay(self, step: int, action: dict, summary: str):
        action_type = action.get("action")
        if action_type == "click":
            action_str = f"{action.get('button', 'left')} click ({action.get('x')}, {action.get('y')})"
        elif action_type == "key":
            action_str = f"key: {action.get('key')}"
        elif action_type == "wait":
            action_str = "waiting"
        else:
            action_str = str(action_type)

        reason = action.get("reason", "")
        summary_text = summary if summary else "No summary yet."

        overlay = f"Step {step} | {action_str}\n{wrap_text(reason)}\n\n{wrap_text(summary_text)}"

        sftp = self.client.open_sftp()
        with sftp.open(self.overlay_remote_path, "w") as f:
            f.write(overlay)
        sftp.close()