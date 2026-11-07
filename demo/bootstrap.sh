#!/usr/bin/env bash
# Builds the recording sandbox in /tmp/bs-demo: a separate OpenCode (its own XDG config, data and state, and its own
# server port), a demo git project, a mock model and a copy of this plugin. Your real OpenCode is not touched.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
plugin=$(cd "$here/.." && pwd)
B=/tmp/bs-demo

mkdir -p "$B"/home/{config,data,state,cache}/opencode "$B"/mock "$B"/media
cp "$here/mock.py" "$B/mock/"
cp "$here/setup.py" "$here/prep.py" "$here/tapes.py" "$B/"

cat > "$B/env.sh" <<'EOF'
export XDG_CONFIG_HOME=/tmp/bs-demo/home/config XDG_DATA_HOME=/tmp/bs-demo/home/data
export XDG_STATE_HOME=/tmp/bs-demo/home/state XDG_CACHE_HOME=/tmp/bs-demo/home/cache
unset OPENCODE_CLI_CONFIG_CONTENT
EOF

# Its own server port, so it never attaches to a running OpenCode.
echo '{ "port": 47391 }' > "$B/home/config/opencode/service.json"

cat > "$B/home/config/opencode/opencode.jsonc" <<'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "update": "disable",
  "share": "disabled",
  "snapshots": false,
  "model": "mock/demo",
  "agents": { "title": { "model": "mock/demo" } },
  "permissions": [
    { "action": "shell", "resource": "*", "effect": "ask" },
    { "action": "shell", "resource": "sleep *", "effect": "allow" }
  ],
  "providers": {
    "mock": {
      "name": "Demo",
      "package": "@opencode/ai/providers/openai-compatible",
      "settings": { "baseURL": "http://127.0.0.1:47390/v1", "apiKey": "demo" },
      "models": {
        "demo": { "name": "Demo model", "capabilities": { "tools": true }, "limit": { "context": 200000, "output": 32000 } }
      }
    }
  }
}
EOF

cat > "$B/home/config/opencode/cli.json" <<'EOF'
{
  "theme": { "name": "tokyonight", "mode": "dark" },
  "plugins": ["-opencode.notifications"],
  "tabs": { "enabled": false, "mode": "off" },
  "keybinds": { "session.list": "ctrl+s" },
  "mouse": false
}
EOF

rm -rf "$B/home/config/opencode/plugins/better-sessions"
mkdir -p "$B/home/config/opencode/plugins/better-sessions"
cp -r "$plugin/tui.tsx" "$plugin/src" "$B/home/config/opencode/plugins/better-sessions/"

if [ ! -d "$B/acme-web/.git" ]; then
  mkdir -p "$B/acme-web"
  (cd "$B/acme-web" && git init -q && printf '# acme-web\n' > README.md && git add . &&
    git -c user.name=demo -c user.email=demo@example.com commit -qm init)
fi
echo '{}' > "$B/mock/scenarios.json"
echo "Sandbox ready in $B"
