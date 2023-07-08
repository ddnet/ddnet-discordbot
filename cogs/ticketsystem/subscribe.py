import discord
import json

from discord.ui import Button, button, View


class SubscribeMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.subscribers = 'data/subscribers.json'

    @discord.ui.select(
        placeholder='To which categories would you like to subscribe to?',
        options=[
            discord.SelectOption(label='In-game Issue', value='Ingame Issue'),
            discord.SelectOption(label='Rename', value='Renames'),
            discord.SelectOption(label='Ban Appeal', value='Ban Appeals'),
            discord.SelectOption(label='Complaint', value='Complaint'),
            discord.SelectOption(label='Other', value='Other')
        ],
        max_values=5, custom_id='Subscribe:Menu'
    )
    async def subscriptions(self, interaction: discord.Interaction, select_item: discord.ui.Select):
        with open(self.subscribers, 'r') as file:
            data = json.load(file)

        await interaction.response.defer(ephemeral=True, thinking=True)

        selected_values = interaction.data['values']
        selected_options = [
            option for option in self.children[0].options if option.value in selected_values
        ]
        selected_categories = [option.label for option in selected_options]

        for category in data['subscriptions']['categories']:
            if category in selected_categories:
                if interaction.user.id not in data['subscriptions']['categories'][category]:
                    data['subscriptions']['categories'][category].append(interaction.user.id)
            else:
                if interaction.user.id in data['subscriptions']['categories'][category]:
                    data['subscriptions']['categories'][category].remove(interaction.user.id)

        with open(self.subscribers, 'w') as file:
            json.dump(data, file, indent=4)

        subscribed_categories = [category for category in selected_categories if
                                 interaction.user.id in data['subscriptions']['categories'][category]]
        category_message = "You have subscribed to the following categories:\n- " + "\n- ".join(subscribed_categories)

        for option in select_item.options:
            option.default = False
        await interaction.followup.send(category_message, ephemeral=True)
        await interaction.message.edit(view=self)

    @discord.ui.button(label='Subscribe All', style=discord.ButtonStyle.green, custom_id='Subscribe:All')
    async def subscribe_all(self, interaction: discord.Interaction, button: Button):

        await interaction.response.defer(ephemeral=True, thinking=True)

        with open(self.subscribers, 'r') as file:
            data = json.load(file)

        for category in data['subscriptions']['categories']:
            if not interaction.user.id in data['subscriptions']['categories'][category]:
                data['subscriptions']['categories'][category].append(interaction.user.id)

        with open(self.subscribers, 'w') as file:
            json.dump(data, file, indent=4)

        await interaction.followup.send('Subscribed you to all ticket categories.', ephemeral=True)

    @discord.ui.button(label='Unsubscribe All', style=discord.ButtonStyle.green, custom_id='Unsubscribe:All')
    async def unsubscribe_all(self, interaction: discord.Interaction, button: Button):

        await interaction.response.defer(ephemeral=True, thinking=True)

        with open(self.subscribers, 'r') as file:
            data = json.load(file)

        for category in data['subscriptions']['categories']:
            if interaction.user.id in data['subscriptions']['categories'][category]:
                data['subscriptions']['categories'][category].remove(interaction.user.id)

        with open(self.subscribers, 'w') as file:
            json.dump(data, file, indent=4)

        await interaction.followup.send('Unsubscribed you from all ticket categories.', ephemeral=True)
