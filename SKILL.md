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
- Do not put a real key after `--key` in a shell command: it can be retained in shell history or exposed to local process inspection. Use the private config file or `--key-stdin` for setup.
- Use `--agent <name>` for agent-originated pushes so group/icon metadata can come from config.
- Only pass `--server`, `--key`, `--group`, or `--icon` when the user explicitly asks to override defaults.
- If command output could include sensitive config, summarize it instead of pasting raw output.

## Send

Run the bundled script from this skill directory:

```bash
python3 scripts/bark-notify.py "Title" "Body"
python3 scripts/bark-notify.py Title Body words without quoting the body
python3 scripts/bark-notify.py --agent codex --level active "Build finished" "Codex completed the requested task"
python3 scripts/bark-notify.py --agent codex --level passive "Progress update" "Tests are running"
```

Use explicit overrides only when requested:

```bash
python3 scripts/bark-notify.py --agent codex --group Custom --icon "https://example.com/custom.png" "Title" "Body"
```

## Notification Level

Choose the lowest Bark interruption level that fits the situation:

| Situation | Level |
| --- | --- |
| Progress update, background status, FYI | `passive` |
| Requested task completed, or user explicitly asked for a normal notification | `active` |
| Agent is blocked and needs user input soon | `timeSensitive` |
| Deployment failed, service is unavailable, long task crashed | `timeSensitive` |
| User explicitly requested an emergency/critical alert | `critical` |

Rules:

- Default to `active` when notifying that a user-requested task is complete. It is a normal visible notification.
- Use `passive` for intermediate progress updates that should not light up the screen.
- Use `timeSensitive` only when the user should notice promptly.
- Use `critical` only when explicitly requested or clearly safety/incident critical; do not use it for routine task failures.
- If the user specifies a level, obey the user.

## Configure

Create `~/.config/bark-notify.env` manually when possible. It is private local configuration and the script saves it with mode `0600`:

```bash
mkdir -p ~/.config
chmod 700 ~/.config
```

To initialize it without putting the key in shell history, pass the key through standard input:

```bash
read -rs BARK_KEY; printf '\n'
printf '%s\n' "$BARK_KEY" | python3 scripts/bark-notify.py --save-config --key-stdin
unset BARK_KEY
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
python3 scripts/bark-notify.py --doctor
python3 scripts/bark-notify.py --dry-run --agent codex --level active "Done" "Ready"
```

`--doctor` reports the selected server, config-file permissions, agent/group/icon resolution, and ping result without printing the key. `--dry-run` prints the final request payload with `device_key` masked and never sends a notification.

If sending fails, first check `--doctor`; then inspect the reported server/network status. Preserve HTTP status and short messages without exposing credentials.
