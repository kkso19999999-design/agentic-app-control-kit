#!/home/kushagra/3d_env/bin/python
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import mss
import mss.tools
from PIL import Image
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Button, Controller as MouseController


mouse = MouseController()
keyboard = KeyboardController()

BUTTONS = {
    "left": Button.left,
    "middle": Button.middle,
    "right": Button.right,
}

SPECIAL_KEYS = {
    "alt": Key.alt,
    "alt_l": Key.alt_l,
    "alt_r": Key.alt_r,
    "backspace": Key.backspace,
    "caps_lock": Key.caps_lock,
    "cmd": Key.cmd,
    "ctrl": Key.ctrl,
    "ctrl_l": Key.ctrl_l,
    "ctrl_r": Key.ctrl_r,
    "delete": Key.delete,
    "down": Key.down,
    "end": Key.end,
    "enter": Key.enter,
    "esc": Key.esc,
    "f1": Key.f1,
    "f2": Key.f2,
    "f3": Key.f3,
    "f4": Key.f4,
    "f5": Key.f5,
    "f6": Key.f6,
    "f7": Key.f7,
    "f8": Key.f8,
    "f9": Key.f9,
    "f10": Key.f10,
    "f11": Key.f11,
    "f12": Key.f12,
    "home": Key.home,
    "left": Key.left,
    "page_down": Key.page_down,
    "page_up": Key.page_up,
    "right": Key.right,
    "shift": Key.shift,
    "shift_l": Key.shift_l,
    "shift_r": Key.shift_r,
    "space": Key.space,
    "tab": Key.tab,
    "up": Key.up,
}


@dataclass
class WindowInfo:
    window_id: str
    desktop: str
    x: int
    y: int
    width: int
    height: int
    host: str
    title: str

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


def run_command(args: list[str]) -> str:
    result = subprocess.run(args, check=True, capture_output=True, text=True, env=os.environ.copy())
    return result.stdout


def list_windows() -> list[WindowInfo]:
    output = run_command(["wmctrl", "-lG"])
    windows: list[WindowInfo] = []
    for line in output.splitlines():
        parts = line.split(None, 7)
        if len(parts) < 8:
            continue
        window_id, desktop, x, y, width, height, host, title = parts
        windows.append(
            WindowInfo(
                window_id=window_id,
                desktop=desktop,
                x=int(x),
                y=int(y),
                width=int(width),
                height=int(height),
                host=host,
                title=title,
            )
        )
    return windows


def find_window(title_query: str) -> WindowInfo:
    query = title_query.lower()
    matches = [w for w in list_windows() if query in w.title.lower()]
    if not matches:
        raise SystemExit(f'No window matched title query: {title_query!r}')
    matches.sort(key=lambda w: (w.width * w.height), reverse=True)
    return matches[0]


def focus_window(window: WindowInfo) -> None:
    subprocess.run(["wmctrl", "-ia", window.window_id], check=True)
    time.sleep(0.2)


def monitor_from_window(window: WindowInfo) -> dict[str, int]:
    return {
        "left": max(window.x, 0),
        "top": max(window.y, 0),
        "width": max(window.width, 1),
        "height": max(window.height, 1),
    }


