from typing import Dict, List

import discord
from d_utils.ext import commands, menus


class Pages(menus.Menu):
    def __init__(self, pages: List[discord.Embed]):
        super().__init__(clear_reactions_after=True)

        self.pages = pages
        self.current_page = 0
        self.num_pages = len(pages)

    def should_add_reactions(self) -> bool:
        return self.num_pages > 1

    def partial_message(self) -> Dict:
        return {
            'content': f'*Page {self.current_page + 1}/{self.num_pages}*',
            'embed': self.pages[self.current_page]
        }

    async def send_initial_message(self, ctx: commands.Context, _: discord.TextChannel) -> discord.Message:
        message = self.partial_message()
        return await ctx.send(**message)

    async def update_page(self, step: int):
        self.current_page = (self.current_page + step) % self.num_pages
        message = self.partial_message()
        await self.message.edit(**message)

    @menus.button('◀️')
    async def on_previous_page(self, _: discord.RawReactionActionEvent):
        await self.update_page(-1)

    @menus.button('▶️')
    async def on_next_page(self, _: discord.RawReactionActionEvent):
        await self.update_page(1)
