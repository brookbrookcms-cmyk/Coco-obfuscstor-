# Coco code-gated loader and Discord bot prototype

This prototype stores a Luau script and its original link in a private SQLite database. It generates a small Delta-compatible loader. The loader needs an access code to fetch and run the script. The same code reveals the original link. This is access control, **not Luraph-style obfuscation**: someone who can run the script can capture the fetched source or its network request.

## Requirements

- Python 3.9 or newer. The Discord bot uses `discord.py` from `requirements.txt`.
- An HTTPS deployment reachable from Delta for real use. `localhost` works only for local API testing.
- A local copy of the Luau script and its original HTTPS URL.

## Try it locally

Run these commands from the repository folder in a terminal:

```sh
python3 coco.py --db coco.sqlite3 add \
  --file example.lua \
  --source-url https://example.com/original.lua \
  --base-url http://127.0.0.1:8000 \
  --output loader.lua
```

Enter an access code of at least 8 characters when prompted. Keep the printed script ID. Start the server in another terminal:

```sh
python3 coco.py --db coco.sqlite3 serve
```

Check the gate (replace `ID` and `YOUR_CODE`):

```sh
curl 'http://127.0.0.1:8000/reveal/ID?code=YOUR_CODE'
curl 'http://127.0.0.1:8000/script/ID?code=YOUR_CODE'
```

The first request returns the original URL; the second returns the stored Luau script. A wrong code returns HTTP 403.

## Discord `/obf` command

1. Create a Discord application and bot in the Discord Developer Portal. Invite the bot to your server with the `bot` and `applications.commands` scopes. Keep its token private.
2. Deploy the Python server above at a public HTTPS address with persistent storage for `coco.sqlite3`. Start it with `python3 coco.py serve --host 0.0.0.0 --port 8000` behind your HTTPS proxy.
3. Install and start the bot in a second process:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
export DISCORD_TOKEN='your-discord-bot-token'
export COCO_BASE_URL='https://your-server.example'
export COCO_DB='coco.sqlite3'
export DISCORD_GUILD_ID='your-server-id'
.venv/bin/python bot.py
```

`DISCORD_GUILD_ID` is optional, but setting it makes `/obf` appear quickly in that server. Without it, Discord may take time to show a global command. The bot and server must use the **same persistent SQLite file**; if they run on separate machines, use shared storage or put them on the same host.

In Discord, type `/obf`. The form asks for your Luau script (up to 4,000 characters), the access code that the loader will require, and the script's original HTTPS link. Submit it. The bot privately replies with `loader.lua`. It does not include your access code in the loader.

To test locally, run `.venv/bin/python -m unittest -v test_coco.py`.

## Use with Delta

Deploy the server behind HTTPS, keep `coco.sqlite3` on private persistent storage, and use your HTTPS domain for `--base-url` when generating the loader. In Delta, set the code and run the generated `loader.lua`:

```lua
getgenv().COCO_CODE = "your-access-code"
-- paste the contents of loader.lua below this line
```

The server must stay online. If the public URL changes, regenerate the loader with the new `--base-url`. The original URL is metadata you supply; this version runs the stored snapshot of the script. To update it, run `add` again with the new file.

## Limits

The code travels in a URL query string in this prototype, so use HTTPS and do not put sensitive or valuable secrets in the code. The server has no rate limiting or admin interface yet. Do not commit the SQLite database or private scripts to a public repository. Anyone with a valid code can retrieve the source and original link; no client-side loader can prevent that.
