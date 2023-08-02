import discord
import os
import json
import discord.ext
import logging

from discord.ui import Button, button, View
from utils.transcript import transcript

CAT_TICKETS            = 1124657181363556403
CHAN_T_TRANSCRIPTS     = 1124657432816267394
CHAN_MODERATOR         = 345588928482508801
CHAN_LOGS              = 968485530230743050
ROLE_ADMIN             = 293495272892399616
ROLE_DISCORD_MODERATOR = 737776812234506270
ROLE_MODERATOR         = 252523225810993153


def is_staff(member: discord.Member) -> bool:
    return any(role.id in (ROLE_ADMIN, ROLE_DISCORD_MODERATOR, ROLE_MODERATOR) for role in member.roles)


def process_ticket_closure(self, ticket_channel_id, ticket_creator_id):
    ticket_data = self.ticket_data["tickets"].get(str(ticket_creator_id))
    channel_ids = ticket_data.get("channel_ids", [])

    category = None

    for channel_id, category in channel_ids:
        if channel_id == ticket_channel_id:
            channel_ids.remove([channel_id, category])
            break

    del ticket_data["inactivity_count"][str(ticket_channel_id)]
    ticket_data["ticket_num"] -= 1

    if ticket_data["ticket_num"] < 1:
        self.ticket_data["tickets"].pop(str(ticket_creator_id), None)
    else:
        self.ticket_data["tickets"][str(ticket_creator_id)] = ticket_data

    with open(self.ticket_data_file, "w") as f:
        json.dump(self.ticket_data, f, indent=4)

    return category


class ConfirmView(discord.ui.View):
    def __init__(self, bot, ticket_data):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_data_file = 'data/ticket_data.json'
        self.ticket_data = ticket_data

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green, custom_id='confirm:close_ticket')
    async def confirm(self, interaction: discord.Interaction, button: Button):
        ticket_creator_id = int(interaction.channel.topic.split(": ")[1].strip("<@!>"))

        if not is_staff(interaction.user) and interaction.user.id != ticket_creator_id:
            return

        ticket_channel = interaction.client.get_channel(interaction.channel.id)
        ticket_creator = await interaction.client.fetch_user(ticket_creator_id)

        ticket_category = process_ticket_closure(self, ticket_channel.id, ticket_creator_id=ticket_creator_id)

        transcript_filename = f'{interaction.channel.name}.txt'
        await transcript(self.bot, ticket_channel.id, filename=transcript_filename)

        try:
            logs_channel = self.bot.get_channel(CHAN_LOGS)
            transcript_channel = self.bot.get_channel(CHAN_T_TRANSCRIPTS)
            message = f'"{ticket_category.capitalize()}" Ticket created by: <@{ticket_creator.id}> (Global Name: {ticket_creator}) ' \
                      f'and closed by <@{interaction.user.id}> (Global Name: {interaction.user})'

            if ticket_category in ('report', 'ban_appeal'):
                transcript_file = discord.File(transcript_filename)
                await logs_channel.send(
                    message,
                    file=transcript_file,
                    allowed_mentions=discord.AllowedMentions(users=False)
                )
                # have to do this twice because discord.File objects are single use only
                transcript_file = discord.File(transcript_filename)
                await transcript_channel.send(
                    message,
                    file=transcript_file,
                    allowed_mentions=discord.AllowedMentions(users=False)
                )
            else:
                transcript_file = discord.File(transcript_filename)
                await transcript_channel.send(
                    message,
                    file=transcript_file,
                    allowed_mentions=discord.AllowedMentions(users=False)
                )

            os.remove(transcript_filename)
        except FileNotFoundError:
            pass

        await interaction.channel.delete()

        default_message = f"Your ticket (category \"{ticket_category}\") has been closed by staff." \
            if is_staff(interaction.user) else None

        try:
            if default_message is not None:
                await ticket_creator.send(default_message)
        except discord.Forbidden:
            pass

        logging.info(
            f"{interaction.user} (ID: {interaction.user.id}) closed {ticket_category.capitalize()} a ticket made by {ticket_creator} "
            f"(ID: {ticket_creator_id}). Removed Channel named {interaction.channel.name} (ID: {interaction.channel_id})"
        )

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red, custom_id='cancel:close_ticket')
    async def cancel(self, interaction: discord.Interaction, button: Button):
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
    async def t_close(self, interaction: discord.Interaction, button: Button):
        """Button which closes a Ticket"""

        await interaction.response.send_message('Are you sure you want to close the ticket?', ephemeral=True,  # noqa
                                                view=ConfirmView(self.bot, self.ticket_data))

    @discord.ui.button(label='Resolve (For Moderators)', style=discord.ButtonStyle.red, custom_id='ModeratorButton')
    async def t_moderator_check(self, interaction: discord.Interaction, button: Button):
        if not is_staff(interaction.user):
            self.click_count += 1
            if self.click_count == 1:
                await interaction.response.send_message(f'This button is for moderators only! Please read the ' # noqa
                                                        f'instructions above!', ephemeral=True)
                return
            elif self.click_count == 2:
                await interaction.response.send_message(f'Stop clicking me!', ephemeral=True) # noqa
                return
            elif self.click_count == 3:
                await interaction.response.send_message(f'If you wont stop, I\'ll close your ticket, ' # noqa
                                                        f'last warning!', ephemeral=True)
                return
            elif self.click_count == 4:
                await interaction.response.send_message(f':OOO You did not just do that!', ephemeral=True) # noqa
                return
            elif self.click_count == 5:
                await interaction.response.send_message(f'(╯°□°)╯︵ ┻━┻', ephemeral=True) # noqa
                return
            elif self.click_count == 6:
                await interaction.response.send_message(f'┬─┬ノ( º _ ºノ)', ephemeral=True) # noqa
                self.click_count = 4
                return

        else:
            score_file = "data/scores.json"
            with open(score_file, "r") as file:
                self.scores = json.load(file)

            user_id = str(interaction.user.id)
            if user_id in self.scores:
                self.scores[user_id] += 1
            else:
                self.scores[user_id] = 1

            with open(score_file, "w") as file:
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
