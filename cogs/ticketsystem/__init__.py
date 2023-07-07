import discord
import json
import os
from typing import Union
import re
import requests

from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone

from cogs.ticketsystem.buttons import CreateButton
from cogs.ticketsystem.close import CloseButton, ModeratorButton
from utils.transcript import transcript

GUILD_DDNET            = 252358080522747904
CAT_TICKETS            = 1124657181363556403
CAT_MODERATION         = 968484659950403585
CHAN_MODERATOR         = 345588928482508801
CHAN_T_TRANSCRIPTS     = 1124657432816267394
CHAN_INFO              = 1124657351442579486
ROLE_ADMIN             = 293495272892399616
ROLE_DISCORD_MODERATOR = 737776812234506270
ROLE_MODERATOR         = 252523225810993153


def is_staff(member: discord.Member) -> bool:
    return any(role.id in (ROLE_ADMIN, ROLE_DISCORD_MODERATOR, ROLE_MODERATOR) for role in member.roles)


def server_link(addr):
    jsondata = requests.get("https://info.ddnet.org/info", timeout=1).json()

    def extract_servers(json, tags, network):
        server_list = None
        if network == "ddnet":
            server_list = json.get('servers')
        elif network == "kog":
            server_list = json.get('servers-kog')

        all_servers = []
        for address in server_list:
            server = address.get('servers')
            for tag in tags:
                server_lists = server.get(tag)
                if server_lists is not None:
                    all_servers += server_lists
        return all_servers

    ddnet = extract_servers(jsondata, ['DDNet', 'Test', 'Tutorial'], "ddnet")
    ddnetpvp = extract_servers(jsondata, ['Block', 'Infection', 'iCTF', 'gCTF', 'Vanilla', 'zCatch',
                                          'TeeWare', 'TeeSmash', 'Foot', 'xPanic', 'Monster'], "ddnet")
    nobyfng = extract_servers(jsondata, ['FNG'], "ddnet")
    kog = extract_servers(jsondata, ['Gores', 'TestGores'], "kog")

    ipv4_addr = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,4}')
    re_match = ipv4_addr.findall(addr)

    if re_match[0] in ddnet:
        message_text = f'{re_match[0]} is an official DDNet server. ' \
                       f'\n<steam://run/412220//{re_match[0]}>/'
    elif re_match[0] in ddnetpvp:
        message_text = f'{re_match[0]} is an official DDNet PvP server. ' \
                       f'\n<steam://run/412220//{re_match[0]}/'
    elif re_match[0] in kog:
        message_text = f'{re_match[0]} appears to be a KoG server. DDNet and KoG aren\'t affiliated. ' \
                       f'\nJoin their discord and ask for help there instead. https://discord.kog.tw/ '
        # return {"errfng": message_text}
    elif re_match[0] in nobyfng:
        message_text = f'{re_match[0]} appears to be a FNG server found within the DDNet tab. ' \
                       f'\nThese servers are classified as official but are not regulated by us. ' \
                       f'\nFor support, join this https://discord.gg/utB4Rs3 discord server instead.'
        # return {"errkog": message_text}
    else:
        message_text = f'{re_match[0]} is not a DDNet or KoG server.'
        # return {"errunknown": message_text}

    return message_text


