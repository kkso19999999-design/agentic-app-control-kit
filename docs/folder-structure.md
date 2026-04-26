# Folder Structure

Recommended public repo layout:

```text
agentic-app-control-kit/
├── toolkit/
│   └── app_control.py
├── examples/
│   ├── app_actions.sample.json
│   ├── llm_shell_prompt_template.md
│   └── project_paths.example.json
├── docs/
│   └── folder-structure.md
├── requirements.txt
├── LICENSE
├── .gitignore
└── README.md
```

## Notes

- Keep the toolkit itself small and reusable.
- Put project-specific automation scripts in a separate repo or subfolder.
- Use placeholder paths in public examples instead of leaking personal home directories.
- If you adapt this for Blender, Colab, ComfyUI, or VS Code, add app-specific examples under `examples/`.

## Suggested extension points

- OCR integration for reading UI text
- window-aware task runner that triggers screenshots only after visual changes
- app-specific helpers for Colab, Google Docs, GitHub, ComfyUI, Blender, or MCP-connected tools
- scene verification pipelines for local game dev workflows
