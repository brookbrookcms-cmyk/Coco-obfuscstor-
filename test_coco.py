import asyncio
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen
from unittest.mock import AsyncMock

import bot
import coco


class CocoTests(unittest.TestCase):
    def test_code_gate_and_link_reveal(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "scripts.sqlite3")
            script_id = coco.store_script(
                db_path, 'print("hello")', "https://example.com/real.lua", "testcode123"
            )
            server = ThreadingHTTPServer(("127.0.0.1", 0), coco.handler_factory(db_path))
            worker = Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                self.assertEqual(
                    urlopen(f"{base}/script/{script_id}?code=testcode123").read(),
                    b'print("hello")',
                )
                self.assertEqual(
                    urlopen(f"{base}/reveal/{script_id}?code=testcode123").read(),
                    b"https://example.com/real.lua",
                )
                with self.assertRaises(HTTPError) as error:
                    urlopen(f"{base}/script/{script_id}?code=wrongcode")
                self.assertEqual(error.exception.code, 403)
            finally:
                server.shutdown()
                server.server_close()
                worker.join()

    def test_obf_modal_creates_loader_with_code_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "scripts.sqlite3")
            modal = bot.ObfModal(db_path, "https://host.example")
            modal.script._value = 'print("from discord")'
            modal.code._value = "discordcode123"
            modal.original_url._value = "https://example.com/source.lua"
            response = type("Response", (), {"send_message": AsyncMock()})()
            interaction = type("Interaction", (), {"response": response})()
            asyncio.run(modal.on_submit(interaction))
            response.send_message.assert_awaited_once()
            args, kwargs = response.send_message.await_args
            self.assertTrue(kwargs["ephemeral"])
            loader = kwargs["file"].fp.getvalue().decode()
            self.assertIn('getgenv().COCO_CODE', loader)
            self.assertIn('https://host.example/script/', loader)
            self.assertNotIn("discordcode123", loader)
            with coco.connect(db_path) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM scripts").fetchone()[0], 1)
            self.assertEqual(bot.CocoBot(db_path, "https://host.example").tree.get_command("obf").name, "obf")

    def test_invalid_url_does_not_store_script(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "scripts.sqlite3")
            with self.assertRaises(ValueError):
                coco.store_script(db_path, "print(1)", "http://example.com/a.lua", "longcode123")
            self.assertFalse(Path(db_path).exists())


if __name__ == "__main__":
    unittest.main()
