from datetime import datetime, timedelta

import discord

from .utils.misc import escape_markdown, format_size

# DDNet guild IDs
GUILD_DDNET = 252358080522747904
CHAN_JOIN_LEAVE = 255191476315750401
CHAN_LOG = 364164149359411201


class MemberLog:
    def __init__(self, bot):
        self.bot = bot

    async def on_member_join(self, member):
        guild = member.guild
        if guild.id != GUILD_DDNET:
            return

        if member.bot:
            return

        msg = f'📥 {member.mention}, Welcome to <:ddnet:395756335892922379> ' \
              '**DDraceNetwork\'s Discord**! Please make sure to read <#311192969493348362>. ' \
              'Have a great time here <:happy:395753933089406976>'
        join_leave = self.bot.get_channel(CHAN_JOIN_LEAVE)
        await join_leave.send(msg)

    async def on_member_remove(self, member):
        def predicate(event):
            now = datetime.utcnow() - timedelta(seconds=5)
            return event.target == member and event.created_at >= now

        guild = member.guild
        if guild.id != GUILD_DDNET:
            return

        if member.bot:
            return

        msg = f'📤 **{escape_markdown(member.name)}#{member.discriminator}** '

        event = await guild.audit_logs().find(predicate)
        if event:
            if event.action == discord.AuditLogAction.kick:
                msg += f'has been **kicked** by {event.user.mention} '
                if event.reason:
                    reason = event.reason.replace('\n', ' ')
                    msg += f'with reason **{reason}** '

                msg += '👉 🚪'

            if event.action == discord.AuditLogAction.ban:
                msg += f'has been **banned** by {event.user.mention} '
                if event.reason:
                    reason = event.reason.replace('\n', ' ')
                    msg += f'with reason **{event.reason}** '

                msg += '<:banhammer:392813948858269696>'

        else:
            msg += 'just **left** the server <:mmm:395753965410582538>'

        join_leave = self.bot.get_channel(CHAN_JOIN_LEAVE)
        await join_leave.send(msg)

    async def on_message_delete(self, message):
        if not message.guild or message.guild.id != GUILD_DDNET:
            return

        deleted_at = datetime.utcnow()
        description = f'**Message sent by {message.author.mention} deleted in <#{message.channel.id}>**'

        if message.content:
            description += '\n' + message.content

        if message.attachments:
            attachment = message.attachments[0]
            filesize, unit = format_size(attachment.size)
            description += f'\n[Attachment: {attachment.filename} ({filesize}{unit})]({attachment.url})'

        embed = discord.Embed(description=description, color=0xDD2E44)
        embed.set_author(name=f'{message.author} | ID: {message.id}',
                         icon_url=message.author.avatar_url_as(format='png'))
        footer = f'Sent: {message.created_at.strftime("%m/%d/%Y %I:%M %p")} | ' \
                 f'Deleted: {deleted_at.strftime("%m/%d/%Y %I:%M %p")}'
        embed.set_footer(text=footer)
        log_channel = self.bot.get_channel(CHAN_LOG)
        await log_channel.send(embed=embed)


def setup(bot):
    bot.add_cog(MemberLog(bot))
