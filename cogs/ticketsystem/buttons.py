import discord

from discord.ui import Button, button, View
from cogs.ticketsystem.close import CloseButton, ModeratorButton

CAT_TICKETS            = 1124657181363556403
CAT_MODERATORION       = 968484659950403585
CHAN_INFO              = 1124657351442579486
CHAN_LOGS              = 968485530230743050
ROLE_ADMIN             = 293495272892399616
ROLE_DISCORD_MODERATOR = 737776812234506270
ROLE_MODERATOR         = 252523225810993153


class MainMenu(discord.ui.View):
    def __init__(self, ticket_data, process_ticket_data):
        super().__init__(timeout=None)
        self.ticket_data = ticket_data
        self.process_ticket_data = process_ticket_data

    """Limits tickets per person to one"""

    async def check_for_open_ticket(self, interaction, ticket_category) -> bool:
        user_id = str(interaction.user.id)
        ticket_info = self.ticket_data.get(user_id)
        if ticket_info and "channel_ids" in ticket_info:
            channel_ids = ticket_info["channel_ids"]
            for channel_id, category in channel_ids:
                if category == ticket_category:
                    channel = interaction.guild.get_channel(channel_id)
                    await interaction.response.send_message(
                        f"You already have an open <{ticket_category}> ticket: {channel.mention}\n"
                        f"Please resolve or close your existing ticket before creating a new one.\n"
                        f"You can close your ticket using the `$close` command within your existing ticket.",
                        ephemeral=True)
                    return True
        return False

    @discord.ui.button(label='In-game Issue', style=discord.ButtonStyle.blurple, custom_id='MainMenu:ig-issue')
    async def t_ingame_issue(self, interaction: discord.Interaction, button: Button):  # noqa
        """Limits tickets per person to one"""
        has_open_ticket = await self.check_for_open_ticket(interaction, ticket_category="ingame-issue")
        if has_open_ticket:
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        ticket_name = f"ig-issue-{interaction.user.name}"
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.get_role(ROLE_MODERATOR): discord.PermissionOverwrite(read_messages=True,
                                                                                    send_messages=True),
        }

        category = interaction.guild.get_channel(CAT_TICKETS)
        logs_channel = interaction.guild.get_channel(CHAN_LOGS)
        new_channel_position = logs_channel.position + 1
        ticket_creator_id = interaction.user.id

        ticket_channel = await interaction.guild.create_text_channel(
            name=ticket_name, category=category, position=new_channel_position, overwrites=overwrites,
            topic=f"Ticket author: <@{ticket_creator_id}>")

        embed = discord.Embed(
                        title="How to properly file a report", color=0xff0000)
        embed.add_field(name=f'',
                        value=f'Hello {interaction.user.mention}, thanks for reaching out!',
                        inline=False)

        embed.add_field(
                        name=f'Follow this Format:',
                        value=f'```prolog\n1. Copy the Server Info by pressing ESC -> Server Info -> Copy Info in-game.```'
                              f'```prolog\n2. Paste the Server Info you copied, by either using the keyboard shortcut '
                              f'CTRL+V or by right-clicking and selecting "Paste".```'
                              f'```prolog\n3. Describe the Problem you are having on the server.```'
                        )
        embed.add_field(
                        name=f'What not to report:',
                        value=f'Do NOT file reports about server lags or DoS attacks.'
                              f'\n\nDo NOT send moderator complaints here, create a ticket instead.'
                              f'\n\nDo NOT add unnecessary videos or demos to your report.'
                              f'\n\nDo NOT report players faking another player.',
                        inline=True
                        )
        embed.add_field(
                        name=f'Here\'s an example of how your report should look like:',
                        value=f'\nDDNet GER10 [ger10.ddnet.org whitelist] - Moderate'
                              f'\nAddress: ddnet://37.230.210.231:8320'
                              f'\nMy IGN: nameless tee'
                              f'\nTheres a blocker called "brainless tee" on my server',
                        inline=False
                        )
        embed.set_thumbnail(url='attachment://avatar.png')

        embed2 = discord.Embed(title='', colour=16776960)
        embed2.add_field(
            name=f'',
            value=f'\n\nIf you wish to close this ticket or opened this ticket by mistake, '
                  f'use either the close button below or type `$close`.', inline=False)

        message = await ticket_channel.send(
            f'{interaction.user.mention}',
            embeds=[embed, embed2], view=CloseButton(interaction.client, self.ticket_data))

        await ticket_channel.send(f'', view=ModeratorButton(interaction.client))

        await interaction.followup.send(  # noqa
            f"<@{interaction.user.id}> your ticket has been created: {message.jump_url}", ephemeral=True)

        await self.process_ticket_data(interaction, ticket_channel, ticket_creator_id, "ingame-issue")

        if interaction.response.is_done():  # noqa
            return

    @discord.ui.button(label='Rename', style=discord.ButtonStyle.blurple, custom_id='MainMenu:renames')
    async def t_renames(self, interaction: discord.Interaction, button: Button):  # noqa
        """Limits tickets per person to one"""
        has_open_ticket = await self.check_for_open_ticket(interaction, ticket_category="rename")
        if has_open_ticket:
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        ticket_name = f"rename-{interaction.user.name}"
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        category = interaction.guild.get_channel(CAT_TICKETS)
        info_channel = interaction.guild.get_channel(CHAN_INFO)
        new_channel_position = info_channel.position + 1
        ticket_creator_id = interaction.user.id

        ticket_channel = await interaction.guild.create_text_channel(
            name=ticket_name, category=category, position=new_channel_position, overwrites=overwrites,
            topic=f"Ticket author: <@{ticket_creator_id}>")

        embed = discord.Embed(title="Player Rename", colour=2210995)
        embed.add_field(name=f'',
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
                        inline=False)

        embed2 = discord.Embed(title='', colour=16776960)
        embed2.add_field(
            name=f'',
            value=f'\n\nIf you wish to close this ticket or opened this ticket by mistake, '
                  f'use either the close button below or type `$close`.', inline=False)

        message = await ticket_channel.send(
            f'<@&{ROLE_ADMIN}> {interaction.user.mention}',
            embeds=[embed, embed2], view=CloseButton(interaction.client, self.ticket_data))

        await interaction.followup.send(  # noqa
            f"<@{interaction.user.id}> your ticket has been created: {message.jump_url}", ephemeral=True)

        await self.process_ticket_data(interaction, ticket_channel, ticket_creator_id, "rename")

        if interaction.response.is_done():  # noqa
            return

    @discord.ui.button(label='Ban Appeal', style=discord.ButtonStyle.blurple, custom_id='MainMenu:ban_appeal')
    async def t_ban_appeal(self, interaction: discord.Interaction, button: Button):  # noqa
        """Limits tickets per person to one"""
        has_open_ticket = await self.check_for_open_ticket(interaction, ticket_category="ban_appeal")
        if has_open_ticket:
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        ticket_name = f"ban-appeal-{interaction.user.name}"
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.get_role(ROLE_MODERATOR): discord.PermissionOverwrite(read_messages=True,
                                                                                    send_messages=True),
            interaction.guild.get_role(ROLE_DISCORD_MODERATOR): discord.PermissionOverwrite(read_messages=True,
                                                                                            send_messages=True)}

        category = interaction.guild.get_channel(CAT_TICKETS)
        info_channel = interaction.guild.get_channel(CHAN_INFO)
        new_channel_position = info_channel.position + 1
        ticket_creator_id = interaction.user.id

        ticket_channel = await interaction.guild.create_text_channel(
            name=ticket_name, category=category, position=new_channel_position, overwrites=overwrites,
            topic=f"Ticket author: <@{ticket_creator_id}>")

        embed = discord.Embed(title="Ban appeal", colour=2210995)
        embed.add_field(
            name=f'',
            value=f'Hello {interaction.user.mention},'
                  f'\nin order to begin your ban appeal, we will need a few important pieces of information from you.'
                  f'\n\n**Please provide us with: **'
                  f'\n* Your public IPv4 Address from this [Link](https://ipv4.icanhazip.com/).'
                  f'\n* Your in-game player name.'
                  f'\n* The reason you\'ve been banned for.')
        embed.add_field(
            name=f'',
            value=f"When writing your appeal, please aim to be clear and straightforward in your explanation. "
                  f"It's important to be honest about what occurred and take ownership for any actions that may have "
                  f"resulted in your ban. "
                  f"Additionally, if you have any evidence, such as screenshots or chat logs that may support your "
                  f"case, please include it in your appeal.")

        embed2 = discord.Embed(title='', colour=16776960)
        embed2.add_field(
            name=f'',
            value=f'Please keep in mind that it may take some time for us to review your appeal. '
                  f'We kindly ask that you remain patient during this process. '
                  f'If the moderators require any further information, please respond promptly to their request.'
                  f'\n\nIf you wish to close this ticket or opened this ticket by mistake, '
                  f'use either the close button below or type `$close`.',
            inline=False)

        message = await ticket_channel.send(
            f'<@&{ROLE_MODERATOR}> '
            # f'<@&{ROLE_ADMIN}> '
            f'{interaction.user.mention}',
            embeds=[embed, embed2],
            view=CloseButton(interaction.client, self.ticket_data))

        await interaction.followup.send(  # noqa
            f"<@{interaction.user.id}> your ticket has been created: {message.jump_url}", ephemeral=True)

        await self.process_ticket_data(interaction, ticket_channel, ticket_creator_id, "ban_appeal")

        if interaction.response.is_done():  # noqa
            return

    @discord.ui.button(label='Complaint', style=discord.ButtonStyle.blurple, custom_id='MainMenu:complaints')
    async def t_complaints(self, interaction: discord.Interaction, button: Button):  # noqa
        """Limits tickets per person to one"""
        has_open_ticket = await self.check_for_open_ticket(interaction, ticket_category="complaint")
        if has_open_ticket:
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        ticket_name = f"complaint-{interaction.user.name}"
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        category = interaction.guild.get_channel(CAT_TICKETS)
        info_channel = interaction.guild.get_channel(CHAN_INFO)
        new_channel_position = info_channel.position + 1
        ticket_creator_id = interaction.user.id

        ticket_channel = await interaction.guild.create_text_channel(
            name=ticket_name, category=category, position=new_channel_position, overwrites=overwrites,
            topic=f"Ticket author: <@{ticket_creator_id}>")

        embed = discord.Embed(title="Ban appeal", colour=2210995)
        embed.add_field(
            name=f'',
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
            name=f'',
            value=f'\n\nIf you wish to close this ticket or opened this ticket by mistake, '
                  f'use either the close button below or type `$close`.', inline=False)

        message = await ticket_channel.send(f'<@&{ROLE_ADMIN}> {interaction.user.mention}', embeds=[embed, embed2],
                                            view=CloseButton(interaction.client, self.ticket_data))

        await interaction.followup.send(  # noqa
            f"<@{interaction.user.id}> your ticket has been created: {message.jump_url}", ephemeral=True)

        await self.process_ticket_data(interaction, ticket_channel, ticket_creator_id, "complaint")

        if interaction.response.is_done():  # noqa
            return

    @discord.ui.button(label='Other', style=discord.ButtonStyle.blurple, custom_id='MainMenu:other')
    async def t_other(self, interaction: discord.Interaction, button: Button):  # noqa
        """Limits tickets per person to one"""
        has_open_ticket = await self.check_for_open_ticket(interaction, ticket_category="other")
        if has_open_ticket:
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        ticket_name = f"other-{interaction.user.name}"
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        category = interaction.guild.get_channel(CAT_TICKETS)
        info_channel = interaction.guild.get_channel(CHAN_INFO)
        new_channel_position = info_channel.position + 1
        ticket_creator_id = interaction.user.id
        ticket_channel = await interaction.guild.create_text_channel(
            name=ticket_name, category=category, position=new_channel_position, overwrites=overwrites,
            topic=f"Ticket author: <@{ticket_creator_id}>")

        embed = discord.Embed(title="Other", colour=2210995)
        embed.add_field(name=f'',
                        value=f'Hello {interaction.user.mention},'
                              f'\nthanks for reaching out to us regarding your unique issue or request. '
                              f'\n\nPlease describe your request or issue in as much detail as possible. '
                              f'The more information you provide, the better we can understand and address your '
                              f'specific concern. Feel free to include any relevant background, specific requirements, '
                              f'or any other details that can help us assist you effectively. Your thorough description'
                              f' will enable us to provide you with the most appropriate help.',
                        inline=False)

        embed2 = discord.Embed(title='', colour=16776960)
        embed2.add_field(
            name=f'',
            value=f'\n\nIf you wish to close this ticket or opened this ticket by mistake, '
                  f'use either the close button below or type `$close`.', inline=False)

        message = await ticket_channel.send(
            f'<@&{ROLE_ADMIN}> {interaction.user.mention}',
            embeds=[embed, embed2], view=CloseButton(interaction.client, self.ticket_data))

        await interaction.followup.send(  # noqa
            f"<@{interaction.user.id}> your ticket has been created: {message.jump_url}", ephemeral=True)

        await self.process_ticket_data(interaction, ticket_channel, ticket_creator_id, "other")

        if interaction.response.is_done():  # noqa
            return
