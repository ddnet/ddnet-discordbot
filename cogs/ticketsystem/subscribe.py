import discord
import json

from discord.ui import Button, button, View


class SubscribeMenu(discord.ui.View):
    def __init__(self, ticket_data):
        super().__init__(timeout=None)
        self.ticket_data = ticket_data
        self.subscribers = 'data/ticket_data.json'

    @discord.ui.select(
        placeholder='To which categories would you like to subscribe to?',
        options=[
            discord.SelectOption(label='Report', value='Reports'),
            discord.SelectOption(label='Rename', value='Renames'),
            discord.SelectOption(label='Ban Appeal', value='Ban Appeals'),
            discord.SelectOption(label='Complaint', value='Complaint'),
            discord.SelectOption(label='Other', value='Other')
        ],
        max_values=5, custom_id='Subscribe:Menu'
    )
    async def subscriptions(self, interaction: discord.Interaction, select_item: discord.ui.Select):
        await interaction.response.defer(ephemeral=True, thinking=True)

        with open(self.subscribers, 'r') as file:
            ticket_data = json.load(file)

        selected_values = interaction.data['values']
        selected_options = [
            option for option in self.children[0].options if option.value in selected_values
        ]
        selected_categories = [option.label for option in selected_options]

        for category in ticket_data['subscriptions']['categories']:
            if category in selected_categories:
                if interaction.user.id not in ticket_data['subscriptions']['categories'][category]:
                    ticket_data['subscriptions']['categories'][category].append(interaction.user.id)
            else:
                if interaction.user.id in ticket_data['subscriptions']['categories'][category]:
                    ticket_data['subscriptions']['categories'][category].remove(interaction.user.id)

        self.ticket_data.update(ticket_data)

        with open('data/ticket_data.json', 'w') as file:
            json.dump(ticket_data, file, indent=4)

        subscribed_categories = [category for category in selected_categories if
                                 interaction.user.id in ticket_data['subscriptions']['categories'][category]]
        category_message = "You have subscribed to the following categories:\n- " + "\n- ".join(subscribed_categories)

        for option in select_item.options:
            option.default = False

        await interaction.followup.send(category_message, ephemeral=True)
        await interaction.message.edit(view=self)

    @discord.ui.button(label='Subscribe All', style=discord.ButtonStyle.green, custom_id='Subscribe:All')
    async def subscribe_all(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)

        with open(self.subscribers, 'r') as file:
            ticket_data = json.load(file)

        for category in ticket_data['subscriptions']['categories']:
            if interaction.user.id not in ticket_data['subscriptions']['categories'][category]:
                ticket_data['subscriptions']['categories'][category].append(interaction.user.id)

        self.ticket_data.update(ticket_data)

        with open(self.subscribers, 'w') as file:
            json.dump(self.ticket_data, file, indent=4)

        await interaction.followup.send('Subscribed you to all ticket categories.', ephemeral=True)

    @discord.ui.button(label='Unsubscribe All', style=discord.ButtonStyle.green, custom_id='Unsubscribe:All')
    async def unsubscribe_all(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)

        with open(self.subscribers, 'r') as file:
            ticket_data = json.load(file)

        for category in ticket_data['subscriptions']['categories']:
            if interaction.user.id in ticket_data['subscriptions']['categories'][category]:
                ticket_data['subscriptions']['categories'][category].remove(interaction.user.id)

        self.ticket_data.update(ticket_data)

        with open(self.subscribers, 'w') as file:
            json.dump(ticket_data, file, indent=4)

        await interaction.followup.send('Unsubscribed you from all ticket categories.', ephemeral=True)
