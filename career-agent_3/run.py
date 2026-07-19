"""Launch the career agent: python run.py

Binds to 127.0.0.1 by default (laptop use). Set CAREER_AGENT_HOST=0.0.0.0 in
.env to expose it on a VM — see the README's EC2 section, and set
BASIC_AUTH_USERNAME/PASSWORD too if you do, since the app holds personal data
and can spend your Anthropic API credits.
"""
import webbrowser
from threading import Timer

import uvicorn

from app.config import settings

HOST = settings.host
PORT = settings.port
_IS_LOCAL = HOST in ("127.0.0.1", "localhost")


def _open_browser():
    webbrowser.open(f"http://{HOST}:{PORT}/")


if __name__ == "__main__":
    if _IS_LOCAL:
        Timer(1.2, _open_browser).start()
    else:
        print(f"Career Agent listening on http://{HOST}:{PORT}/ (not opening a local browser — headless host).")
        if not settings.basic_auth_enabled:
            print("WARNING: BASIC_AUTH_USERNAME/PASSWORD are not set. This is exposed with no authentication.")
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
