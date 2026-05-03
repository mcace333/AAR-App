#!/usr/bin/env python3
"""
SM2 Screenshot & Discord-Logger Tool (Windows 11)
Waits for a global hotkey (Home/End/F7), takes 4 screenshots of the battle results screen,
opens a GUI for data entry, and copies formatted text to the clipboard.
"""

import os
import queue
import threading
import time
from datetime import datetime
from pathlib import Path

from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController, Key, KeyCode
import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------------------
# Configuration (easy to adjust)
# ---------------------------------------------------------------------------
CAPTURE_SCALE    = 0.8     # Fraction of screen to capture (centered)
TAB_SWITCH_PAUSE = 3.5     # Pause between tab switch and next screenshot (sec)
INITIAL_PAUSE    = 2.0     # Pause before the first screenshot
INITIAL_KEY      = Key.enter              # Key pressed once at the start (open screen)
TAB_KEY          = KeyCode.from_char('e') # Key for switching tabs between screenshots
OUTPUT_DIR       = "SM2_Results"

# ---------------------------------------------------------------------------
# Dropdown options
# ---------------------------------------------------------------------------
MISSIONS = [
    "INFERNO", "DECAPITATION", "VOX LIBERATIS", "RELIQUARY",
    "FALL OF ATREUS", "BALLISTIC ENGINE", "OBELISK", "GILDED FATE", "EXTRACTION",
]
DIFFICULTIES = [
    "MINIMAL", "AVERAGE", "SUBSTANTIAL", "RUTHLESS", "LETHAL",
    "DAILY STRATAGEM NORMAL", "DAILY STRATAGEM HARD",
    "WEEKLY STRATAGEM NORMAL", "WEEKLY STRATAGEM HARD",
]
GENESEED     = ["RETRIEVED", "LOST / NOT FOUND"]
ARMORYDATA   = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
WAVES        = [str(i) for i in range(1, 51)]
SIEGE_MISSIONS = ["NORMAL", "HARD"]

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
_sequence_running = threading.Event()
_kbd = KeyboardController()


def check_environment() -> None:
    try:
        import mss
        print("[INFO] Screenshot tool: mss")
    except ImportError:
        print("[ERROR] mss not found – run: pip install mss")