class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ticket_data_file = "data/ticket_data.json"
        self.ticket_data = {}
        self.check_inactive_tickets.start()
        self.update_scores_topic.start()
        self.channel = None
        self.scores = {}
        self.mentions = set()
        self.verify_message = {}

    async def process_ticket_data(self, interaction, ticket_channel, ticket_creator_id, ticket_category):
        ticket_num = self.ticket_data.get(str(interaction.user.id), {}).get("ticket_num", 0) + 1

        creator_data = self.ticket_data.setdefault(str(ticket_creator_id), {})
        creator_data.setdefault('channel_ids', []).append((int(ticket_channel.id), ticket_category))

        inactivity_count = creator_data.setdefault('inactivity_count', {})
        for channel_id, _ in creator_data['channel_ids']:
            inactivity_count.setdefault(str(channel_id), 0)

        creator_data['ticket_num'] = ticket_num
        creator_data['inactivity_count'] = inactivity_count

        with open(self.ticket_data_file, "w") as f:
            json.dump(self.ticket_data, f, indent=4)

    @commands.command()
    async def button(self, ctx):
        if ctx.guild is None or ctx.guild.id != GUILD_DDNET or ROLE_ADMIN not in [role.id for role in ctx.author.roles]:
            return

        embed = discord.Embed(title="🎫  Welcome to our ticket system!",
                              description="If you've been banned and want to appeal the decision, need to request a "
                                          "rename, or have a complaint about the behavior of other users or moderators,"
                                          " you can create a ticket using the buttons below.",
                              colour=34483)
        embed.add_field(name="In-Game Issues",
                        value=f"If you encounter any behavior within the game that violates our rules, such as "
                              f"**blocking, fun-voting, cheating, or any other form of misconduct**, you can open a "
                              f"ticket in this given category to address the problem."
                              f"\n\nNote:\nPlease refrain from creating a support ticket for technical issues "
                              f"like DoS attacks or in-game lags",
                        inline=False)
        embed.add_field(name="Rename Requests",
                        value=f"The rules for rename requests are:"
                              f"\n- The original name should have 3k or more points on it"
                              f"\n- Your last rename should be at least one year ago"
                              f"\n- You must be able to provide proof of owning the points being moved"
                              f"\n- The names shouldn't be banned",
                        inline=False)
        embed.add_field(name="Ban appeals",
                        value=f"If you've been banned unfairly from our in-game servers, you are eligible to appeal the"
                              f" decision. Please note that ban appeals are not guaranteed to be successful, and our "
                              f"team reserves the right to deny any appeal at their discretion."
                              f"\n\nNote: Only file a ticket if you've been banned across all servers or from one of "
                              f"our moderators.",
                        inline=False)
        embed.add_field(name="Complaints",
                        value=f"If a staff member's behavior in our community has caused you concern, you have the "
                              f"option to make a complaint. Please note that complaints must be "
                              f"based on specific incidents or behaviors and not on personal biases or general "
                              f"dissatisfaction.",
                        inline=False)
        embed.add_field(name="Other",
                        value=f"If you have an issue or request that doesn't fit into any of the specific categories "
                              f"provided, you can still use our ticket system by selecting the \"Other\" option. "
                              f"This will allow you to explain your issue or request in detail, and we "
                              f"will review it and assist you accordingly. ",
                        inline=False)

        await ctx.send(embed=embed, view=CreateButton(self.ticket_data, self.process_ticket_data))

    @commands.command()
    async def invite(self, ctx, user: Union[discord.Member, discord.Role]):
        """Adds a user or role to the ticket. Example:
        $invite <discord username or role>
        """
        if ctx.channel.category.id not in [CAT_TICKETS, CAT_MODERATION] and is_staff(ctx.author.roles):
            return

        if not ctx.channel.topic or not ctx.channel.topic.startswith("Ticket author:"):
            await ctx.send('This is not a ticket channel you goof.')
            return

        channel = ctx.channel
        overwrite = channel.overwrites_for(user)

        if isinstance(user, discord.Member):
            overwrite.read_messages = True
            overwrite.send_messages = True
            await channel.set_permissions(user, overwrite=overwrite)
            await ctx.send(f"{user.mention} has been added to the channel.")
        elif isinstance(user, discord.Role):
            overwrite.read_messages = True
            overwrite.send_messages = True
            await channel.set_permissions(user, overwrite=overwrite)
            await ctx.send(f"{user.mention} role has been added to the channel.")
        else:
            await ctx.send("Invalid user or role provided.")

    @commands.command()
    async def close(self, ctx, *, message=None):
        """Closes a Ticket.
        Staff members can include a small message for the ticket creator. Example:
        $close <message>
        """

        if not ctx.channel.topic or not ctx.channel.topic.startswith("Ticket author:"):
            await ctx.send('This is not a ticket channel you goof.')
            return

        ticket_creator_id = int(ctx.channel.topic.split(": ")[1].strip("<@!>"))
        ticket_data = self.ticket_data.get(str(ticket_creator_id))

        if ticket_data is None:
            return

        channel_ids = ticket_data.get("channel_ids", [])
        if not any(channel_id[0] == ctx.channel.id for channel_id in channel_ids):
            return

        for channel_id, category in channel_ids:
            if channel_id == ctx.channel.id:
                ticket_category = category
                break

        if is_staff(ctx.author):
            default_message = f"Your <{ticket_category}> ticket has been closed by staff."
            ext_message = f"{default_message} " \
                          f"\nThis is the message that has been left for you by our team: " \
                          f"\n> {message}" if message else default_message
        else:
            ext_message = f"Your <{ticket_category}> ticket has been closed."

        ticket_channel = self.bot.get_channel(ctx.channel.id)
        ticket_creator = await self.bot.fetch_user(ticket_creator_id)
        await ticket_creator.send(ext_message)

        for channel_id in channel_ids:
            if channel_id[0] == ctx.channel.id:
                channel_ids.remove(channel_id)
                break

        del ticket_data["inactivity_count"][str(ctx.channel.id)]
        ticket_data["ticket_num"] -= 1

        if ticket_data["ticket_num"] < 1:
            self.ticket_data.pop(str(ticket_creator_id), None)
        else:
            self.ticket_data[str(ticket_creator_id)] = ticket_data

        with open(self.ticket_data_file, "w") as f:
            json.dump(self.ticket_data, f, indent=4)

        transcript_filename = f'{ticket_channel.name}.txt'
        await transcript(self.bot, ticket_channel.id, filename=transcript_filename)

        try:
            transcript_file = discord.File(transcript_filename)
            transcript_channel = self.bot.get_channel(CHAN_T_TRANSCRIPTS)
            await transcript_channel.send(f'Ticket created by: {ticket_creator} ({ticket_creator.id})',
                                          file=transcript_file)
            os.remove(transcript_filename)
        except FileNotFoundError:
            pass

        await ctx.channel.delete()

    @tasks.loop(hours=1)
    async def check_inactive_tickets(self):
        ticket_data_copy = self.ticket_data.copy()
        for user_id, ticket_data in ticket_data_copy.items():
            channel_ids = ticket_data.get("channel_ids", [])
            inactivity_count = ticket_data.get("inactivity_count", {})

            for channel_id, ticket_category in channel_ids:
                ticket_channel = self.bot.get_channel(channel_id)

                now = datetime.utcnow().replace(tzinfo=timezone.utc)
                recent_messages = [msg async for msg in
                                   ticket_channel.history(limit=1, after=now - timedelta(hours=6))]

                if recent_messages and recent_messages[0].created_at.astimezone(timezone.utc) > now - timedelta(
                        days=1):
                    inactivity_count[str(channel_id)] = 0
                else:
                    inactivity_count[str(channel_id)] = inactivity_count.get(str(channel_id), 0) + 1

                # TODO: Add some more logic, e.g send a message that a ticket is about to be closed at 2 Inactivity.
                if inactivity_count[str(channel_id)] >= 3:
                    topic = ticket_channel.topic
                    ticket_creator_id = int(topic.split(": ")[1].strip("<@!>"))
                    ticket_creator = await self.bot.fetch_user(ticket_creator_id)

                    message = f"Your <{ticket_category}> ticket has been closed due to inactivity."

                    await ticket_creator.send(message)
                    await ticket_channel.delete()

                    for channel_id in channel_ids:
                        if channel_id[0] == ticket_channel.id:
                            channel_ids.remove(channel_id)
                            break

                    del ticket_data["inactivity_count"][str(ticket_channel.id)]
                    ticket_data["ticket_num"] -= 1

                    if ticket_data["ticket_num"] < 1:
                        self.ticket_data.pop(str(ticket_creator_id))

        with open(self.ticket_data_file, "w") as f:
            json.dump(self.ticket_data, f, indent=4)

    @check_inactive_tickets.before_loop
    async def before_check_inactive_tickets(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=1)
    async def update_scores_topic(self):
        score_file = "data/scores.json"
        with open(score_file, "r") as file:
            scores = json.load(file)

        topic = "Issues Resolved:"
        for user_id, score in scores.items():
            topic += f" <@{user_id}> = {score} |"

        topic = topic.rstrip("|")

        channel = self.bot.get_channel(CHAN_MODERATOR)
        if channel:
            await channel.edit(topic=topic)

    @update_scores_topic.before_loop
    async def before_update_scores_topic(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        with open(self.ticket_data_file, "r") as f:
            self.ticket_data = json.load(f)

        self.bot.add_view(view=CreateButton(self.ticket_data, self.process_ticket_data))
        self.bot.add_view(view=CloseButton(self.bot, self.ticket_data))
        self.bot.add_view(view=ModeratorButton(self.bot))

    @commands.Cog.listener('on_message')
    async def server_link_verify(self, message: discord.Message):
        if message.author.bot:
            return

        ip_pattern = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}')
        ip_match = ip_pattern.search(message.content)

        if not ip_match:
            return

        ipv4 = ip_match.group(0)
        server_link_message = server_link(ipv4)

        if message.channel.name.startswith('ig-issue-') and message.channel not in self.mentions:
            at_mention_moderator = f'<@&{ROLE_MODERATOR}>'
            server_link_message += '\n' + at_mention_moderator
            self.mentions.add(message.channel)

        verify_message = await message.channel.send(server_link_message)
        self.verify_message[message.id] = verify_message.id

    @commands.Cog.listener('on_message_edit')
    async def message_delete_handler(self, before: discord.Message, after: discord.Message):
        if before.author.bot:
            return

        if before.id in self.verify_message:
            preview_message_id = self.verify_message[before.id]

            ip_pattern = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}')
            ip_match = ip_pattern.search(after.content)

            if not ip_match:
                return

            ipv4 = ip_match.group(0)
            server_link_message = server_link(ipv4)

            preview_message = await before.channel.fetch_message(preview_message_id)

            await preview_message.edit(content=server_link_message)


async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
