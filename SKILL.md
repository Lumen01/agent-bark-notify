---
name: bark-notify
description: Use when the user asks an agent to send a Bark push notification, notify them from the terminal, test Bark notification delivery, or use a Bark notification skill.
metadata:
  author: "Lumen"
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
python3 scripts/bark-notify.py --agent codex --level active "Milestone reached" "The first migration finished"
```

Use explicit overrides only when requested:

```bash
python3 scripts/bark-notify.py --agent codex --group Custom --icon "https://example.com/custom.png" "Title" "Body"
```

## Decide Whether to Send

A progress-update instruction grants permission to send useful notifications; it does not make every agent update notification-worthy.

Send a Bark notification when at least one of these is true:

- The user explicitly asked for a Bark notification or reminder.
- A long-running task reached a meaningful milestone or completed while the user may be away.
- The agent is blocked, a long-running task failed, or the user needs to act.

Skip Bark for routine tool activity, short tasks, tests merely starting or continuing, partial findings, and updates already visible in the active conversation. If an update is too minor for a normal visible notification, usually do not send it. Use `passive` only when the user explicitly asks for a quiet, passive, background, or Notification Center-only delivery.

## Notification Level

After deciding to send, choose the level from this table. Use `active` when the user did not specify a level and the situation does not require `timeSensitive` or `critical`:

| Situation | Level |
| --- | --- |
| Meaningful progress, requested task completed, or ordinary user-requested notification | `active` |
| Agent is blocked and needs user input soon | `timeSensitive` |
| Deployment failed, service is unavailable, long task crashed | `timeSensitive` |
| User explicitly requested an emergency/critical alert | `critical` |
| User explicitly requested quiet/background delivery | `passive` |

Rules:

- Default to `active` whenever a notification is worth sending, including meaningful progress and task completion.
- Do not use `passive` as a low-stakes default or a fallback for routine progress. Skip the push instead.
- Use `passive` only when the user explicitly requests quiet/background delivery.
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

Bark icons must be URLs reachable by the receiving device. Local `.app`, `.icns`, or filesystem paths are not valid notification icon values. If no `--icon` or agent icon is configured, use the built-in Agent Bark icon hosted from `assets/agent-bark.png` through jsDelivr. Resolution order is explicit `--icon`, agent environment/config, then the built-in default.

## Check

```bash
python3 scripts/bark-notify.py --help
python3 scripts/bark-notify.py --ping
python3 scripts/bark-notify.py --doctor
python3 scripts/bark-notify.py --dry-run --agent codex --level active "Done" "Ready"
```

`--doctor` reports the selected server, config-file permissions, agent/group/icon resolution, and ping result without printing the key. `--dry-run` prints the final request payload with `device_key` masked and never sends a notification.

If sending fails, first check `--doctor`; then inspect the reported server/network status. Preserve HTTP status and short messages without exposing credentials.