def ensure_output_dir(base_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_dir = base_path / OUTPUT_DIR / timestamp
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _crop_to_region(image_path: Path, region: dict) -> None:
    from PIL import Image
    x, y, w, h = region["left"], region["top"], region["width"], region["height"]
    if x == 0 and y == 0:
        with Image.open(image_path) as img:
            if img.size == (w, h):
                return
    with Image.open(image_path) as img:
        cropped = img.crop((x, y, x + w, y + h))
        cropped.save(str(image_path), "PNG")


def take_screenshot(output_path: Path, region: dict) -> None:
    import mss as _mss
    from PIL import Image
    with _mss.mss() as sct:
        raw = sct.grab(region)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        img.save(str(output_path), "PNG")


def simulate_key(key) -> None:
    print(f"  → Key: {key}")
    _kbd.press(key)
    _kbd.release(key)


def compute_region() -> dict:
    import mss as _mss
    with _mss.mss() as sct:
        m = sct.monitors[1]
        sw, sh = m["width"], m["height"]
    rw = int(sw * CAPTURE_SCALE)
    rh = int(sh * CAPTURE_SCALE)
    region = {"left": (sw - rw) // 2, "top": (sh - rh) // 2, "width": rw, "height": rh}
    print(f"[INFO] Screen: {sw}x{sh} → Capture region: {rw}x{rh} at ({region['left']}, {region['top']})")
    return region


def run_screenshot_sequence(base_path: Path) -> list[Path]:
    session_dir = ensure_output_dir(base_path)
    region = compute_region()
    paths = []

    time.sleep(INITIAL_PAUSE)

    # Screenshot 1 before pressing Enter
    output_path = session_dir / "screenshot_1.png"
    take_screenshot(output_path, region)
    print(f"Screenshot 1 saved: {output_path}")
    paths.append(output_path)

    simulate_key(INITIAL_KEY)
    time.sleep(TAB_SWITCH_PAUSE)

    for i in range(2, 5):
        output_path = session_dir / f"screenshot_{i}.png"
        take_screenshot(output_path, region)
        print(f"Screenshot {i} saved: {output_path}")
        paths.append(output_path)

        if i < 4:
            simulate_key(TAB_KEY)
            time.sleep(TAB_SWITCH_PAUSE)

    return paths


def generate_result_text(mission: str, difficulty: str, geneseed: str, armorydata: str, challenge: str = "") -> str:
    lines = []
    if challenge.strip():
        lines.append(f"CHALLENGE: {challenge.strip()}")
    lines += [
        f"MISSION: {mission}",
        f"DIFFICULTY: {difficulty}",
        f"GENESEED: {geneseed}",
        f"ARMORYDATA: {armorydata}",
        "BROTHERS: ",
    ]
    return "\n".join(lines)


def generate_siege_text(mission: str, waves: str, challenge: str = "") -> str:
    lines = []
    if challenge.strip():
        lines.append(f"CHALLENGE: {challenge.strip()}")
    lines += [
        f"MISSION: {mission}",
        f"WAVES: {waves}",
        "BROTHERS: ",
    ]
    return "\n".join(lines)


def on_copy_button(win: tk.Toplevel, mode_var: tk.StringVar, vars_op: dict, vars_siege: dict, status_label: tk.Label) -> None:
    if mode_var.get() == "SIEGE":
        text = generate_siege_text(
            mission   = vars_siege["mission"].get(),
            waves     = vars_siege["waves"].get(),
            challenge = vars_siege["challenge"].get(),
        )
    else:
        text = generate_result_text(
            mission    = vars_op["mission"].get(),
            difficulty = vars_op["difficulty"].get(),
            geneseed   = vars_op["geneseed"].get(),
            armorydata = vars_op["armorydata"].get(),
            challenge  = vars_op["challenge"].get(),
        )
    win.clipboard_clear()
    win.clipboard_append(text)
    win.update()
    print(f"Copied:\n{text}")
    status_label.config(text="✓ Copied to clipboard!")
    win.after(500, win.destroy)


def open_results_gui(parent: tk.Tk, screenshot_paths: list[Path]) -> None:
    win = tk.Toplevel(parent)
    win.title("SM2 Mission Results")
    win.resizable(False, False)

    outer = ttk.Frame(win, padding=16)
    outer.grid(sticky="nsew")

    # Mode selection
    mode_var = tk.StringVar(value="OPERATION")
    ttk.Label(outer, text="MODE:", anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
    ttk.Combobox(outer, textvariable=mode_var, values=["OPERATION", "SIEGE"], state="readonly", width=24).grid(
        row=0, column=1, sticky="ew", pady=(0, 8)
    )
    ttk.Separator(outer, orient="horizontal").grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

    # --- Operation frame ---
    op_frame = ttk.Frame(outer)
    op_frame.grid(row=2, column=0, columnspan=2, sticky="ew")

    vars_op = {
        "challenge":  tk.StringVar(value=""),
        "mission":    tk.StringVar(value=MISSIONS[0]),
        "difficulty": tk.StringVar(value=DIFFICULTIES[0]),
        "geneseed":   tk.StringVar(value=GENESEED[0]),
        "armorydata": tk.StringVar(value=ARMORYDATA[0]),
    }
    ttk.Label(op_frame, text="CHALLENGE:", anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
    ttk.Entry(op_frame, textvariable=vars_op["challenge"], width=26).grid(row=0, column=1, sticky="ew", pady=4)
    for row_idx, (lbl, key, opts) in enumerate([
        ("MISSION:",    "mission",    MISSIONS),
        ("DIFFICULTY:", "difficulty", DIFFICULTIES),
        ("GENESEED:",   "geneseed",   GENESEED),
        ("ARMORYDATA:", "armorydata", ARMORYDATA),
    ], start=1):
        ttk.Label(op_frame, text=lbl, anchor="w").grid(row=row_idx, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Combobox(op_frame, textvariable=vars_op[key], values=opts, state="readonly", width=24).grid(
            row=row_idx, column=1, sticky="ew", pady=4
        )

    # --- Siege frame ---
    siege_frame = ttk.Frame(outer)

    vars_siege = {
        "challenge": tk.StringVar(value=""),
        "mission":   tk.StringVar(value=SIEGE_MISSIONS[0]),
        "waves":     tk.StringVar(value=WAVES[0]),
    }
    ttk.Label(siege_frame, text="CHALLENGE:", anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
    ttk.Entry(siege_frame, textvariable=vars_siege["challenge"], width=26).grid(row=0, column=1, sticky="ew", pady=4)
    for row_idx, (lbl, key, opts) in enumerate([
        ("MISSION:", "mission", SIEGE_MISSIONS),
        ("WAVES:",   "waves",   WAVES),
    ], start=1):
        ttk.Label(siege_frame, text=lbl, anchor="w").grid(row=row_idx, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Combobox(siege_frame, textvariable=vars_siege[key], values=opts, state="readonly", width=24).grid(
            row=row_idx, column=1, sticky="ew", pady=4
        )

    def on_mode_change(*_):
        if mode_var.get() == "SIEGE":
            op_frame.grid_remove()
            siege_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        else:
            siege_frame.grid_remove()
            op_frame.grid(row=2, column=0, columnspan=2, sticky="ew")

    mode_var.trace_add("write", on_mode_change)

    status_label = ttk.Label(outer, text="", foreground="green")
    status_label.grid(row=4, column=0, columnspan=2, pady=(4, 0))

    ttk.Button(
        outer,
        text="Generate & copy text",
        command=lambda: on_copy_button(win, mode_var, vars_op, vars_siege, status_label),
    ).grid(row=3, column=0, columnspan=2, pady=(12, 4), sticky="ew")

    parent.wait_window(win)


def start_hotkey_listener(base_path: Path, gui_queue: queue.Queue) -> keyboard.Listener:

    def on_press(key):
        if key in (keyboard.Key.home, keyboard.Key.end, keyboard.Key.f7):
            if _sequence_running.is_set():
                print("[INFO] Screenshot sequence already running, hotkey ignored.")
                return
            _sequence_running.set()
            print("[INFO] Hotkey detected, starting screenshot sequence...")

            def run():
                try:
                    paths = run_screenshot_sequence(base_path)
                    gui_queue.put(paths)
                except Exception as exc:
                    print(f"[ERROR] Screenshot sequence failed: {exc}")
                finally:
                    _sequence_running.clear()

            threading.Thread(target=run, daemon=True).start()

    listener = keyboard.Listener(on_press=on_press)
    listener.daemon = True
    listener.start()
    return listener


def main() -> None:
    base_path = Path(__file__).parent.resolve()

    print("SM2 Screenshot & Discord-Logger Tool")
    print("=====================================")

    check_environment()

    gui_queue: queue.Queue = queue.Queue()

    # Hidden main Tk window for queue polling (keeps mainloop alive)
    hidden_root = tk.Tk()
    hidden_root.withdraw()

    start_hotkey_listener(base_path, gui_queue)
    print(f"Waiting for Home/End/F7 key... (output in {base_path / OUTPUT_DIR})")

    def poll_queue():
        try:
            paths = gui_queue.get_nowait()
            open_results_gui(hidden_root, paths)
            print("Done.")
            print("\nWaiting for Home/End/F7 key...")
        except queue.Empty:
            pass
        hidden_root.after(100, poll_queue)

    hidden_root.after(100, poll_queue)

    try:
        hidden_root.mainloop()
    except KeyboardInterrupt:
        print("\nExiting.")


if __name__ == "__main__":
    main()
