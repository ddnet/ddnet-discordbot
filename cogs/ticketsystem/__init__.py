import discord
import json
import os
import re
import requests
import logging

from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
from typing import Union

from cogs.ticketsystem.buttons import MainMenu
from cogs.ticketsystem.close import CloseButton, process_ticket_closure
from cogs.ticketsystem.subscribe import SubscribeMenu
from config import ROLE_MOD, ROLE_DISCORD_MOD, ROLE_ADMIN, GUILD_DDNET, CHAN_QUESTIONS, CHAN_BUGS, TH_REPORTS, \
    TH_BAN_APPEALS, TH_RENAMES, TH_COMPLAINTS, TH_ADMIN_MAIL, CHAN_MODERATOR
from utils.d_utils import is_staff, check_admin
from utils.transcript import transcript

log = logging.getLogger('tickets')


def extract_servers(tags, network):
    jsondata = requests.get("https://info.ddnet.org/info", timeout=1).json()

    server_list = None
    if network == "ddnet":
        server_list = jsondata.get('servers')
    elif network == "kog":
        server_list = jsondata.get('servers-kog')

    all_servers = []
    for address in server_list:
        server = address.get('servers')
        for tag in tags:
            server_lists = server.get(tag)
            if server_lists is not None:
                all_servers += server_lists
    return all_servers


def server_link(addr):
    ddnet = extract_servers(['DDNet', 'Test', 'Tutorial'], "ddnet")
    ddnetpvp = extract_servers(['Block', 'Infection', 'iCTF', 'gCTF', 'Vanilla', 'zCatch',
                                'TeeWare', 'Foot', 'xPanic', 'Monster'], "ddnet")
    nobyfng = extract_servers(['FNG'], "ddnet")
    kog = extract_servers(['Gores', 'TestGores'], "kog")

    ipv4_addr = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,4}')
    re_match = ipv4_addr.findall(addr)

    if re_match[0] in ddnet:
        message_text = f'{re_match[0]} is an official DDNet server. ' \
                       f'\n<https://ddnet.org/connect-to/?addr={re_match[0]}/>'
    elif re_match[0] in ddnetpvp:
        message_text = f'{re_match[0]} is an official DDNet PvP server. ' \
                       f'\n<https://ddnet.org/connect-to/?addr={re_match[0]}/>'
    elif re_match[0] in kog:
        message_text = f'{re_match[0]} appears to be a KoG server. DDNet and KoG aren\'t affiliated. ' \
                       f'\nJoin their discord and ask for help there instead. <https://discord.kog.tw/>'
        return {"errfng": message_text}
    elif re_match[0] in nobyfng:
        message_text = f'{re_match[0]} appears to be a FNG server found within the DDNet tab. ' \
                       f'\nThese servers are classified as official but are not regulated by us. ' \
                       f'\nFor support, join this https://discord.gg/utB4Rs3 discord server instead.'
        return {"errkog": message_text}
    else:
        message_text = f'{re_match[0]} is not a DDNet or KoG server.'
        return {"errunknown": message_text}

    return message_text


