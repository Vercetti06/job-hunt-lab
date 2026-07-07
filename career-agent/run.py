"""Launch the career agent locally: python run.py"""
import webbrowser
from threading import Timer

import uvicorn

HOST = "127.0.0.1"
PORT = 8420


def _open_browser():
    webbrowser.open(f"http://{HOST}:{PORT}/")


if __name__ == "__main__":
    Timer(1.2, _open_browser).start()
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
