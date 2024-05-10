from typing import Iterable

import discord
from config import GUILD_DDNET, CHAN_SKIN_SUBMIT, ROLE_ADMIN


def is_staff(member: discord.Member, roles: Iterable) -> bool:
    return any(r.id in roles for r in member.roles)


def check_if_staff(message: discord.Message, roles: Iterable):
    author = message.author
    return (message.guild is None or message.guild.id != GUILD_DDNET or
            message.channel.id != CHAN_SKIN_SUBMIT or is_staff(author, roles))


def check_admin(ctx):
    return ctx.guild is None or ctx.guild.id != GUILD_DDNET or ctx.author.get_role(ROLE_ADMIN) is None
