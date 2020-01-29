from typing import Dict, List

import discord
from discord.ext import commands, menus


class Pages(menus.Menu):
    def __init__(self, pages: List[discord.Embed]):
        try:
            super().__init__(clear_reactions_after=True, check_embeds=True)
        except menus.MenuError:
            raise discord.Forbidden

        self.pages = pages
        self.num_pages = len(pages)

    def should_add_reactions(self) -> bool:
        return self.num_pages > 1

    def partial_message(self, page: int) -> Dict:
        return {
            'content': f'*Page {page + 1}/{self.num_pages}*',
            'embed': self.pages[page]
        }

    async def send_initial_message(self, ctx: commands.Context, channel: discord.TextChannel) -> discord.Message:
        self.current_page = page = 0
        message = self.partial_message(page)
        return await ctx.send(**message)

    async def update_page(self, step: int):
        self.current_page = page = (self.current_page + step) % self.num_pages
        message = self.partial_message(page)
        await self.message.edit(**message)

    @menus.button('◀️')
    async def on_previous_page(self, payload: discord.RawReactionActionEvent):
        await self.update_page(-1)

    @menus.button('▶️')
    async def on_next_page(self, payload: discord.RawReactionActionEvent):
        await self.update_page(1)
