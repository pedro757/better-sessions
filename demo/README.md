# Recording the demo

The GIFs and screenshots in `media/` come from a sandboxed OpenCode with made-up sessions. Nothing in it touches
a real OpenCode install: it uses its own XDG config, data and state directories under `/tmp/bs-demo` and its own
server port, and it talks to a local mock model instead of a provider.

| File           | What it does                                                                                              |
| -------------- | --------------------------------------------------------------------------------------------------------- |
| `bootstrap.sh` | Creates `/tmp/bs-demo`: the sandbox config, a demo git project (`acme-web`) and a copy of the plugin      |
| `mock.py`      | An OpenAI-compatible chat completions server. Each prompt picks a scenario: answer, keep streaming (running), call the shell tool (permission), call the question tool, or start a background command |
| `setup.py`     | Creates the demo sessions, backdates the older ones in the sandbox database, and writes the plugin state  |
| `prep.py`      | Resets the plugin state before each recording                                                             |
| `tapes.py`     | Writes the [VHS](https://github.com/charmbracelet/vhs) tapes                                              |

```sh
demo/bootstrap.sh
python3 /tmp/bs-demo/mock/mock.py 47390 &      # keep it running while recording
python3 /tmp/bs-demo/setup.py
cd /tmp/bs-demo && python3 tapes.py
# manage deletes a session, so it goes last.
for t in tabs actions jump message wake manage; do
  mise exec vhs@latest ttyd@latest -- vhs tapes/$t.tape
done
```

The output lands in `/tmp/bs-demo/media`. Stop the sandbox server afterwards with
`source /tmp/bs-demo/env.sh && opencode service stop`.