class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ticket_data_file = "data/ticket-system/ticket_data.json"
        self.ticket_data = {}
        self.check_inactive_tickets.start()
        self.update_scores_topic.start()
        self.mentions = set()
        self.verify_message = {}
        self.roles = (ROLE_ADMIN, ROLE_DISCORD_MOD, ROLE_MOD)

    @commands.command(hidden=True)
    async def ticket_menu(self, ctx):
        if ctx.guild is None or ctx.guild.id != GUILD_DDNET or ROLE_ADMIN not in [role.id for role in ctx.author.roles]:
            return

        embed = discord.Embed(
            title="🎫  Welcome to our ticket system!",
            description="If you've been banned and want to appeal the decision, need to request a "
                        "rename, or have a complaint about the behavior of other users or moderators, "
                        "you can create a ticket using the buttons below.",
            colour=34483
        )
        embed.add_field(
            name="Report",
            value=f"If you encounter any behavior within the game that violates our rules, such as "
                  f"**blocking, fun-voting, cheating, or any other form of misconduct**, you can open a "
                  f"ticket in this given category to address the problem. \n\n"
                  f"Note:\nRefrain from creating a ticket for server issues like DoS attacks or in-game lags",
            inline=False
        )
        embed.add_field(
            name="Rename Request",
            value=f"The rules for rename requests are: \n"
                  f"- The original name should have 3k or more points on it \n"
                  f"- Your last rename should be __at least one year ago__ \n"
                  f"- You must be able to provide proof of owning the points being moved \n"
                  f"- The names shouldn't be banned \n"
                  f"- If you request a rename and then later change your mind, know that it won't be reverted until at"
                  f" least one year has passed. Think carefully.",
            inline=False
        )
        embed.add_field(
            name="Ban Appeal",
            value=f"If you've been banned unfairly from our in-game servers, you are eligible to appeal the"
                  f" decision. Please note that ban appeals are not guaranteed to be successful, and our "
                  f"team reserves the right to deny any appeal at their discretion. \n\n"
                  f"Note: Only file a ticket if you've been banned across all servers or from one of "
                  f"our moderators.",
            inline=False
        )
        embed.add_field(
            name="Staff Complaint",
            value=f"If a staff member's behavior in our community has caused you concern, you have the "
                  f"option to make a complaint. Please note that complaints must be "
                  f"based on specific incidents or behaviors and not on personal biases or general dissatisfaction.",
            inline=False
        )
        embed.add_field(
            name="Admin-Mail (No technical support)",
            value=f"If you have an issue or request related to administrative matters, you can use this option. "
                  f"Explain your issue or request in detail and we will review it and assist you accordingly. \n\n"
                  f"**Note: For technical issues or bugs, use <#{CHAN_QUESTIONS}> or <#{CHAN_BUGS}> instead.**",
            inline=False
        )
        embed_warning = discord.Embed(
            title="If you create tickets with no valid reason or solely to troll, "
                  "you will be given a timeout.",
            description="",
            colour=16776960
        )
        await ctx.message.delete()
        await ctx.send(embeds=[embed, embed_warning], view=MainMenu(self.ticket_data))

    @commands.command(hidden=True)
    async def subscribe_button(self, ctx):
        if check_admin(ctx):
            return

        await ctx.send(
            f'Choose the ticket categories you wish to receive notifications for, '
            f'or use the Subscribe/Unsubscribe buttons to manage notifications for all categories.',
            view=SubscribeMenu(self.ticket_data)
        )

    @commands.command(hidden=True)
    async def invite(self, ctx, user: Union[discord.Member, discord.Role]):
        """Adds a user or role to the ticket. Example:
        $invite <discord username or role>
        """
        if ctx.guild is None or ctx.guild.id != GUILD_DDNET or not is_staff(ctx.author, self.roles):
            return

        if not ctx.channel.topic or not ctx.channel.topic.startswith("Ticket author:"):
            return

        if isinstance(user, discord.Role) and user.id == ctx.guild.default_role.id:
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

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.BadUnionArgument):
            await ctx.send("Invalid user or role provided.")

    @commands.command(hidden=True)
    async def close(self, ctx, *, message=None):
        """
        Closes a Ticket.
        Staff members can include a small message for the ticket creator. Example:
        $close <message>
        """
        if ctx.guild is None or ctx.guild.id != GUILD_DDNET:
            return

        if not ctx.channel.topic or not ctx.channel.topic.startswith("Ticket author:"):
            return

        ticket_creator_id = int(ctx.channel.topic.split(": ")[1].strip("<@!>"))

        if not is_staff(ctx.author, self.roles) and ctx.author.id != ticket_creator_id:
            await ctx.channel.send('This ticket does not belong to you.')
            return

        ticket_channel = self.bot.get_channel(ctx.channel.id)
        ticket_creator = await self.bot.fetch_user(ticket_creator_id)

        transcript_file, zip_file = await transcript(self.bot, ticket_channel)
        ticket_category = process_ticket_closure(self, ticket_channel.id, ticket_creator_id=ticket_creator_id)

        if transcript_file:
            await ticket_channel.send(f'Uploading files...')
            targets = {
                'report': TH_REPORTS,
                'ban_appeal': TH_BAN_APPEALS,
                'rename': TH_RENAMES,
                'complaint': TH_COMPLAINTS,
                'admin-mail': TH_ADMIN_MAIL,
            }

            if ticket_category in targets:
                target_channel = self.bot.get_channel(targets[ticket_category])
            else:
                await ticket_channel.send("Something went horribly wrong. Target Channel doesn't exist or is locked.")
                return

            if target_channel:
                t_message = (
                    f'**Ticket Channel ID: {ticket_channel.id}**'
                    f'\n\"{ticket_category.title()}\" Ticket created by: <@{ticket_creator.id}> '
                    f'(Global Name: {ticket_creator}) and closed by <@{ctx.author.id}> (Global Name: {ctx.author})')

                await target_channel.send(
                    t_message,
                    files=[discord.File(transcript_file)],
                    allowed_mentions=discord.AllowedMentions(users=False)
                )

                if zip_file is not None:
                    for z in zip_file:
                        await target_channel.send(
                            files=[discord.File(z)],
                            allowed_mentions=discord.AllowedMentions(users=False)
                        )
            else:
                await ticket_channel.send("Something went horribly wrong. Invalid ticket category.")

        if is_staff(ctx.author, self.roles):
            response = f"Your ticket (category \"{ticket_category.capitalize()}\") has been closed by staff."
            if message:
                response += f"\nThis is the message that has been left for you by our team:\n> {message}"
        else:
            response = f"Your ticket (category \"{ticket_category.capitalize()}\") has been closed."

        file_paths = []
        if transcript_file is not None:
            response += "\n**Transcript:**"
            file_paths.append(transcript_file)

        try:
            if response:
                await ticket_creator.send(content=response,
                                          file=discord.File(transcript_file) if transcript_file else None)
        except discord.Forbidden:
            pass

        if zip_file is not None and isinstance(zip_file, list):
            file_paths.extend(zip_file)
        try:
            for file_path in file_paths:
                if file_path is not None:
                    os.remove(file_path)
        except FileNotFoundError:
            pass

        await ticket_channel.send(f'Done! Closing Ticket...')
        await ctx.channel.delete()

        log.info(
            f"{ctx.author} (ID: {ctx.author.id}) closed a ticket made by {ticket_creator} "
            f"(ID: {ticket_creator_id}). Removed Channel named {ctx.channel.name} (ID: {ctx.channel.id})"
        )

    @tasks.loop(hours=1)
    async def check_inactive_tickets(self):
        channels_to_remove = []
        for ticket_user_id, ticket_data in self.ticket_data.get("tickets", {}).items():
            for channel_id, ticket_category in ticket_data.get("channel_ids", []):
                ticket_channel = self.bot.get_channel(channel_id)

                if ticket_category in ['admin-mail', 'complaint']:
                    continue

                inactivity_count = ticket_data.get("inactivity_count", {})

                now = datetime.utcnow().replace(tzinfo=timezone.utc)

                recent_messages = []
                async for msg in ticket_channel.history(limit=5, oldest_first=False):
                    if not msg.author.bot:
                        recent_messages.append(msg)

                if recent_messages and recent_messages[0].created_at.astimezone(timezone.utc) > now - timedelta(
                        days=1):
                    inactivity_count[str(channel_id)] = 0
                else:
                    inactivity_count[str(channel_id)] = inactivity_count.get(str(channel_id), 0) + 1

                if inactivity_count[str(channel_id)] == 2:
                    await ticket_channel.send(
                        f'<@{ticket_user_id}>, this ticket is about to be closed due to inactivity.'
                        f'\nIf your report or question has been resolved, consider closing '
                        f'this ticket yourself by typing $close.'
                        f'\n**To keep this ticket active, please reply to this message.**'
                    )
                    pass

                if inactivity_count[str(channel_id)] >= 6:
                    channels_to_remove.append((ticket_channel.id, ticket_user_id))

        with open(self.ticket_data_file, "w") as f:
            json.dump(self.ticket_data, f, indent=4)

        if channels_to_remove:
            for channel_id, ticket_creator_id in channels_to_remove:
                ticket_channel = self.bot.get_channel(channel_id)
                transcript_file, zip_file = await transcript(self.bot, ticket_channel)
                ticket_creator = await self.bot.fetch_user(ticket_creator_id)
                ticket_category = process_ticket_closure(self, ticket_channel.id,
                                                         ticket_creator_id=ticket_creator_id)

                if transcript_file:
                    await ticket_channel.send(f'Uploading files...')
                    targets = {
                        'report': TH_REPORTS,
                        'ban_appeal': TH_BAN_APPEALS,
                        'rename': TH_RENAMES,
                        'complaint': TH_COMPLAINTS,
                        'admin-mail': TH_ADMIN_MAIL,
                    }

                    if ticket_category in targets:
                        target_channel = self.bot.get_channel(targets[ticket_category])
                    else:
                        await ticket_channel.send("Something went horribly wrong. Target Channel doesn't exist.")
                        return

                    if target_channel:
                        t_message = (f'\"{ticket_category.title()}\"Ticket created by: <@{ticket_creator.id}> '
                                     f'(Global Name: {ticket_creator}), closed due to inactivity.'
                                     f'\nTicket Channel ID: {ticket_channel.id}')

                        await target_channel.send(
                            t_message,
                            files=[discord.File(transcript_file)],
                            allowed_mentions=discord.AllowedMentions(users=False)
                        )

                        if zip_file is not None:
                            for z in zip_file:
                                await target_channel.send(
                                    files=[discord.File(z)],
                                    allowed_mentions=discord.AllowedMentions(users=False)
                                )
                    else:
                        await ticket_channel.send("Something went horribly wrong. Invalid ticket category.")

                message = f"Your ticket (category \"{ticket_category.capitalize()}\") has been closed due to inactivity."

                if transcript_file is not None:
                    message += "\n**Transcript:**"

                try:
                    if message:
                        await ticket_creator.send(content=message,
                                                  file=discord.File(transcript_file) if transcript_file else None)
                except discord.Forbidden:
                    pass

                file_paths = []
                if transcript_file is not None:
                    file_paths.append(transcript_file)
                if zip_file is not None and isinstance(zip_file, list):
                    file_paths.extend(zip_file)
                try:
                    for file_path in file_paths:
                        if file_path is not None:
                            os.remove(file_path)
                except FileNotFoundError:
                    pass

                await ticket_channel.send(f'Done! Closing Ticket...')
                await ticket_channel.delete()

                log.info(
                    f" Removed channel named {ticket_channel.name} (ID: {ticket_channel.id}), due to inactivity."
                )

    @check_inactive_tickets.before_loop
    async def before_check_inactive_tickets(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=1)
    async def update_scores_topic(self):
        score_file = "data/ticket-system/scores.json"
        with open(score_file, "r") as file:
            scores = json.load(file)

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        topic = "Issues Resolved:"
        for user_id, score in sorted_scores[:30]:
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

        self.bot.add_view(view=MainMenu(self.ticket_data))
        self.bot.add_view(view=CloseButton(self.bot, self.ticket_data))
        self.bot.add_view(view=SubscribeMenu(self.ticket_data))

    @commands.Cog.listener('on_message')
    async def server_link_verify(self, message: discord.Message):
        if message.guild is None or message.author.bot or message.guild.id != GUILD_DDNET:
            return

        ip_pattern = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}')
        ip_match = ip_pattern.search(message.content)

        if not ip_match:
            return

        ipv4 = ip_match.group(0)
        result = server_link(ipv4)

        if message.channel:
            if "errfng" in result:
                content = result["errfng"]
            elif "errkog" in result:
                content = result["errkog"]
            elif "errunknown" in result:
                content = result["errunknown"]
            elif message.channel.name.startswith('report-') and message.channel not in self.mentions:
                server_link_message = result
                at_mention_moderator = f'\n<@&{ROLE_MOD}>'
                content = server_link_message + at_mention_moderator
                self.mentions.add(message.channel)
            else:
                content = result

            verify_message = await message.channel.send(content)
            self.verify_message[message.id] = verify_message.id

    @commands.Cog.listener('on_message_edit')
    async def message_edit_handler(self, before: discord.Message, after: discord.Message):
        if before.author.bot:
            return

        ip_pattern = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}')
        ip_match = ip_pattern.search(after.content)

        if not ip_match:
            return

        ipv4 = ip_match.group(0)
        result = server_link(ipv4)

        if after.channel.name.startswith('report-') and after.channel not in self.mentions:
            at_mention_moderator = f'<@&{ROLE_MOD}>'
            result += '\n' + at_mention_moderator
            self.mentions.add(after.channel)

            preview_message = await before.channel.fetch_message(self.verify_message.get(before.id))

            if preview_message:
                await preview_message.delete()

            verify_message = await after.channel.send(result)
            self.verify_message[after.id] = verify_message.id
        else:
            verify_message_id = self.verify_message.get(before.id)

            if verify_message_id:
                preview_message = await before.channel.fetch_message(verify_message_id)

                if "errfng" in result:
                    await preview_message.edit(content=result["errfng"])
                elif "errkog" in result:
                    await preview_message.edit(content=result["errkog"])
                elif "errunknown" in result:
                    await preview_message.edit(content=result["errunknown"])
                else:
                    await preview_message.edit(content=result)


async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
