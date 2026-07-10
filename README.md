# Bark Notify Skill

[中文文档](README.zh-CN.md)

Skill for sending [Bark](https://github.com/Finb/Bark) push notifications from agents.

This repository is a skill first. The notification helper is a bundled script at
`scripts/bark-notify.py`, not a standalone package that must be installed from PyPI.

## Install The Skill

### Ask an Agent to Install It

Paste this prompt into an agent that has terminal access:

```text
Read https://github.com/Lumen01/agent-bark-notify/blob/main/README.md and install Bark Notify Skill by following its “Install Manually” section. Prefer the shared multi-agent installation unless I ask for a single runtime. Check for an existing installation before changing files, expose the skill to the requested runtime, and confirm that its SKILL.md is discoverable. Do not configure, print, commit, or place a Bark device key in shell history.
```

### Install Manually

The following instructions are for people who prefer to install the skill themselves.

#### For Multiple Agents

If you want Codex, Claude, OpenCode, and other agents to share this skill, install
it once under `~/.agents`:

```bash
git clone https://github.com/Lumen01/agent-bark-notify.git ~/.agents/skills/bark-notify
```

Then point each agent runtime at that shared copy if the runtime needs its own
skills directory.

#### For One Specific Agent

If you only want one agent to use this skill, install or link it into that
agent's own skills directory. Examples:

```bash
mkdir -p ~/.codex/skills
ln -sf ~/.agents/skills/bark-notify ~/.codex/skills/bark-notify

mkdir -p ~/.claude/skills
ln -sf ~/.agents/skills/bark-notify ~/.claude/skills/bark-notify
```

For OpenCode or other agents, use the equivalent skills directory documented by
that runtime. The only requirement is that the skill root contains `SKILL.md`.

## Prompt Agents To Use It

Installing the skill only makes it available. To make agents use it proactively,
add this instruction to a global or project-level `AGENTS.md`, depending on
where you want the behavior:

```markdown
- Use the bark-notify SKILL to update the user on progress, especially when handling time-consuming tasks.
```

Put it in a global `AGENTS.md` when you want progress notifications across many
projects. Put it in a project `AGENTS.md` when only that repository should use
Bark progress updates.

## Configure Secrets

Keep Bark credentials local and private. Do not commit real keys.

Create `~/.config/bark-notify.env` manually. This is the preferred setup because the key never appears in a command or shell history:

```env
BARK_SERVER="https://api.day.app"
BARK_KEY="your-bark-device-key"
BARK_GROUP="Agents"
```

Or initialize it by securely reading the key from standard input:

```bash
read -rs BARK_KEY; printf '\n'
printf '%s\n' "$BARK_KEY" | python3 ~/.agents/skills/bark-notify/scripts/bark-notify.py --save-config --key-stdin
unset BARK_KEY
```

## Agent Identity

Agent group and icon metadata can live in `~/.config/bark-notify-agents.json`:

```json
{
  "codex": {
    "group": "Codex",
    "icon": "https://example.com/icons/codex.png"
  }
}
```

The icon must be a URL reachable by the receiving iOS device. Common hosting
choices include GitHub Pages, Cloudflare Pages, S3/R2, nginx, Caddy, or jsDelivr.
If no icon URL is configured, the notification is still sent without a custom icon.

Environment variables override the agent JSON:

```env
BARK_AGENT_CODEX_GROUP="Codex"
BARK_AGENT_CODEX_ICON="https://example.com/icons/codex.png"
```

## Agent Usage

After the skill is installed, an agent should load `SKILL.md` and run the bundled
script relative to the skill directory:

```bash
python3 scripts/bark-notify.py "Title" "Body"
python3 scripts/bark-notify.py --agent codex --level active "Build finished" "Codex completed the requested task"
python3 scripts/bark-notify.py --agent codex --level passive "Progress update" "Tests are running"
python3 scripts/bark-notify.py --ping
python3 scripts/bark-notify.py --doctor
python3 scripts/bark-notify.py --dry-run --agent codex --level active "Build finished" "Ready"
```

## Notification Levels

The skill uses Bark's notification interruption levels:

| Situation | Level |
| --- | --- |
| Progress update, background status, FYI | `passive` |
| Requested task completed, or user explicitly asked for a normal notification | `active` |
| Agent is blocked and needs user input soon | `timeSensitive` |
| Deployment failed, service unavailable, long task crashed | `timeSensitive` |
| User explicitly requested an emergency/critical alert | `critical` |

`passive` only enters Notification Center and does not light the screen. `active`
is Bark's normal visible notification and should be used for user-requested task
completion. `timeSensitive` can appear during a Focus mode when Bark and iOS
are authorized for it. `critical` can ignore silent/Focus modes and should only
be used for a real incident or an explicit emergency request.

On iOS, Bark must be allowed to deliver the corresponding notification type:

- Open iOS Settings, then Notifications, then Bark.
- Enable notifications for Bark.
- Enable Time Sensitive Notifications if you want `timeSensitive` alerts to break through Focus modes.
- Enable Critical Alerts if Bark shows that option and you intend to use `critical`.
- Focus modes can still affect what appears immediately; allow Bark in the relevant Focus if needed.

If the user wants a shell command, they may optionally create a local wrapper:

```bash
mkdir -p ~/.local/bin
ln -sf ~/.agents/skills/bark-notify/scripts/bark-notify.py ~/.local/bin/bark-notify
```

## Diagnose Before Sending

Use `--doctor` when an agent, icon, group, or server does not behave as
expected. It reports the resolved configuration and pings Bark without exposing
the device key. Use `--dry-run` to inspect the final push payload without
sending; the device key is always shown as `***`.

## Automatic ClawHub Publishing

The GitHub Actions workflow at `.github/workflows/clawhub-publish.yml` publishes
this skill whenever relevant files are pushed to `main`. It uses ClawHub's
official reusable workflow, which skips unchanged content and automatically
creates the next patch version when the skill changed.

Before the first run, add a repository Actions secret named `CLAWHUB_TOKEN`:

1. Create a ClawHub API token from the ClawHub web UI while signed in as the
   owner of this skill.
2. In GitHub, open **Settings → Secrets and variables → Actions** for this
   repository and create the `CLAWHUB_TOKEN` secret with that value.
3. Run **Publish Bark Notify to ClawHub** once from the Actions tab, or push a
   relevant change to `main`.

The token is only passed to the publishing workflow and must never be committed
to this repository.

## Develop And Test

```bash
python3 -m unittest discover -s tests
python3 -m py_compile scripts/bark-notify.py tests/test_cli.py
```
