#!/usr/bin/env python3
"""Small code-gated Luau loader prototype. Uses only Python's standard library."""

import argparse
import getpass
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


def connect(path):
    db = sqlite3.connect(path)
    db.execute("""CREATE TABLE IF NOT EXISTS scripts (
        id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        source_url TEXT NOT NULL,
        salt BLOB NOT NULL,
        code_hash BLOB NOT NULL
    )""")
    db.commit()
    return db


def key_hash(code, salt):
    return hashlib.pbkdf2_hmac("sha256", code.encode("utf-8"), salt, 200_000)


def make_loader(base_url, script_id):
    base = urlparse(base_url)
    if base.scheme not in ("http", "https") or not base.netloc:
        raise ValueError("Server URL must be HTTP(S)")
    endpoint = base_url.rstrip("/") + "/script/" + script_id
    return f'''-- Coco loader prototype. Enter your code in Delta before running this file:
-- getgenv().COCO_CODE = "your-code"
local code = getgenv().COCO_CODE
assert(type(code) == "string" and #code > 0, "Set getgenv().COCO_CODE first")
local url = {json.dumps(endpoint)} .. "?code=" .. game:GetService("HttpService"):UrlEncode(code)
local source = game:HttpGet(url)
local fn, err = loadstring(source)
assert(fn, err)
fn()
'''


def store_script(db_path, source, source_url, code):
    if not source.strip():
        raise ValueError("Script is empty")
    parsed = urlparse(source_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Original link must be an HTTPS URL")
    if len(code) < 8:
        raise ValueError("Use an access code of at least 8 characters")
    salt = secrets.token_bytes(16)
    script_id = secrets.token_urlsafe(12)
    with connect(db_path) as db:
        db.execute("INSERT INTO scripts VALUES (?, ?, ?, ?, ?)",
                   (script_id, source, source_url, salt, key_hash(code, salt)))
    return script_id


def add(args):
    source = Path(args.file).read_text(encoding="utf-8")
    code = getpass.getpass("Access code: ")
    try:
        make_loader(args.base_url, "example")  # Validate before storing anything.
        script_id = store_script(args.db, source, args.source_url, code)
        loader = make_loader(args.base_url, script_id)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    Path(args.output).write_text(loader, encoding="utf-8")
    print(f"Wrote loader: {args.output}")
    print(f"Script ID: {script_id}")
    print(f"Reveal URL: {args.base_url.rstrip('/')}/reveal/{script_id}")


def handler_factory(db_path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # The request URL contains the access code. Do not log it.
            pass

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self.reply(200, "ok")
                return
            parts = parsed.path.strip("/").split("/")
            if len(parts) != 2 or parts[0] not in ("script", "reveal"):
                self.reply(404, "Not found")
                return
            script_id = parts[1]
            code = parse_qs(parsed.query).get("code", [""])[0]
            with connect(db_path) as db:
                row = db.execute("SELECT source, source_url, salt, code_hash FROM scripts WHERE id = ?",
                                 (script_id,)).fetchone()
            if not row or not code or not hmac.compare_digest(key_hash(code, row[2]), row[3]):
                self.reply(403, "Invalid code or script ID")
                return
            self.reply(200, row[0] if parts[0] == "script" else row[1])

        def reply(self, status, body):
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="coco.sqlite3", help="Private SQLite database path")
    subs = parser.add_subparsers(dest="command", required=True)
    add_parser = subs.add_parser("add", help="Store a script and generate its Delta loader")
    add_parser.add_argument("--file", required=True, help="Local Luau script")
    add_parser.add_argument("--source-url", required=True, help="Original HTTPS link to reveal")
    add_parser.add_argument("--base-url", required=True, help="Public URL of this server")
    add_parser.add_argument("--output", default="loader.lua")
    serve_parser = subs.add_parser("serve", help="Start the code-gated server")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.command == "add":
        add(args)
    else:
        print(f"Serving on http://{args.host}:{args.port}", flush=True)
        ThreadingHTTPServer((args.host, args.port), handler_factory(args.db)).serve_forever()


if __name__ == "__main__":
    main()
