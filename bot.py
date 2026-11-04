"""Discord /obf command for the Coco code-gated loader prototype."""

import io
import os

import discord
from discord import app_commands

from coco import make_loader, store_script


class ObfModal(discord.ui.Modal, title="Create protected script"):
    script = discord.ui.TextInput(
        label="Luau script", style=discord.TextStyle.paragraph,
        placeholder="Paste the script you want to protect", max_length=4000,
    )
    code = discord.ui.TextInput(
        label="Access code", placeholder="At least 8 characters",
        min_length=8, max_length=100,
    )
    original_url = discord.ui.TextInput(
        label="Original HTTPS script link", placeholder="https://example.com/script.lua",
        max_length=1000,
    )

    def __init__(self, db_path, base_url):
        super().__init__()
        self.db_path = db_path
        self.base_url = base_url

    async def on_submit(self, interaction: discord.Interaction):
        try:
            script_id = store_script(
                self.db_path, self.script.value, self.original_url.value, self.code.value
            )
            loader = make_loader(self.base_url, script_id)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        file = discord.File(io.BytesIO(loader.encode("utf-8")), filename="loader.lua")
        reveal_url = f"{self.base_url.rstrip('/')}/reveal/{script_id}"
        await interaction.response.send_message(
            f"Your loader is attached. In Delta, set `getgenv().COCO_CODE` to your code "
            f"before running it. To reveal the original link, open `{reveal_url}?code=YOUR_CODE`. "
            "Keep your code private.",
            file=file, ephemeral=True,
        )


class CocoBot(discord.Client):
    def __init__(self, db_path, base_url, guild_id=None):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.db_path = db_path
        self.base_url = base_url
        self.guild_id = guild_id

        @self.tree.command(name="obf", description="Create a code-gated Luau loader")
        async def obf(interaction: discord.Interaction):
            await interaction.response.send_modal(ObfModal(self.db_path, self.base_url))

    async def setup_hook(self):
        if self.guild_id:
            guild = discord.Object(id=self.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


def main():
    token = os.environ.get("DISCORD_TOKEN")
    base_url = os.environ.get("COCO_BASE_URL")
    if not token or not base_url:
        raise SystemExit("Set DISCORD_TOKEN and COCO_BASE_URL")
    if not base_url.startswith("https://"):
        raise SystemExit("COCO_BASE_URL must start with https:// for Delta")
    guild_id = os.environ.get("DISCORD_GUILD_ID")
    bot = CocoBot(os.environ.get("COCO_DB", "coco.sqlite3"), base_url,
                  int(guild_id) if guild_id else None)
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