def screenshot(path: Path, window_title: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with mss.MSS() as sct:
        if window_title:
            window = find_window(window_title)
            shot = sct.grab(monitor_from_window(window))
        else:
            shot = sct.grab(sct.monitors[0])
        mss.tools.to_png(shot.rgb, shot.size, output=str(path))


def screenshot_window_content(path: Path, window_title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    window = find_window(window_title)
    with tempfile.NamedTemporaryFile(suffix=".xwd", delete=False) as tmp:
        temp_path = tmp.name
    try:
        subprocess.run(["xwd", "-silent", "-id", window.window_id, "-out", temp_path], check=True, env=os.environ.copy())
        image = Image.open(temp_path)
        image.save(path)
    finally:
        try:
            os.remove(temp_path)
        except FileNotFoundError:
            pass


def resolve_key(name: str):
    lowered = name.lower()
    return SPECIAL_KEYS.get(lowered, lowered)


def tap_key(name: str) -> None:
    key = resolve_key(name)
    keyboard.press(key)
    keyboard.release(key)


def press_hotkey(parts: list[str]) -> None:
    resolved = [resolve_key(part) for part in parts]
    for key in resolved:
        keyboard.press(key)
    for key in reversed(resolved):
        keyboard.release(key)


def relative_to_absolute(window: WindowInfo, x: int, y: int) -> tuple[int, int]:
    return window.x + x, window.y + y


def maybe_focus_and_resolve_xy(args: argparse.Namespace) -> tuple[int, int]:
    x = args.x
    y = args.y
    if getattr(args, "title", None):
        window = find_window(args.title)
        focus_window(window)
        if getattr(args, "relative", False):
            x, y = relative_to_absolute(window, x, y)
    return x, y


def cmd_list_windows(_: argparse.Namespace) -> None:
    print(json.dumps([w.__dict__ for w in list_windows()], indent=2))


def cmd_focus(args: argparse.Namespace) -> None:
    window = find_window(args.title)
    focus_window(window)
    print(json.dumps(window.__dict__, indent=2))


def cmd_geometry(args: argparse.Namespace) -> None:
    window = find_window(args.title)
    print(json.dumps({**window.__dict__, "center": window.center}, indent=2))


def cmd_screenshot(args: argparse.Namespace) -> None:
    screenshot(Path(args.output), args.title)
    print(args.output)


def cmd_content_screenshot(args: argparse.Namespace) -> None:
    screenshot_window_content(Path(args.output), args.title)
    print(args.output)


def cmd_watch(args: argparse.Namespace) -> None:
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for index in range(args.count):
        target = out_dir / f"frame_{index:04d}.png"
        screenshot(target, args.title)
        print(str(target))
        if index < args.count - 1:
            time.sleep(args.interval)


def cmd_content_watch(args: argparse.Namespace) -> None:
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for index in range(args.count):
        target = out_dir / f"frame_{index:04d}.png"
        screenshot_window_content(target, args.title)
        print(str(target))
        if index < args.count - 1:
            time.sleep(args.interval)


def cmd_click(args: argparse.Namespace) -> None:
    x, y = maybe_focus_and_resolve_xy(args)
    mouse.position = (x, y)
    time.sleep(args.move_duration)
    for index in range(args.clicks):
        mouse.click(BUTTONS[args.button], 1)
        if index < args.clicks - 1:
            time.sleep(args.click_interval)
    print(json.dumps({"x": x, "y": y, "button": args.button, "clicks": args.clicks}, indent=2))


def cmd_move(args: argparse.Namespace) -> None:
    x, y = maybe_focus_and_resolve_xy(args)
    mouse.position = (x, y)
    time.sleep(args.move_duration)
    print(json.dumps({"x": x, "y": y}, indent=2))


def cmd_mouse_down(args: argparse.Namespace) -> None:
    x, y = maybe_focus_and_resolve_xy(args)
    mouse.position = (x, y)
    time.sleep(args.move_duration)
    mouse.press(BUTTONS[args.button])
    print(json.dumps({"x": x, "y": y, "button": args.button, "state": "down"}, indent=2))


def cmd_mouse_up(args: argparse.Namespace) -> None:
    x, y = maybe_focus_and_resolve_xy(args)
    mouse.position = (x, y)
    time.sleep(args.move_duration)
    mouse.release(BUTTONS[args.button])
    print(json.dumps({"x": x, "y": y, "button": args.button, "state": "up"}, indent=2))


def cmd_drag(args: argparse.Namespace) -> None:
    start_x = args.x1
    start_y = args.y1
    end_x = args.x2
    end_y = args.y2

    if getattr(args, "title", None):
        window = find_window(args.title)
        focus_window(window)
        if getattr(args, "relative", False):
            start_x, start_y = relative_to_absolute(window, start_x, start_y)
            end_x, end_y = relative_to_absolute(window, end_x, end_y)

    mouse.position = (start_x, start_y)
    time.sleep(args.move_duration)
    mouse.press(BUTTONS[args.button])
    time.sleep(args.hold_duration)
    mouse.position = (end_x, end_y)
    time.sleep(args.drag_duration)
    mouse.release(BUTTONS[args.button])
    print(json.dumps({
        "start": [start_x, start_y],
        "end": [end_x, end_y],
        "button": args.button
    }, indent=2))


def cmd_scroll(args: argparse.Namespace) -> None:
    if getattr(args, "title", None):
        focus_window(find_window(args.title))
    mouse.scroll(args.dx, args.dy)
    print(json.dumps({"dx": args.dx, "dy": args.dy}, indent=2))


def cmd_key(args: argparse.Namespace) -> None:
    if args.title:
        focus_window(find_window(args.title))
    keys = [part.strip() for part in args.keys.split("+") if part.strip()]
    if len(keys) == 1:
        tap_key(keys[0])
    else:
        press_hotkey(keys)
    print(json.dumps({"keys": keys}, indent=2))


def cmd_type(args: argparse.Namespace) -> None:
    if args.title:
        focus_window(find_window(args.title))
    for char in args.text:
        keyboard.press(char)
        keyboard.release(char)
        time.sleep(args.interval)
    print(json.dumps({"typed": args.text}, indent=2))


def cmd_highlight_window(args: argparse.Namespace) -> None:
    window = find_window(args.title)
    script = Path(__file__).resolve()
    subprocess.Popen(
        [
            sys.executable,
            str(script),
            "_overlay",
            "border",
            "--x", str(window.x - args.padding),
            "--y", str(window.y - args.padding),
            "--width", str(window.width + args.padding * 2),
            "--height", str(window.height + args.padding * 2),
            "--seconds", str(args.seconds),
            "--color", args.color,
            "--thickness", str(args.thickness),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=os.environ.copy(),
    )
    print(json.dumps({"window": window.title, "seconds": args.seconds}, indent=2))


def cmd_mark(args: argparse.Namespace) -> None:
    x, y = maybe_focus_and_resolve_xy(args)
    script = Path(__file__).resolve()
    subprocess.Popen(
        [
            sys.executable,
            str(script),
            "_overlay",
            "marker",
            "--x", str(x),
            "--y", str(y),
            "--seconds", str(args.seconds),
            "--color", args.color,
            "--radius", str(args.radius),
            "--thickness", str(args.thickness),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=os.environ.copy(),
    )
    print(json.dumps({"x": x, "y": y, "seconds": args.seconds}, indent=2))


def wait_for_window(title: str, timeout: float = 10.0, interval: float = 0.25) -> WindowInfo:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            return find_window(title)
        except SystemExit as error:
            last_error = error
            time.sleep(interval)
    raise SystemExit(str(last_error) if last_error else f"Window not found: {title!r}")


def cmd_wait_window(args: argparse.Namespace) -> None:
    window = wait_for_window(args.title, args.timeout, args.interval)
    print(json.dumps(window.__dict__, indent=2))


def execute_action(action: dict) -> None:
    command = action["command"]
    data = {key.replace("-", "_"): value for key, value in action.items() if key != "command"}

    if command == "sleep":
        time.sleep(float(data.get("seconds", 1.0)))
        return

    if command == "wait-window":
        cmd_wait_window(SimpleNamespace(
            title=data["title"],
            timeout=float(data.get("timeout", 10.0)),
            interval=float(data.get("interval", 0.25)),
        ))
        return

    if command == "focus":
        cmd_focus(SimpleNamespace(title=data["title"]))
        return

    if command == "geometry":
        cmd_geometry(SimpleNamespace(title=data["title"]))
        return

    if command == "screenshot":
        cmd_screenshot(SimpleNamespace(output=data["output"], title=data.get("title")))
        return

    if command == "content-screenshot":
        cmd_content_screenshot(SimpleNamespace(output=data["output"], title=data["title"]))
        return

    if command == "click":
        cmd_click(SimpleNamespace(
            x=int(data["x"]),
            y=int(data["y"]),
            title=data.get("title"),
            relative=bool(data.get("relative", False)),
            button=data.get("button", "left"),
            clicks=int(data.get("clicks", 1)),
            click_interval=float(data.get("click_interval", 0.1)),
            move_duration=float(data.get("move_duration", 0.15)),
        ))
        return

    if command == "move":
        cmd_move(SimpleNamespace(
            x=int(data["x"]),
            y=int(data["y"]),
            title=data.get("title"),
            relative=bool(data.get("relative", False)),
            move_duration=float(data.get("move_duration", 0.15)),
        ))
        return

    if command == "mouse-down":
        cmd_mouse_down(SimpleNamespace(
            x=int(data["x"]),
            y=int(data["y"]),
            title=data.get("title"),
            relative=bool(data.get("relative", False)),
            button=data.get("button", "left"),
            move_duration=float(data.get("move_duration", 0.15)),
        ))
        return

    if command == "mouse-up":
        cmd_mouse_up(SimpleNamespace(
            x=int(data["x"]),
            y=int(data["y"]),
            title=data.get("title"),
            relative=bool(data.get("relative", False)),
            button=data.get("button", "left"),
            move_duration=float(data.get("move_duration", 0.15)),
        ))
        return

    if command == "drag":
        cmd_drag(SimpleNamespace(
            x1=int(data["x1"]),
            y1=int(data["y1"]),
            x2=int(data["x2"]),
            y2=int(data["y2"]),
            title=data.get("title"),
            relative=bool(data.get("relative", False)),
            button=data.get("button", "left"),
            move_duration=float(data.get("move_duration", 0.15)),
            hold_duration=float(data.get("hold_duration", 0.1)),
            drag_duration=float(data.get("drag_duration", 0.25)),
        ))
        return

    if command == "scroll":
        cmd_scroll(SimpleNamespace(
            dx=int(data.get("dx", 0)),
            dy=int(data.get("dy", 0)),
            title=data.get("title"),
        ))
        return

    if command == "key":
        cmd_key(SimpleNamespace(keys=data["keys"], title=data.get("title")))
        return

    if command == "type":
        cmd_type(SimpleNamespace(
            text=data["text"],
            title=data.get("title"),
            interval=float(data.get("interval", 0.02)),
        ))
        return

    if command == "highlight-window":
        cmd_highlight_window(SimpleNamespace(
            title=data["title"],
            seconds=float(data.get("seconds", 2.0)),
            padding=int(data.get("padding", 6)),
            thickness=int(data.get("thickness", 4)),
            color=data.get("color", "#ffb347dd"),
        ))
        return

    if command == "mark":
        cmd_mark(SimpleNamespace(
            x=int(data["x"]),
            y=int(data["y"]),
            title=data.get("title"),
            relative=bool(data.get("relative", False)),
            seconds=float(data.get("seconds", 1.5)),
            radius=int(data.get("radius", 28)),
            thickness=int(data.get("thickness", 4)),
            color=data.get("color", "#46d9ffdd"),
        ))
        return

    raise SystemExit(f"Unsupported script command: {command}")


def cmd_run_script(args: argparse.Namespace) -> None:
    actions = json.loads(Path(args.path).read_text())
    if not isinstance(actions, list):
        raise SystemExit("Script file must contain a JSON list of action objects.")
    for index, action in enumerate(actions):
        if not isinstance(action, dict) or "command" not in action:
            raise SystemExit(f"Invalid action at index {index}: {action!r}")
        execute_action(action)
    print(json.dumps({"status": "ok", "actions": len(actions)}, indent=2))


def parse_hex_color(value: str) -> tuple[int, int, int, int]:
    text = value.strip().lstrip("#")
    if len(text) == 6:
        text += "ff"
    if len(text) != 8:
        raise ValueError(f"Unsupported color format: {value}")
    return tuple(int(text[index:index + 2], 16) for index in range(0, 8, 2))


def run_overlay(argv: list[str]) -> int:
    from PyQt5 import QtCore, QtGui, QtWidgets

    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["border", "marker"])
    parser.add_argument("--x", type=int, required=True)
    parser.add_argument("--y", type=int, required=True)
    parser.add_argument("--width", type=int, default=0)
    parser.add_argument("--height", type=int, default=0)
    parser.add_argument("--seconds", type=float, default=1.4)
    parser.add_argument("--color", default="#ffb347dd")
    parser.add_argument("--thickness", type=int, default=4)
    parser.add_argument("--radius", type=int, default=32)
    args = parser.parse_args(argv)

    app = QtWidgets.QApplication(["app_control_overlay"])
    color = QtGui.QColor(*parse_hex_color(args.color))

    class OverlayWidget(QtWidgets.QWidget):
        def __init__(self) -> None:
            super().__init__()
            flags = (
                QtCore.Qt.FramelessWindowHint
                | QtCore.Qt.Tool
                | QtCore.Qt.WindowStaysOnTopHint
                | QtCore.Qt.BypassWindowManagerHint
            )
            self.setWindowFlags(flags)
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
            self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
            self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)

            if args.mode == "border":
                self.setGeometry(args.x, args.y, max(args.width, 1), max(args.height, 1))
            else:
                size = args.radius * 2 + args.thickness * 6
                self.setGeometry(args.x - size // 2, args.y - size // 2, size, size)

        def paintEvent(self, _event) -> None:
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            pen = QtGui.QPen(color, args.thickness)
            painter.setPen(pen)

            if args.mode == "border":
                rect = self.rect().adjusted(args.thickness, args.thickness, -args.thickness, -args.thickness)
                painter.drawRoundedRect(rect, 12, 12)
            else:
                center = self.rect().center()
                radius = args.radius
                painter.drawEllipse(center, radius, radius)
                painter.drawLine(center.x() - radius - 10, center.y(), center.x() + radius + 10, center.y())
                painter.drawLine(center.x(), center.y() - radius - 10, center.x(), center.y() + radius + 10)

    widget = OverlayWidget()
    widget.show()
    QtCore.QTimer.singleShot(int(args.seconds * 1000), app.quit)
    return app.exec_()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simple X11 desktop and app control helper for Codex.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("list-windows", help="List top-level windows via wmctrl.")
    p.set_defaults(func=cmd_list_windows)

    p = subparsers.add_parser("focus", help="Focus the first matching window by title substring.")
    p.add_argument("title")
    p.set_defaults(func=cmd_focus)

    p = subparsers.add_parser("geometry", help="Print window geometry for a matching title.")
    p.add_argument("title")
    p.set_defaults(func=cmd_geometry)

    p = subparsers.add_parser("wait-window", help="Wait until a matching window appears.")
    p.add_argument("title")
    p.add_argument("--timeout", type=float, default=10.0)
    p.add_argument("--interval", type=float, default=0.25)
    p.set_defaults(func=cmd_wait_window)

    p = subparsers.add_parser("screenshot", help="Capture a screenshot of the full screen or one window.")
    p.add_argument("output")
    p.add_argument("--title", help="Capture the first window whose title contains this text.")
    p.set_defaults(func=cmd_screenshot)

    p = subparsers.add_parser("content-screenshot", help="Capture window contents through X11 even if another window is on top.")
    p.add_argument("output")
    p.add_argument("--title", required=True, help="Capture the first window whose title contains this text.")
    p.set_defaults(func=cmd_content_screenshot)

    p = subparsers.add_parser("watch", help="Capture screenshots repeatedly.")
    p.add_argument("output_dir")
    p.add_argument("--title", help="Capture the first window whose title contains this text.")
    p.add_argument("--interval", type=float, default=2.0, help="Seconds between frames.")
    p.add_argument("--count", type=int, default=10, help="Number of frames to capture.")
    p.set_defaults(func=cmd_watch)

    p = subparsers.add_parser("content-watch", help="Repeatedly capture window contents through X11.")
    p.add_argument("output_dir")
    p.add_argument("--title", required=True, help="Capture the first window whose title contains this text.")
    p.add_argument("--interval", type=float, default=2.0, help="Seconds between frames.")
    p.add_argument("--count", type=int, default=10, help="Number of frames to capture.")
    p.set_defaults(func=cmd_content_watch)

    p = subparsers.add_parser("click", help="Click at absolute or window-relative coordinates.")
    p.add_argument("x", type=int)
    p.add_argument("y", type=int)
    p.add_argument("--title", help="Focus this window first.")
    p.add_argument("--relative", action="store_true", help="Treat x/y as relative to the matched window.")
    p.add_argument("--button", default="left", choices=["left", "middle", "right"])
    p.add_argument("--clicks", type=int, default=1)
    p.add_argument("--click-interval", type=float, default=0.1)
    p.add_argument("--move-duration", type=float, default=0.15)
    p.set_defaults(func=cmd_click)

    p = subparsers.add_parser("move", help="Move the cursor without clicking.")
    p.add_argument("x", type=int)
    p.add_argument("y", type=int)
    p.add_argument("--title", help="Focus this window first.")
    p.add_argument("--relative", action="store_true", help="Treat x/y as relative to the matched window.")
    p.add_argument("--move-duration", type=float, default=0.15)
    p.set_defaults(func=cmd_move)

    p = subparsers.add_parser("mouse-down", help="Press and hold a mouse button.")
    p.add_argument("x", type=int)
    p.add_argument("y", type=int)
    p.add_argument("--title", help="Focus this window first.")
    p.add_argument("--relative", action="store_true", help="Treat x/y as relative to the matched window.")
    p.add_argument("--button", default="left", choices=["left", "middle", "right"])
    p.add_argument("--move-duration", type=float, default=0.15)
    p.set_defaults(func=cmd_mouse_down)

    p = subparsers.add_parser("mouse-up", help="Release a mouse button.")
    p.add_argument("x", type=int)
    p.add_argument("y", type=int)
    p.add_argument("--title", help="Focus this window first.")
    p.add_argument("--relative", action="store_true", help="Treat x/y as relative to the matched window.")
    p.add_argument("--button", default="left", choices=["left", "middle", "right"])
    p.add_argument("--move-duration", type=float, default=0.15)
    p.set_defaults(func=cmd_mouse_up)

    p = subparsers.add_parser("drag", help="Drag from one point to another.")
    p.add_argument("x1", type=int)
    p.add_argument("y1", type=int)
    p.add_argument("x2", type=int)
    p.add_argument("y2", type=int)
    p.add_argument("--title", help="Focus this window first.")
    p.add_argument("--relative", action="store_true", help="Treat coordinates as relative to the matched window.")
    p.add_argument("--button", default="left", choices=["left", "middle", "right"])
    p.add_argument("--move-duration", type=float, default=0.15)
    p.add_argument("--hold-duration", type=float, default=0.1)
    p.add_argument("--drag-duration", type=float, default=0.25)
    p.set_defaults(func=cmd_drag)

    p = subparsers.add_parser("scroll", help="Scroll vertically or horizontally.")
    p.add_argument("dx", type=int, help="Horizontal scroll amount.")
    p.add_argument("dy", type=int, help="Vertical scroll amount.")
    p.add_argument("--title", help="Focus this window first.")
    p.set_defaults(func=cmd_scroll)

    p = subparsers.add_parser("key", help="Send one key or a hotkey combo like ctrl+l.")
    p.add_argument("keys")
    p.add_argument("--title", help="Focus this window first.")
    p.set_defaults(func=cmd_key)

    p = subparsers.add_parser("type", help="Type text into the focused window.")
    p.add_argument("text")
    p.add_argument("--title", help="Focus this window first.")
    p.add_argument("--interval", type=float, default=0.02)
    p.set_defaults(func=cmd_type)

    p = subparsers.add_parser("highlight-window", help="Draw a temporary highlighted border around a window.")
    p.add_argument("title")
    p.add_argument("--seconds", type=float, default=2.0)
    p.add_argument("--padding", type=int, default=6)
    p.add_argument("--thickness", type=int, default=4)
    p.add_argument("--color", default="#ffb347dd")
    p.set_defaults(func=cmd_highlight_window)

    p = subparsers.add_parser("mark", help="Draw a temporary target marker at a point.")
    p.add_argument("x", type=int)
    p.add_argument("y", type=int)
    p.add_argument("--title", help="Focus this window first.")
    p.add_argument("--relative", action="store_true", help="Treat x/y as relative to the matched window.")
    p.add_argument("--seconds", type=float, default=1.5)
    p.add_argument("--radius", type=int, default=28)
    p.add_argument("--thickness", type=int, default=4)
    p.add_argument("--color", default="#46d9ffdd")
    p.set_defaults(func=cmd_mark)

    p = subparsers.add_parser("run-script", help="Run a JSON action script to reduce command round-trips.")
    p.add_argument("path")
    p.set_defaults(func=cmd_run_script)

    return parser


def main() -> int:
    if os.environ.get("DISPLAY") is None:
        print("DISPLAY is not set. This tool requires an active X11 desktop session.", file=sys.stderr)
        return 1
    if len(sys.argv) > 1 and sys.argv[1] == "_overlay":
        return run_overlay(sys.argv[2:])
    args = build_parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
