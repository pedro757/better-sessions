#!/usr/bin/env python3
"""A tiny OpenAI-compatible chat completions server for recording the better-sessions demo.

The first user message of a conversation picks a scenario from scenarios.json:
  quick       short answer, the session finishes
  slow        streams for hours, the session keeps running
  permission  calls the shell tool (the sandbox asks for shell permission), so the session waits on the user
  question    calls the question tool, so the session waits on the user
  background  starts a background shell command and finishes its turn (OpenCode calls it idle; the plugin does not)
Title requests get the scenario's title.
"""
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = HERE / "requests.log"
lock = threading.Lock()


def scenarios():
    return json.loads((HERE / "scenarios.json").read_text())


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(part.get("text", "") for part in content if isinstance(part, dict))
    return ""


def log(entry):
    with lock, LOG.open("a") as handle:
        handle.write(json.dumps(entry)[:20000] + "\n")


def find_scenario(messages):
    table = scenarios()
    users = [text_of(m.get("content")) for m in messages if m.get("role") == "user"]
    for text in users:
        for prompt, scenario in table.items():
            if prompt in text:
                return prompt, scenario
    return None, {"kind": "quick", "title": (users[0][:40] if users else "Demo session")}


def is_title_request(body):
    system = " ".join(text_of(m.get("content")) for m in body.get("messages", []) if m.get("role") == "system")
    return "title" in system.lower() and not body.get("tools")


def tool_named(body, *names):
    for tool in body.get("tools") or []:
        name = tool.get("function", {}).get("name", "")
        if name in names:
            return name
    return None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.rstrip("/").endswith("/models"):
            self.json({"object": "list", "data": [{"id": "demo", "object": "model", "owned_by": "demo"}]})
            return
        self.json({"ok": True})

    def json(self, value, status=200):
        data = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        messages = body.get("messages", [])
        prompt, scenario = find_scenario(messages)
        title = is_title_request(body)
        log({
            "at": time.time(),
            "title": title,
            "prompt": prompt,
            "stream": body.get("stream"),
            "tools": [t.get("function", {}).get("name") for t in body.get("tools") or []],
            "messages": [{"role": m.get("role"), "text": text_of(m.get("content"))[:300], "tool_calls": m.get("tool_calls")} for m in messages],
            "tool_schemas": {
                t.get("function", {}).get("name"): t.get("function", {}).get("parameters")
                for t in body.get("tools") or []
                if t.get("function", {}).get("name") in ("question", "shell", "bash")
            },
        })
        tool_results = [m for m in messages if m.get("role") == "tool"]
        if title:
            self.reply(body, text=scenario.get("title", "Demo session"))
            return
        kind = scenario.get("kind", "quick")
        if kind == "slow":
            self.reply(body, text=scenario.get("reply", "Working through the changes step by step."), slow=True)
            return
        if kind == "permission" and not tool_results:
            name = tool_named(body, "shell", "bash")
            if name:
                self.reply(body, tool=(name, {"command": scenario.get("command", "pnpm test")}))
                return
        if kind == "background" and not tool_results:
            name = tool_named(body, "shell", "bash")
            if name:
                self.reply(body, tool=(name, {"command": scenario.get("command", "sleep 7200"), "background": True}))
                return
        if kind == "question" and not tool_results:
            name = tool_named(body, "question")
            if name:
                self.reply(body, tool=(name, scenario.get("question_args", {})))
                return
        self.reply(body, text=scenario.get("reply", "Done. The change is in place and the tests pass."))

    def reply(self, body, text=None, tool=None, slow=False):
        stream = body.get("stream", False)
        created = int(time.time())
        base = {"id": f"chatcmpl-{created}", "object": "chat.completion.chunk", "created": created, "model": "demo"}
        usage = {"prompt_tokens": 1200, "completion_tokens": 80, "total_tokens": 1280}
        if not stream:
            message = {"role": "assistant", "content": text or ""}
            if tool:
                message["tool_calls"] = [{"id": "call_demo", "type": "function", "function": {"name": tool[0], "arguments": json.dumps(tool[1])}}]
            self.json({**base, "object": "chat.completion", "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if tool else "stop"}], "usage": usage})
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        def send(choice, extra=None):
            chunk = {**base, "choices": [choice], **(extra or {})}
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            self.wfile.flush()

        try:
            send({"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None})
            if tool:
                send({"index": 0, "delta": {"tool_calls": [{"index": 0, "id": "call_demo", "type": "function", "function": {"name": tool[0], "arguments": json.dumps(tool[1])}}]}, "finish_reason": None})
                send({"index": 0, "delta": {}, "finish_reason": "tool_calls"}, {"usage": usage})
            else:
                words = (text or "").split(" ")
                for index, word in enumerate(words):
                    send({"index": 0, "delta": {"content": ("" if index == 0 else " ") + word}, "finish_reason": None})
                    time.sleep(0.02)
                if slow:
                    # Keep the session running: one more word every few seconds, for hours.
                    for index in range(4000):
                        time.sleep(3)
                        send({"index": 0, "delta": {"content": " ." if index % 20 else "\n\nStill working on it."}, "finish_reason": None})
                send({"index": 0, "delta": {}, "finish_reason": "stop"}, {"usage": usage})
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        self.close_connection = True


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 47390
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
