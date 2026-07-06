---
name: bark-notify
description: Use when the user asks an agent to send a Bark push notification, notify them from the terminal, test Bark notification delivery, or use a Bark notification skill.
---

# Bark Notify

## Overview

Use this skill to send Bark notifications from an agent. The bundled script is `scripts/bark-notify.py`, resolved relative to this `SKILL.md`.

## Safety

- Never print, commit, or quote `BARK_KEY`.
- Do not put Bark keys in repository files.
- Prefer local private config at `~/.config/bark-notify.env`.
- Use `--agent <name>` for agent-originated pushes so group/icon metadata can come from config.
- Only pass `--server`, `--key`, `--group`, or `--icon` when the user explicitly asks to override defaults.
- If command output could include sensitive config, summarize it instead of pasting raw output.

## Send

Run the bundled script from this skill directory:

```bash
python3 scripts/bark-notify.py "Title" "Body"
python3 scripts/bark-notify.py Title Body words without quoting the body
python3 scripts/bark-notify.py --agent codex --level passive "Build finished" "Codex completed the requested task"
```

Use explicit overrides only when requested:

```bash
python3 scripts/bark-notify.py --agent codex --group Custom --icon "https://example.com/custom.png" "Title" "Body"
```

## Notification Level

Choose the lowest Bark interruption level that fits the situation:

| Situation | Level |
| --- | --- |
| Agent completed work, tests passed, background status, FYI | `passive` |
| User explicitly asked for a normal notification | `active` |
| Agent is blocked and needs user input soon | `timeSensitive` |
| Deployment failed, service is unavailable, long task crashed | `timeSensitive` |
| User explicitly requested an emergency/critical alert | `critical` |

Rules:

- Default to `passive` for agent-initiated completion/status notifications.
- Use `active` for ordinary user-requested notifications when no urgency is stated.
- Use `timeSensitive` only when the user should notice promptly.
- Use `critical` only when explicitly requested or clearly safety/incident critical; do not use it for routine task failures.
- If the user specifies a level, obey the user.

## Configure

Initialize local private config:

```bash
python3 scripts/bark-notify.py --save-config --server "https://api.day.app" --key "<Bark device key>"
```

Agent metadata is optional and lives outside the repository at `~/.config/bark-notify-agents.json`:

```json
{
  "codex": {
    "group": "Codex",
    "icon": "https://example.com/icons/codex.png"
  }
}
```

Bark icons must be URLs reachable by the receiving device. Local `.app`, `.icns`, or filesystem paths are not valid notification icon values. If no icon URL is configured, omit the icon and still send the notification.

## Check

```bash
python3 scripts/bark-notify.py --help
python3 scripts/bark-notify.py --ping
```

If sending fails, first check `--ping`; then inspect server/network status. Preserve HTTP status and short messages without exposing credentials.
