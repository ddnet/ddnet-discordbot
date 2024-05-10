import os
import json
import logging

import discord
import discord.ext
from discord.ui import Button

from config import ROLE_ADMIN, ROLE_DISCORD_MOD, ROLE_MOD, TH_REPORTS, TH_BAN_APPEALS, TH_RENAMES, TH_COMPLAINTS, \
    TH_ADMIN_MAIL
from utils.d_utils import is_staff
from utils.transcript import transcript

log = logging.getLogger('tickets')
roles = (ROLE_ADMIN, ROLE_DISCORD_MOD, ROLE_MOD)


def process_ticket_closure(self, ticket_channel_id, ticket_creator_id):
    ticket_data = self.ticket_data["tickets"].get(str(ticket_creator_id))
    channel_ids = ticket_data.get("channel_ids", [])

    category = None

    try:
        for channel_id, category in channel_ids:
            if channel_id == ticket_channel_id:
                channel_ids.remove([channel_id, category])
                break
    except KeyError:
        log.info('Ticket data for %s does not exist' % ticket_channel_id)

    try:
        del ticket_data["inactivity_count"][str(ticket_channel_id)]
        ticket_data["ticket_num"] -= 1
    except KeyError:
        ticket_data.setdefault('channel_ids', []).append([int(ticket_channel_id), category])
        log.info('Ticket data for %s does not exist' % ticket_channel_id)

    if ticket_data["ticket_num"] < 1:
        self.ticket_data["tickets"].pop(str(ticket_creator_id), None)
    else:
        self.ticket_data["tickets"][str(ticket_creator_id)] = ticket_data

    with open(self.ticket_data_file, "w", encoding='utf-8') as f:
        json.dump(self.ticket_data, f, indent=4)

    return category


class ConfirmView(discord.ui.View):
    def __init__(self, bot, ticket_data):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_data_file = 'data/ticket-system/ticket_data.json'
        self.ticket_data = ticket_data
        self.roles = roles

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green, custom_id='confirm:close_ticket')
    async def confirm(self, interaction: discord.Interaction, _: Button):

        await interaction.response.defer(ephemeral=True, thinking=True)  # noqa

        ticket_creator_id = int(interaction.channel.topic.split(": ")[1].strip("<@!>"))

        if not is_staff(interaction.user, self.roles) and interaction.user.id != ticket_creator_id:
            await interaction.channel.send('This ticket does not belong to you.')
            return

        ticket_channel = interaction.client.get_channel(interaction.channel.id)
        ticket_creator = await interaction.client.fetch_user(ticket_creator_id)

        transcript_file, zip_file = await transcript(self.bot, ticket_channel)
        ticket_category = process_ticket_closure(self, ticket_channel.id, ticket_creator_id=ticket_creator_id)

        if transcript_file:
            await ticket_channel.send('Uploading files...')
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
                t_message = (
                    f'**Ticket Channel ID: {ticket_channel.id}**'
                    f'\n\"{ticket_category.title()}\" Ticket created by: <@{ticket_creator.id}> '
                    f'(Global Name: {ticket_creator}) and closed by <@{interaction.user.id}> (Global Name: {interaction.user})')

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

        if is_staff(interaction.user, self.roles):
            response = f"Your ticket (category \"{ticket_category.capitalize()}\") has been closed by staff."
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

        await ticket_channel.send('Done! Closing Ticket...')
        await interaction.channel.delete()

        log.info(
            f"{interaction.user} (ID: {interaction.user.id}) closed {ticket_category.capitalize()} a ticket made by {ticket_creator} "
            f"(ID: {ticket_creator_id}). Removed Channel named {interaction.channel.name} (ID: {interaction.channel_id})"
        )

        if interaction.response.is_done():  # noqa
            return

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red, custom_id='cancel:close_ticket')
    async def cancel(self, interaction: discord.Interaction, _: Button):
        await interaction.response.defer()  # noqa
        await interaction.delete_original_response()
        await interaction.followup.send('Ticket closure cancelled.', ephemeral=True)


class CloseButton(discord.ui.View):
    def __init__(self, bot, ticket_data):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_data = ticket_data
        self.click_count = 0
        self.scores = {}

    @discord.ui.button(label='Close', style=discord.ButtonStyle.blurple, custom_id='MainMenu:close_ticket')
    async def t_close(self, interaction: discord.Interaction, _: Button):
        """Button which closes a Ticket"""

        await interaction.response.send_message('Are you sure you want to close the ticket?', ephemeral=True,  # noqa
                                                view=ConfirmView(self.bot, self.ticket_data))

    @discord.ui.button(label='Resolve (For Moderators)', style=discord.ButtonStyle.red, custom_id='ModeratorButton')
    async def t_moderator_check(self, interaction: discord.Interaction, _: Button):
        if not is_staff(interaction.user, roles):
            self.click_count += 1
            if self.click_count == 1:
                return await interaction.response.send_message('This button is for moderators only! Please read the '  # noqa
                                                        'instructions above!', ephemeral=True)
            if self.click_count == 2:
                return await interaction.response.send_message('Stop clicking me!', ephemeral=True)  # noqa
            if self.click_count == 3:
                return await interaction.response.send_message('If you wont stop, I\'ll close your ticket, '  # noqa
                                                        'last warning!', ephemeral=True)
            if self.click_count == 4:
                return await interaction.response.send_message(':OOO You did not just do that!', ephemeral=True)  # noqa
            if self.click_count == 5:
                return await interaction.response.send_message('(╯°□°)╯︵ ┻━┻', ephemeral=True)  # noqa
            self.click_count = 4
            return await interaction.response.send_message('┬─┬ノ( º _ ºノ)', ephemeral=True)  # noqa
        score_file = "data/ticket-system/scores.json"
        with open(score_file, "r", encoding='utf-8') as file:
            self.scores = json.load(file)

        user_id = str(interaction.user.id)
        if user_id in self.scores:
            self.scores[user_id] += 1
        else:
            self.scores[user_id] = 1

        with open(score_file, "w", encoding='utf-8') as file:
            json.dump(self.scores, file)

        close = CloseButton(interaction.client, self.ticket_data)
        close.remove_item(close.t_moderator_check)
        await interaction.message.edit(view=close)

        await interaction.response.send_message(  # noqa
            f'{interaction.user.mention}, thanks for taking care of this! Increased your score by 1.',
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions(users=False)
        )

        await interaction.channel.send(
            f'Hey, {interaction.user.mention} is on their way to'
            f' help you with your report. Thank you for your patience!',
            allowed_mentions=discord.AllowedMentions(users=False)
        )
