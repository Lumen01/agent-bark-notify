---
name: bark-notify
description: Use when the user asks an agent to send a Bark push notification, notify them from the terminal, test Bark notification delivery, or use the `bark-notify` CLI.
---

# Bark Notify

## Overview

Use `bark-notify` to send Bark notifications. It reads private local config from `~/.config/bark-notify.env` and optional agent identity metadata from `~/.config/bark-notify-agents.json`.

## Safety

- Never print, commit, or quote `BARK_KEY`.
- Do not put Bark keys in repository files.
- Use `--agent <name>` for agent-originated pushes so group/icon metadata can come from config.
- Only pass `--server`, `--key`, `--group`, or `--icon` when the user explicitly asks to override defaults.
- Summarize command output if it might include sensitive config.

## Send

```bash
bark-notify "Title" "Body"
bark-notify Title Body words without quoting the body
bark-notify --agent codex "Build finished" "Codex completed the requested task"
```

Use explicit overrides only when requested:

```bash
bark-notify --agent codex --group Custom --icon "https://example.com/custom.png" "Title" "Body"
```

## Agent Identity

Agent metadata is configured outside the skill:

```json
{
  "codex": {
    "group": "Codex",
    "icon": "https://example.com/icons/codex.png"
  }
}
```

Bark icons must be URLs reachable by the receiving device. Local `.app`, `.icns`, or filesystem paths are not valid notification icon values.

## Check Or Configure

```bash
bark-notify --ping
bark-notify --save-config --server "https://api.day.app" --key "<Bark device key>"
```

If sending fails, first check `--ping`; then inspect server/network status. Preserve HTTP status and short messages without exposing credentials.

