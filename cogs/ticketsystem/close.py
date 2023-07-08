import discord
import os
import json


from discord.ui import Button, button, View
from utils.transcript import transcript

CAT_TICKETS            = 1124657181363556403
CHAN_T_TRANSCRIPTS     = 1124657432816267394
CHAN_MODERATOR         = 345588928482508801
ROLE_ADMIN             = 293495272892399616
ROLE_DISCORD_MODERATOR = 737776812234506270
ROLE_MODERATOR         = 252523225810993153


def is_staff(member: discord.Member) -> bool:
    return any(role.id in (ROLE_ADMIN, ROLE_DISCORD_MODERATOR, ROLE_MODERATOR) for role in member.roles)


class ConfirmView(discord.ui.View):
    def __init__(self, bot, ticket_data):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_data_file = 'data/ticket_data.json'
        self.ticket_data = ticket_data

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green, custom_id='confirm:close_ticket')
    async def confirm(self, interaction: discord.Interaction, button: Button):
        ticket_creator_id = int(interaction.channel.topic.split(": ")[1].strip("<@!>"))
        ticket_data = self.ticket_data.get(str(ticket_creator_id))

        if ticket_data is None:
            return

        channel_ids = ticket_data.get("channel_ids", [])
        if not any(channel_id[0] == interaction.channel.id for channel_id in channel_ids):
            return

        for channel_id, category in channel_ids:
            if channel_id == interaction.channel.id:
                ticket_category = category
                break

        ticket_channel = interaction.client.get_channel(interaction.channel.id)
        default_message = f"Your <{ticket_category}> ticket has been closed by staff." if is_staff(
            interaction.user) else "Your ticket has been closed."
        ticket_creator = await interaction.client.fetch_user(ticket_creator_id)
        await ticket_creator.send(default_message)

        for channel_id in channel_ids:
            if channel_id[0] == interaction.channel.id:
                channel_ids.remove(channel_id)
                break

        del ticket_data["inactivity_count"][str(interaction.channel.id)]
        ticket_data["ticket_num"] -= 1

        if ticket_data["ticket_num"] < 1:
            self.ticket_data.pop(str(ticket_creator_id), None)
        else:
            self.ticket_data[str(ticket_creator_id)] = ticket_data

        with open(self.ticket_data_file, "w") as f:
            json.dump(self.ticket_data, f, indent=4)

        transcript_filename = f'{interaction.channel.name}.txt'
        await transcript(self.bot, ticket_channel.id, filename=transcript_filename)

        try:
            transcript_file = discord.File(transcript_filename)
            transcript_channel = self.bot.get_channel(CHAN_T_TRANSCRIPTS)
            await transcript_channel.send(f'Ticket created by: {ticket_creator} ({ticket_creator.id})',
                                          file=transcript_file)
            os.remove(transcript_filename)
        except FileNotFoundError:
            pass

        await interaction.channel.delete()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red, custom_id='cancel:close_ticket')
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await interaction.delete_original_response()
        await interaction.followup.send('Ticket closure cancelled.', ephemeral=True)

class CloseButton(discord.ui.View):
    def __init__(self, bot, ticket_data):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_data = ticket_data

    @discord.ui.button(label='Close', style=discord.ButtonStyle.blurple, custom_id='MainMenu:close_ticket')
    async def t_close(self, interaction: discord.Interaction, button: Button):
        """Button which closes a Ticket"""

        # Create a confirmation view for the interaction
        await interaction.response.send_message('Are you sure you want to close the ticket?', ephemeral=True,
                                                view=ConfirmView(self.bot, self.ticket_data))

class ModeratorButton(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.click_count = 0
        self.channel = None
        self.scores = {}

    async def update_scores_topic(self):
        sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        formatted_users = [f"<@{user}> = {score}" for user, score in sorted_scores]
        topic = "Scores: " + " | ".join(formatted_users)
        await self.channel.edit(topic=topic)

    @discord.ui.button(label='Button for Moderators', style=discord.ButtonStyle.red, custom_id='ModeratorButton')
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

            await interaction.response.send_message( # noqa
                f'{interaction.user.mention}, thanks for taking care of this! Increased your score by 1.',
                ephemeral=True)
            await interaction.message.delete()
            await interaction.channel.send(f'Hey, {interaction.user.mention} is on their way to'
                                           f' help you with your report. Thank you for your patience!')
