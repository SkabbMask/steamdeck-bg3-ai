# steamdeck-bg3-ai
An LLM that autonomously plays Baldur's Gate 3 on a Steam Deck using a multimodal model. The agent captures screenshots over SSH, sends them to the LLM for analysis, and executes mouse/keyboard actions via xdotool.

## How it works

```
PC                                           Steam Deck
----------                                   ----------
1. SSH in → capture screenshot               →   scrot saves /tmp/bg3_screenshot.png
2. Resize + send to LLM API
3. Receive action JSON
4. SSH in → execute xdotool                  →   mouse click / keypress in BG3
5. Write overlay (for stream) via SFTP       →   /tmp/bg3_overlay.txt (for OBS)
6. Save logs locally
```

## Requirements

### PC (runs the agent)
- Python 3.12+
- LLM API key

### Steam Deck (runs the game)
- BG3 installed via Steam
- Desktop Mode accessible
- Connected to the same local network as your PC

---

## Steam Deck Setup

### 1. Switch to Desktop Mode
Press the **Steam button** → **Power** → **Switch to Desktop**

### 2. Open a terminal
Click the application launcher (bottom-left) → search for **Konsole**

### 3. Set a password for the deck user
```bash
passwd
```
Choose a password — you'll need this for SSH.

### 4. Enable SSH
```bash
sudo systemctl enable sshd --now
```

### 5. Disable read-only filesystem
```bash
sudo steamos-readonly disable
```

### 6. Initialize pacman keyring
```bash
sudo pacman-key --init
sudo pacman-key --populate
```

### 7. Install required packages
```bash
sudo pacman -S xdotool scrot
```

### 8. Find the Deck's local IP address
```bash
ip addr show | grep 192.168
```
Note this IP — you'll need it for the `.env` file.

### 9. Test SSH from your PC
```powershell
ssh deck@<DECK_IP>
```
It should connect without errors.

---

## PC Setup

### 1. Install Python dependencies
```powershell
pip install anthropic paramiko pillow python-dotenv
```

### 2. Create a `.env` file
Create a file called `.env` in the project folder with:
```
STEAMDECK_HOST
STEAMDECK_USER
STEAMDECK_PASS
LOG_DIR=logs
GEMINI_API_KEY
```
---

## Running the Agent

### 1. Prepare the Steam Deck
- Make sure the Deck is in **Desktop Mode**
- Launch BG3 from the Steam icon in the taskbar
- Wait for BG3 to reach the main menu or be in-game

### 2. Start the agent on your PC
```powershell
python bg3_agent.py
```

The agent will:
1. Connect to the Deck via SSH
2. Detect the X11 display auth automatically
3. Start capturing screenshots and sending them to LLM
4. Execute actions and log everything to the `logs/`(or whatever you specified in the .env file) folder

### 3. Stop the agent
Press `Ctrl+C` at any time. State is saved after every step so you can resume later by running the script again.

### 4. Start fresh
Delete `logs` to reset memory and start from step 1.

---

## OBS Streaming Setup (optional)

To stream the agent playing BG3 on Twitch with a live overlay:

### On the Steam Deck
```bash
sudo pacman -S obs-studio
```
A text containing the last action, step number, and the current summary can be found at /tmp/bg3_overlay.txt on the Steam Deck.

---

## Configuration

Key settings in `config.py`:

| `LOOP_INTERVAL` | `10` | Seconds between actions |
| `MAX_LOOPS` | `99999` | Max steps before stopping |
| `SUMMARY_EVERY` | `50` | Steps between memory summarization |
| `RECENT_ACTIONS_KEEP` | `10` | Recent actions always included in prompt |
| `LOOP_DETECT_WINDOW` | `5` | Identical clicks before nudging model |
| `MAX_CONSECUTIVE_WAIT` | `3` | Waits in a row before auto-pressing Escape (example: for cut-scenes) |


---

## Logs

Every step is saved to `logs/step_XXXX/`:
- `screenshot.jpg` — what the model saw
- `action.json` — what action was taken and the current summary

Additional files:
- `logs/agent.log` — full run log
- `logs/summary.txt` — latest rolling summary
- `logs/state.json` — saved state for resuming
- `logs/latest.jpg` — most recent screenshot

---

## Troubleshooting

**SSH connection refused**
- Check `sudo systemctl status sshd` on the Deck
- Make sure you're on the same WiFi network

**scrot: Can't open X display**
- The Deck must be in Desktop Mode, not Gaming Mode
- Run `DISPLAY=:0 XAUTHORITY=$(ls /run/user/1000/xauth_*) scrot /tmp/test.png` to verify

**Clicks landing in wrong position**
- The agent assumes native Deck resolution of 1280x800
- If using an external monitor at a different resolution, update the scaling in `parse_coordinates()`
