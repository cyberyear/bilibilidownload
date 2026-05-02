from __future__ import annotations

import threading
import time
import webbrowser

import uvicorn


HOST = "127.0.0.1"
PORT = 8000


def run_server() -> None:
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False, log_level="warning")


def main() -> None:
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    time.sleep(1.5)
    webbrowser.open(f"http://{HOST}:{PORT}")

    while thread.is_alive():
        time.sleep(1)


if __name__ == "__main__":
    main()
