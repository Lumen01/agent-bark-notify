# Bark Notify Skill

Skill for sending [Bark](https://github.com/Finb/Bark) push notifications from agents.

This repository is a skill first. The notification helper is a bundled script at
`scripts/bark-notify.py`, not a standalone package that must be installed from PyPI.

## Install The Skill

### For Multiple Agents

If you want Codex, Claude, OpenCode, and other agents to share this skill, install
it once under `~/.agents`:

```bash
git clone https://github.com/Lumen01/agent-bark-notify.git ~/.agents/skills/bark-notify
```

Then point each agent runtime at that shared copy if the runtime needs its own
skills directory.

### For One Specific Agent

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

## Configure Secrets

Keep Bark credentials local and private. Do not commit real keys.

Create `~/.config/bark-notify.env` manually:

```env
BARK_SERVER="https://api.day.app"
BARK_KEY="your-bark-device-key"
BARK_GROUP="Agents"
```

Or initialize it with:

```bash
python3 ~/.agents/skills/bark-notify/scripts/bark-notify.py --save-config --server "https://api.day.app" --key "your-bark-device-key"
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
python3 scripts/bark-notify.py --agent codex "Build finished" "Codex completed the requested task"
python3 scripts/bark-notify.py --ping
```

If the user wants a shell command, they may optionally create a local wrapper:

```bash
mkdir -p ~/.local/bin
ln -sf ~/.agents/skills/bark-notify/scripts/bark-notify.py ~/.local/bin/bark-notify
```

## Develop And Test

```bash
python3 -m unittest discover -s tests
python3 -m py_compile scripts/bark-notify.py tests/test_cli.py
```
