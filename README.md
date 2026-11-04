# Coco code-gated loader prototype

This prototype stores a Luau script and its original link in a private SQLite database. It generates a small Delta-compatible loader. The loader needs an access code to fetch and run the script. The same code reveals the original link. This is access control, **not Luraph-style obfuscation**: someone who can run the script can capture the fetched source or its network request.

## Requirements

- Python 3.9 or newer; no packages to install.
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

## Use with Delta

Deploy the server behind HTTPS, keep `coco.sqlite3` on private persistent storage, and use your HTTPS domain for `--base-url` when generating the loader. In Delta, set the code and run the generated `loader.lua`:

```lua
getgenv().COCO_CODE = "your-access-code"
-- paste the contents of loader.lua below this line
```

The server must stay online. If the public URL changes, regenerate the loader with the new `--base-url`. The original URL is metadata you supply; this version runs the stored snapshot of the script. To update it, run `add` again with the new file.

## Limits

The code travels in a URL query string in this prototype, so use HTTPS and do not put sensitive or valuable secrets in the code. The server has no rate limiting or admin interface yet. Do not commit the SQLite database or private scripts to a public repository. Anyone with a valid code can retrieve the source and original link; no client-side loader can prevent that.
