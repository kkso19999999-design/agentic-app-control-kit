# Agentic App Control Kit

An open-source Python 3.12 X11 desktop and app control toolkit for shell-access AI agents.

This package is meant for multimodal or shell-capable LLM agents that need to:

- focus applications by window title
- click, right-click, scroll, and drag inside apps
- use keyboard shortcuts
- capture screenshots and low-FPS frame sequences
- work with Chrome, VS Code, Blender, Google Docs, Colab, ComfyUI, and similar tools

It was built by Codex and refined through repeated real-world iteration with a human operator. The implementation works, but it took a lot of back-and-forth testing and tuning to get there, so this repo is intentionally honest about the rough edges and requirements.

## Why this exists

- It supports local host workflows, which is a big advantage for users building tools around local dev servers, browser-based UIs, desktop apps, MCP-style connectors, game scenes, Colab tunnels, and similar setups.
- It uses the user's real desktop, cursor, browser session, and screen instead of a fully abstract cloud sandbox.
- Because it is Python 3.12-based, other developers can use AI tools to extend it for additional operating systems beyond the current Linux X11 focus.

## Current limitations

- Right now this toolkit uses the user's own cursor and live desktop.
- It does not yet ship with a polished built-in "agent is currently controlling this app" highlight system that is always visible in a production-ready way.
- A basic temporary border/marker helper is included, but a stronger cross-platform operator-safety indicator would be a great contribution.

If you are a developer building on top of this, please feel free to improve the visibility/highlight experience and add support for more operating systems.

## What is included

- `toolkit/app_control.py`
  The main X11 desktop and app automation script.
- `examples/app_actions.sample.json`
  A sample JSON action script.
- `examples/project_paths.example.json`
  Placeholder paths that other users can adapt.
- `examples/llm_shell_prompt_template.md`
  A sample prompt users can hand to a shell-access multimodal LLM.
- `docs/folder-structure.md`
  Recommended repo layout and adaptation notes.
- `requirements.txt`
  Python package dependencies for the toolkit.

## Supported actions

- list windows
- focus a window
- read geometry
- visible screenshot capture
- X11 content capture of a target window
- repeated frame capture
- move mouse
- left, middle, or right click
- mouse down / mouse up
- drag and drop
- scroll
- type text
- send hotkeys
- wait for a window
- temporary highlight border around an app
- temporary target marker on screen
- run a JSON action script

## Environment requirements

This toolkit is currently aimed at Linux desktops using X11.

System tools expected:

- `wmctrl`
- `xwd`
- `xprop`
- `xrandr`

Python packages:

- `mss`
- `Pillow`
- `pynput`
- `pygetwindow`
- `python-xlib`
- `PyQt5`

## Quick start

Create or activate a Python environment, then install:

```bash
pip install -r requirements.txt
```

Run the tool:

```bash
python toolkit/app_control.py list-windows
python toolkit/app_control.py geometry "Google Chrome"
python toolkit/app_control.py screenshot /tmp/chrome.png --title "Google Chrome"
python toolkit/app_control.py click 300 200 --title "Google Chrome" --relative
python toolkit/app_control.py drag 300 200 560 420 --title "Google Chrome" --relative
python toolkit/app_control.py key ctrl+l --title "Google Chrome"
```

## Example workflow

Open an app surface and navigate to a page:

```bash
python toolkit/app_control.py focus "Google Chrome"
python toolkit/app_control.py key ctrl+l --title "Google Chrome"
python toolkit/app_control.py type "https://www.wikipedia.org" --title "Google Chrome"
python toolkit/app_control.py key enter --title "Google Chrome"
```

Capture a low-FPS review sequence:

```bash
python toolkit/app_control.py content-watch /tmp/wiki-frames --title "Google Chrome" --interval 2 --count 10
```

## Placeholder path adaptation

Use the example file here:

- `examples/project_paths.example.json`

Replace the placeholder values with your real workspace root, Python path, screenshot directory, and preferred application titles.

## Sample prompt for shell-access multimodal LLMs

See:

- `examples/llm_shell_prompt_template.md`

That template is designed for agents that can run shell commands and optionally inspect screenshots.

## Recommended usage style

- Prefer one action at a time when verifying risky UI flows.
- Use low-FPS capture for debugging animation or load issues.
- Use JSON action scripts only when the flow is already understood.
- Keep screenshots and transcripts outside the toolkit folder if you plan to publish the repo cleanly.

## Honesty note

This project was not generated in one clean shot. It was built through real iteration, failures, retries, UI verification, and toolchain patching. That is part of the value: it gives future users a working starting point for agentic local app and local-host workflows that many platforms still do not support cleanly.

## License

MIT
