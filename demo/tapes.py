#!/usr/bin/env python3
"""Writes the VHS tapes for the better-sessions demo. Usage: tapes.py  (writes tapes/*.tape)"""
from pathlib import Path

B = Path("/tmp/bs-demo")
OUT = Path("media")
(B / "tapes").mkdir(exist_ok=True)
(B / OUT).mkdir(exist_ok=True)

HEADER = """Output {out}/{name}.gif
Set Shell "bash"
Set FontFamily "CaskaydiaMono NFM"
Set FontSize 16
Set Width 1200
Set Height 820
Set Padding 20
Set WindowBar Colorful
Set BorderRadius 10
Set Theme "tokyonight"
Set TypingSpeed 70ms
Set CursorBlink false
Hide
Type "source /tmp/bs-demo/env.sh && cd /tmp/bs-demo/acme-web && python3 /tmp/bs-demo/prep.py {prep} && clear && opencode"
Enter
Sleep 7s
Show
"""

TAPES = {
    "tabs": ("default", """
Sleep 1.5s
Ctrl+S
Sleep 3.5s
Screenshot {out}/active.png
Sleep 1s
Tab
Sleep 2.5s
Screenshot {out}/settled.png
Sleep 500ms
Tab
Sleep 2.5s
Screenshot {out}/snoozed.png
Sleep 500ms
Tab
Sleep 2.5s
"""),
    "actions": ("default", """
Sleep 1s
Ctrl+S
Sleep 2s
Down 2
Sleep 1s
Ctrl+E
Sleep 2s
Down 3
Sleep 1s
Ctrl+E
Sleep 500ms
Screenshot {out}/settle-blocked.png
Sleep 2.5s
Up 2
Sleep 1s
Ctrl+T
Sleep 1.5s
Screenshot {out}/snooze-menu.png
Down
Sleep 800ms
Enter
Sleep 2s
Ctrl+U
Ctrl+U
Down 2
Sleep 1s
Ctrl+T
Sleep 1.2s
Up
Sleep 800ms
Enter
Sleep 1s
Type "45m"
Sleep 800ms
Enter
Sleep 2s
Tab
Sleep 500ms
Tab
Sleep 2.5s
Ctrl+A
Sleep 2s
Tab
Sleep 3s
"""),
    "jump": ("default", """
Sleep 1s
Ctrl+S
Sleep 1.5s
Ctrl+S
Sleep 2.2s
Type "f"
Sleep 3s
Ctrl+S
Sleep 1.5s
Tab
Sleep 1.5s
Ctrl+D
Sleep 1.2s
Ctrl+D
Sleep 1.2s
Ctrl+U
Sleep 1.5s
Ctrl+S
Sleep 2.2s
Screenshot {out}/jump-labels.png
Type "s"
Sleep 3s
"""),
    "message": ("default", """
Sleep 1s
Ctrl+S
Sleep 1.5s
Tab
Sleep 1.5s
Down
Sleep 1.2s
Enter
Sleep 2.5s
Type "Also add them to the docs pages"
Sleep 800ms
Enter
Sleep 3.5s
Ctrl+S
Sleep 3s
Tab
Sleep 2.5s
"""),
    "wake": ("wake", """
Sleep 500ms
Ctrl+S
Sleep 1s
Tab
Sleep 400ms
Tab
Sleep 9s
Shift+Tab
Sleep 400ms
Shift+Tab
Sleep 3.5s
"""),
    "manage": ("default", """
Sleep 1s
Ctrl+S
Sleep 1.5s
Type "dashboard"
Sleep 2.5s
Tab
Sleep 2s
Shift+Tab
Sleep 1s
Backspace 9
Sleep 1.5s
Ctrl+U
Ctrl+U
Sleep 500ms
Down 5
Sleep 1s
Ctrl+F
Sleep 2s
Ctrl+R
Sleep 1.2s
Type " in every package"
Sleep 800ms
Enter
Sleep 2s
Ctrl+X
Sleep 1.8s
Ctrl+X
Sleep 2.5s
"""),
}

for name, (prep, body) in TAPES.items():
    text = HEADER.format(out=OUT, name=name, prep=prep) + body.format(out=OUT)
    (B / "tapes" / f"{name}.tape").write_text(text)
    print("wrote", name)
