import json
import logging

import discord
from discord.ui import Button, button
from cogs.ticketsystem.close import CloseButton

from config import ROLE_DISCORD_MOD, ROLE_MOD, CAT_TICKETS

log = logging.getLogger('tickets')


class MainMenu(discord.ui.View):
    def __init__(self, ticket_data):
        super().__init__(timeout=None)
        self.ticket_data = ticket_data
        self.ticket_data_file = "data/ticket-system/ticket_data.json"

    def process_ticket_data(self, interaction, ticket_channel, ticket_creator_id, ticket_category):
        ticket_num = \
            self.ticket_data.setdefault("tickets", {}).get(str(interaction.user.id), {}).get("ticket_num", 0) + 1

        creator_data = self.ticket_data.setdefault("tickets", {}).setdefault(str(ticket_creator_id), {})
        creator_data.setdefault('channel_ids', []).append([int(ticket_channel.id), ticket_category])

        inactivity_count = creator_data.setdefault('inactivity_count', {})
        for channel_id, _ in creator_data['channel_ids']:
            inactivity_count.setdefault(str(channel_id), 0)

        creator_data['ticket_num'] = ticket_num
        creator_data['inactivity_count'] = inactivity_count

        with open(self.ticket_data_file, "w", encoding='utf-8') as f:
            json.dump(self.ticket_data, f, indent=4)

        user_ids = self.ticket_data["subscriptions"]["categories"].get(ticket_category, [])
        mention_subscribers = [f"<@{user_id}>" for user_id in user_ids]
        mention_message = " ".join(mention_subscribers) + f' {interaction.user.mention}'

        return mention_message

    async def ticket_num(self, category) -> int:
        ticket_num = self.ticket_data["ticket_count"]["categories"][category]

        if ticket_num:
            ticket_num = int(ticket_num) + 1
        else:
            ticket_num = 1

        ticket_num = int(ticket_num)
        self.ticket_data["ticket_count"]["categories"][category] = int(ticket_num)

        with open(self.ticket_data_file, 'w', encoding='utf-8') as file:
            json.dump(self.ticket_data, file, indent=4)

        return ticket_num

    async def check_for_open_ticket(self, interaction, ticket_category) -> bool:
        """Limits tickets per person to one"""
        user_id = str(interaction.user.id)
        ticket_info = self.ticket_data["tickets"].get(user_id)
        if ticket_info and "channel_ids" in ticket_info:
            channel_ids = ticket_info["channel_ids"]
            for channel_id, category in channel_ids:
                if category == ticket_category:
                    channel = interaction.guild.get_channel(channel_id)
                    await interaction.response.send_message(
                        f"You already have an open <{ticket_category}> ticket: {channel.mention}"
                        f"\nPlease resolve or close your existing ticket before creating a new one."
                        f"\nYou can close your ticket using the `$close` command within your existing ticket.",
                        ephemeral=True)
                    return True
        return False

    @discord.ui.button(label='Report', style=discord.ButtonStyle.danger, custom_id='MainMenu:report')
    async def t_reports(self, interaction: discord.Interaction, _: Button):  # noqa
        """Limits tickets per person to one"""
        has_open_ticket = await self.check_for_open_ticket(interaction, ticket_category="report")
        if has_open_ticket:
            return

        await interaction.response.defer(ephemeral=True, thinking=True)  # noqa

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=False),
            interaction.user: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True),
            interaction.guild.get_role(ROLE_MOD): discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True),
            interaction.guild.get_role(ROLE_DISCORD_MOD): discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True)
        }

        ticket_name = f"report-{await self.ticket_num(category='report')}"
        category = interaction.guild.get_channel(CAT_TICKETS)
        channel_position = category.channels[-1].position + 0
        ticket_creator_id = interaction.user.id

        ticket_channel = await interaction.guild.create_text_channel(
            name=ticket_name,
            category=category,
            position=channel_position,
            overwrites=overwrites,
            topic=f"Ticket author: <@{ticket_creator_id}>")

        mention_message = self.process_ticket_data(interaction, ticket_channel, ticket_creator_id, "report")

        embed = discord.Embed(
            title="How to properly file a report", color=0xff0000)
        embed.add_field(
            name='',
            value=f'Hello {interaction.user.mention}, thanks for reaching out!',
            inline=False
        )
        embed.add_field(
            name='Follow this Format:',
            value='```prolog\n1. Copy the Server Info by pressing ESC -> Server Info -> Copy Info in-game.```'
                  '```prolog\n2. Paste the Server Info you copied, by either using the keyboard shortcut '
                  'CTRL+V or by right-clicking and selecting "Paste".```'
                  '```prolog\n3. Describe the Problem you are having on the server.```'
        )
        embed.add_field(
            name='What not to report:',
            value='Do NOT file reports about server lags or DoS attacks.'
                  '\n\nDo NOT send moderator complaints here, create a "Complaint" ticket instead.'
                  '\n\nDo NOT add unnecessary videos or demos to your report.'
                  '\n\nDo NOT report players faking another player.',
            inline=True
        )
        embed.add_field(
            name='Here\'s an example of how your report should look like:',
            value='\nDDNet GER10 [ger10.ddnet.org whitelist] - Moderate'
                  '\nAddress: ddnet://37.230.210.231:8320'
                  '\nMy IGN: nameless tee'
                  '\nTheres a blocker called "brainless tee" on my server',
            inline=False
        )
        embed.set_thumbnail(url='attachment://avatar.png')

        embed2 = discord.Embed(title='', colour=16776960)
        embed2.add_field(
            name='',
            value='\n\nIf you wish to close this ticket or opened this ticket by mistake, '
                  'use either the close button below or type `$close`.',
            inline=False
        )

        message = await ticket_channel.send(
            mention_message,
            embeds=[embed, embed2],
            view=CloseButton(interaction.client, self.ticket_data)
        )

        await interaction.followup.send(  # noqa
            f"<@{interaction.user.id}> your ticket has been created: {message.jump_url}", ephemeral=True)
        log.info(f'{interaction.user} (ID: {interaction.user.id}) created a "Report" ticket.')

        if interaction.response.is_done():  # noqa
            return

    @discord.ui.button(label='Rename', style=discord.ButtonStyle.blurple, custom_id='MainMenu:renames')
    async def t_renames(self, interaction: discord.Interaction, _: Button):  # noqa
        """Limits tickets per person to one"""
        has_open_ticket = await self.check_for_open_ticket(interaction, ticket_category="rename")
        if has_open_ticket:
            return

        await interaction.response.defer(ephemeral=True, thinking=True)  # noqa

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=False),
            interaction.user: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True),
            interaction.guild.get_role(ROLE_DISCORD_MOD): discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True)
        }

        ticket_name = f"rename-{await self.ticket_num(category='rename')}"
        category = interaction.guild.get_channel(CAT_TICKETS)
        channel_position = category.channels[-1].position + 0
        ticket_creator_id = interaction.user.id

        ticket_channel = await interaction.guild.create_text_channel(
            name=ticket_name,
            category=category,
            position=channel_position,
            overwrites=overwrites,
            topic=f"Ticket author: <@{ticket_creator_id}>")

        mention_message = self.process_ticket_data(interaction, ticket_channel, ticket_creator_id, "rename")

        embed = discord.Embed(title="Player Rename", colour=2210995)
        embed.add_field(
            name='',
            value=f'Hello {interaction.user.mention},'
                  f'\n\nto initiate the process of moving your in-game points to a different name,'
                  f'\nwe require some essential information from you. Kindly provide answers to the '
                  f'following questions:'
                  f'\n\n* What is your current player name in the game?'
                  f'\n* What name would you like to change to?'
                  f'\n* Have you ever received a rename before?'
                  f'\n - If yes, by whom?'
                  f'\n* To validate the ownership of the points being transferred, '
                  f'we require you to provide us verifiable evidence of ownership.'
                  f'\n - We accept proof in form of old demo files that contain finishes done on DDNet. '
                  f'The demo files directory can be found in your config directory. '
                  f'Use $configdir if you\'re unsure where that is.'
                  f'\n - Alternatively, if you have any personal connections to one of our staff members, '
                  f'you can ask them to vouch for your credibility.',
            inline=False
        )

        embed2 = discord.Embed(title='', colour=16776960)
        embed2.add_field(
            name='',
            value='\n\nIf you wish to close this ticket or opened this ticket by mistake, '
                  'use either the close button below or type `$close`.',
            inline=False
        )

        close = CloseButton(interaction.client, self.ticket_data)
        close.remove_item(close.t_moderator_check)

        message = await ticket_channel.send(
            mention_message,
            embeds=[embed, embed2],
            view=close
        )

        await interaction.followup.send(  # noqa
            f"<@{interaction.user.id}> your ticket has been created: {message.jump_url}", ephemeral=True)
        log.info(f'{interaction.user} (ID: {interaction.user.id}) created a "Rename" ticket.')

        if interaction.response.is_done():  # noqa
            return

    @discord.ui.button(label='Ban Appeal', style=discord.ButtonStyle.blurple, custom_id='MainMenu:ban_appeal')
    async def t_ban_appeal(self, interaction: discord.Interaction, _: Button):  # noqa
        """Limits tickets per person to one"""
        has_open_ticket = await self.check_for_open_ticket(interaction, ticket_category="ban_appeal")
        if has_open_ticket:
            return

        await interaction.response.defer(ephemeral=True, thinking=True)  # noqa

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=False),
            interaction.user: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True),
            interaction.guild.get_role(ROLE_MOD): discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True),
            interaction.guild.get_role(ROLE_DISCORD_MOD): discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True)
        }

        ticket_name = f"ban-appeal-{await self.ticket_num(category='ban_appeal')}"
        category = interaction.guild.get_channel(CAT_TICKETS)
        channel_position = category.channels[-1].position + 0
        ticket_creator_id = interaction.user.id

        ticket_channel = await interaction.guild.create_text_channel(
            name=ticket_name,
            category=category,
            position=channel_position,
            overwrites=overwrites,
            topic=f"Ticket author: <@{ticket_creator_id}>"
        )

        mention_message = self.process_ticket_data(interaction, ticket_channel, ticket_creator_id, "ban_appeal")

        embed = discord.Embed(title="Ban appeal", colour=2210995)
        embed.add_field(
            name='',
            value=f'Hello {interaction.user.mention},'
                  f'\nin order to begin your ban appeal, we will need a few important pieces of information from you.'
                  f'\n\n**Please provide us with: **'
                  f'\n* Your public IPv4 Address from this [Link](https://ipv4.icanhazip.com/).'
                  f'\n* Your in-game player name.'
                  f'\n* The reason you\'ve been banned for.'
        )
        embed.add_field(
            name='',
            value="When writing your appeal, please aim to be clear and straightforward in your explanation. "
                  "It's important to be honest about what occurred and take ownership for any actions that may have "
                  "resulted in your ban. "
                  "Additionally, if you have any evidence, such as screenshots or chat logs that may support your "
                  "case, please include it in your appeal."
        )

        embed2 = discord.Embed(title='', colour=16776960)
        embed2.add_field(
            name='',
            value='Please keep in mind that it may take some time for us to review your appeal. '
                  'We kindly ask that you remain patient during this process. '
                  'If the moderators require any further information, please respond promptly to their request.'
                  '\n\nIf you wish to close this ticket or opened this ticket by mistake, '
                  'use either the close button below or type `$close`.',
            inline=False
        )

        close = CloseButton(interaction.client, self.ticket_data)
        close.remove_item(close.t_moderator_check)

        message = await ticket_channel.send(
            mention_message,
            embeds=[embed, embed2],
            view=close
        )

        await interaction.followup.send(  # noqa
            f"<@{interaction.user.id}> your ticket has been created: {message.jump_url}", ephemeral=True)
        log.info(f'{interaction.user} (ID: {interaction.user.id}) created a "Ban Appeal" ticket.')

        if interaction.response.is_done():  # noqa
            return

    @discord.ui.button(label='Staff Complaint', style=discord.ButtonStyle.blurple, custom_id='MainMenu:complaints')
    async def t_complaints(self, interaction: discord.Interaction, _: Button):  # noqa
        """Limits tickets per person to one"""
        has_open_ticket = await self.check_for_open_ticket(interaction, ticket_category="complaint")
        if has_open_ticket:
            return

        await interaction.response.defer(ephemeral=True, thinking=True)  # noqa

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=False),
            interaction.user: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True),
            interaction.guild.get_role(ROLE_DISCORD_MOD): discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True)
        }

        ticket_name = f"complaint-{await self.ticket_num(category='complaint')}"
        category = interaction.guild.get_channel(CAT_TICKETS)
        channel_position = category.channels[-1].position + 0
        ticket_creator_id = interaction.user.id

        ticket_channel = await interaction.guild.create_text_channel(
            name=ticket_name,
            category=category,
            position=channel_position,
            overwrites=overwrites,
            topic=f"Ticket author: <@{ticket_creator_id}>"
        )

        mention_message = self.process_ticket_data(interaction, ticket_channel, ticket_creator_id, "complaint")

        embed = discord.Embed(title="Complaint", colour=2210995)
        embed.add_field(
            name='',
            value=f'Hello {interaction.user.mention},'
                  f'\napproach the process with clarity and objectivity. '
                  f'Here are some steps to help you write an effective complaint:'
                  f'\n\nClearly pinpoint the incident or behavior that has caused you concern. '
                  f'Be specific about what happened, when it occurred, and who was involved. '
                  f'This will provide a clear context for your complaint. '
                  f'Ensure that your complaint is based on objective facts rather than '
                  f'personal biases or general dissatisfaction. '
                  f'Stick to the specific incident or behavior you are addressing and '
                  f'avoid making assumptions or generalizations.'
                  f'\n\nAlso, upload relevant evidence or supporting information that can strengthen your complaint. '
                  f'This may include screenshots, message logs or in-game demos.',
            inline=False)

        embed2 = discord.Embed(title='', colour=16776960)
        embed2.add_field(
            name='',
            value='\n\nIf you wish to close this ticket or opened this ticket by mistake, '
                  'use either the close button below or type `$close`.',
            inline=False
        )

        close = CloseButton(interaction.client, self.ticket_data)
        close.remove_item(close.t_moderator_check)

        message = await ticket_channel.send(
            mention_message,
            embeds=[embed, embed2],
            view=close
        )

        await interaction.followup.send(  # noqa
            f"<@{interaction.user.id}> your ticket has been created: {message.jump_url}", ephemeral=True)
        log.info(f'{interaction.user} (ID: {interaction.user.id}) created a "Complaint" ticket.')

        if interaction.response.is_done():  # noqa
            return

    @discord.ui.button(label='Admin-Mail', style=discord.ButtonStyle.blurple, custom_id='MainMenu:admin-mail')
    async def t_admin_mail(self, interaction: discord.Interaction, _: Button):  # noqa
        """Limits tickets per person to one"""
        has_open_ticket = await self.check_for_open_ticket(interaction, ticket_category="admin-mail")
        if has_open_ticket:
            return

        await interaction.response.defer(ephemeral=True, thinking=True)  # noqa

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=False),
            interaction.user: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True),
            interaction.guild.get_role(ROLE_DISCORD_MOD): discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True)
        }

        ticket_name = f"admin-mail-{await self.ticket_num(category='admin-mail')}"
        category = interaction.guild.get_channel(CAT_TICKETS)
        channel_position = category.channels[-1].position + 0
        ticket_creator_id = interaction.user.id

        ticket_channel = await interaction.guild.create_text_channel(
            name=ticket_name,
            category=category,
            position=channel_position,
            overwrites=overwrites,
            topic=f"Ticket author: <@{ticket_creator_id}>"
        )

        mention_message = self.process_ticket_data(interaction, ticket_channel, ticket_creator_id, "admin-mail")

        embed = discord.Embed(title="Admin-Mail", colour=2210995)
        embed.add_field(
            name='',
            value=f'Hello {interaction.user.mention},'
                  f'\nthanks for reaching out to us regarding your unique issue or request. '
                  f'\n\nPlease describe your request or issue in as much detail as possible. '
                  f'The more information you provide, the better we can understand and address your '
                  f'specific concern. Feel free to include any relevant background, specific requirements, '
                  f'or any other details that can help us assist you effectively. Your thorough description'
                  f' will enable us to provide you with the most appropriate help.',
            inline=False
        )

        embed2 = discord.Embed(title='', colour=16776960)
        embed2.add_field(
            name='',
            value='\n\nIf you wish to close this ticket or opened this ticket by mistake, '
                  'use either the close button below or type `$close`.',
            inline=False
        )

        close = CloseButton(interaction.client, self.ticket_data)
        close.remove_item(close.t_moderator_check)

        message = await ticket_channel.send(
            mention_message,
            embeds=[embed, embed2],
            view=close
        )

        await interaction.followup.send(  # noqa
            f"<@{interaction.user.id}> your ticket has been created: {message.jump_url}", ephemeral=True)
        log.info(f'{interaction.user} (ID: {interaction.user.id}) created a "Admin-Mail" ticket.')

        if interaction.response.is_done():  # noqa
            return
