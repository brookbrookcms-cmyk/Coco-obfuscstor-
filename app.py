"""Run the HTTP gate and Discord bot together in one Railway service."""

import os
from pathlib import Path
from threading import Thread
from http.server import ThreadingHTTPServer

import bot
from coco import connect, handler_factory


def start_http(db_path, port):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    connect(db_path).close()
    server = ThreadingHTTPServer(("0.0.0.0", port), handler_factory(db_path))
    Thread(target=server.serve_forever, daemon=True).start()
    return server


def main():
    if not os.environ.get("DISCORD_TOKEN") or not os.environ.get("COCO_BASE_URL"):
        raise SystemExit("Set DISCORD_TOKEN and COCO_BASE_URL in Railway Variables")
    db_path = os.environ.get("COCO_DB", "coco.sqlite3")
    server = start_http(db_path, int(os.environ.get("PORT", "8000")))
    try:
        bot.main()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
