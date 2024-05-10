import discord
import random
import os
import json
import asyncio

from discord.ext import commands
from io import BytesIO
from typing import Optional

from config import TH_QUIZ, CHAN_ANSWERS, GUILD_DDNET


class Teeguesser(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lock = asyncio.Lock()

        self.scores = {}
        self.score_file = "data/teeguesser/scores.json"
        self._diff = None

        self.questions = None
        self.questions_tiebreaker = None

        self._answer = None
        self.game_over = True
        self.current_round = 1

        self.tiebreak_round = False
        self.tiebreaker_final_round = False

        self.participants = {}

        self.quiz_helper = None
        self.unveiled_indices = set()

    async def write_score(self, user_id, rounds=0, maps=0):
        with open(self.score_file, "r") as file:
            self.scores = json.load(file)

        user_id = str(user_id)
        if user_id in self.scores:
            self.scores[user_id]['rounds_won'] += rounds
            self.scores[user_id]['maps_guessed'] += maps
        else:
            self.scores[user_id] = {
                'rounds_won': rounds,
                'maps_guessed': maps
            }

        with open(self.score_file, "w") as file:
            json.dump(self.scores, file)

    async def reset(self, full_reset: Optional[bool] = False):
        if self.quiz_helper:
            self.quiz_helper.cancel()

        self._answer = None
        self.game_over = True
        self.current_round = 1

        if full_reset:
            self.participants = {}
            self.tiebreak_round = False
            self.tiebreaker_final_round = False

    async def get_score(self, user_id):
        with open(self.score_file, "r") as file:
            self.scores = json.load(file)

        if user_id in self.scores:
            user_data = self.scores[user_id]
            rounds_won = user_data.get('rounds_won')
            maps_guessed = user_data.get('maps_guessed')
            return rounds_won, maps_guessed
        else:
            return 0, 0

    async def quiz_image(self):
        m_root = 'data/teeguesser/maps'

        diff_dir = [f for f in os.listdir(m_root) if os.path.isdir(os.path.join(m_root, f))]

        weights = {
            'insane': 0.24,
            'brutal': 0.03,
            'moderate': 0.2,
            'novice': 0.1,
            'solo': 0.05,
            'oldschool': 0.1,
            'fun': 0.01
        }

        while True:
            _diff = random.choices(diff_dir, [weights[f] for f in diff_dir])[0]
            if _diff != self._diff:
                break

        self._diff = _diff
        path_to_diff = os.path.join(m_root, _diff)

        map_dir = [f for f in os.listdir(path_to_diff) if os.path.isdir(os.path.join(path_to_diff, f))]
        _map = random.choice(map_dir)
        path_to_map = os.path.join(path_to_diff, _map)

        _img = [f for f in os.listdir(path_to_map) if f.endswith('.png')]
        img = random.choice(_img)

        with open(os.path.join(path_to_map, img), 'rb') as image_file:
            _buf = BytesIO(image_file.read())

        return _diff, _buf, _map

    async def quiz(self):
        _diff, _buf, _map = await self.quiz_image()
        self.game_over = False
        self._answer = os.path.basename(_map)

        return _diff, _buf

    def hint(self):
        unveiled_indices = [i for i in range(len(self._answer)) if i not in self.unveiled_indices]

        if unveiled_indices:
            index = random.choice(unveiled_indices)
            self.unveiled_indices.add(index)

        hint = ["_" if i not in self.unveiled_indices and self._answer[i] != ' ' else self._answer[i] for i in
                range(len(self._answer))]
        return hint

    async def quiz_hints(self, message, difficulty):
        self.unveiled_indices = set()

        if self.game_over:
            self.quiz_helper.cancel()
            return

        await asyncio.sleep(10)

        content = message.content.replace("Server Difficulty: ?", f"Server Difficulty: **{difficulty.capitalize()}**")
        updated = await message.edit(content=content)

        await asyncio.sleep(5)

        while not self.game_over and difficulty != 'fun':
            revealed_hint = ' '.join(self.hint())

            if self.game_over:
                break

            await asyncio.sleep(5)

            content = (f"{updated.content}\n\n"
                       f"Too difficult? Here's a hint :)\n"
                       f"`{revealed_hint}`")

            await updated.edit(content=content)

            if len(self.unveiled_indices) >= 0.75 * len(self._answer):
                await message.delete()

                msg = await message.channel.send(
                    content=f"Times up! The map was: `{self._answer}`. Let's try a different map.")
                self._answer = None

                await asyncio.sleep(5)
                await msg.delete()
                await self.start_round(message.channel)
                break

    def scoreboard_embed(self) -> discord.Embed:
        scoreboard = "\n".join([
            f"<@{user_id}>: {score[1] if self.game_over and score[1] != 0 else score[0]} rounds won"
            for user_id, score in sorted(self.participants.items(), key=lambda x: x[1][0], reverse=True) if
            (self.game_over and score[1] != 0) or (not self.game_over and score[0] != 0)
        ])

        rows = scoreboard.split('\n')
        description = '\n'.join(rows)

        title = 'Scoreboard:' if self.game_over else f"{'Tiebreaker Scoreboard:' if self.tiebreak_round else 'Scoreboard'}"

        return discord.Embed(title=title, description=description)

    async def handle_correct_answer(self, message):
        await self.write_score(message.author.id, maps=1)

        self.participants.setdefault(message.author.id, [0, 0])
        self.participants[message.author.id][0] += 1
        self.participants[message.author.id][1] += 1

        quiz_channel = self.bot.get_channel(TH_QUIZ)
        a = asyncio.create_task(message.add_reaction("🎉"))
        b = asyncio.create_task(quiz_channel.send(f'Nice, {message.author.mention}! "{self._answer}" is correct.'))
        await asyncio.gather(a, b)

        if self.quiz_helper:
            self.quiz_helper.cancel()

        await asyncio.sleep(5)

        if self.tiebreaker_final_round and self.tiebreak_round:
            await self.tiebreaker_last_round(quiz_channel)
        elif self.tiebreak_round:
            await self.tiebreaker(quiz_channel)
        else:
            await self.next_round(quiz_channel)

    async def start_round(self, channel):
        await channel.purge()
        _diff, _buf = await self.quiz()

        round_type = "Final Tiebreaker" if self.tiebreak_round and self.tiebreaker_final_round \
            else "Tiebreaker Round" if self.tiebreak_round else "Round"
        difficulty_text = "Math" if _diff == 'fun' else "?"

        msg = await channel.send(
            f"## {round_type} {str(self.current_round) + '.' if round_type != 'Final Tiebreaker' else ''}\nServer Difficulty: {difficulty_text}\nGuess the map from this image!",
            file=discord.File(_buf, filename='quiz_image.png')
        )

        self.quiz_helper = asyncio.create_task(self.quiz_hints(msg, _diff))

    async def next_round(self, quiz_channel):
        if self.current_round < self.questions:
            self._answer = None
            self.current_round += 1

            await quiz_channel.purge()

            await quiz_channel.send(f'Next round starting...', embed=self.scoreboard_embed())
            await asyncio.sleep(5)

            await self.start_round(quiz_channel)
        else:
            self.game_over = True
            await self.quiz_game_over(quiz_channel)

    async def quiz_game_over(self, quiz_channel):
        self.game_over = True
        winners = [user_id for user_id, score in self.participants.items() if score == max(self.participants.values())]

        await quiz_channel.purge(limit=5, bulk=True)

        if len(winners) == 1:
            await self.single_winner(quiz_channel, winners[0])
        else:
            await self.multiple_winners(quiz_channel, winners)

    async def single_winner(self, quiz_channel, winner):
        await self.write_score(winner, rounds=1)
        score = await self.get_score(str(winner))

        await quiz_channel.send(
            f"## <@{winner}> won this game. \n"
            f"Your Profile:\nGames won: `{score[0]}`, Maps correctly identified: `{score[1]}`\n\n"
            f"Starting a new round in a couple seconds..", embed=self.scoreboard_embed()
        )
        await asyncio.sleep(10)

        channel = self.bot.get_channel(CHAN_ANSWERS)
        await self.default_overwrites(channel)
        await self.reset(full_reset=True)

        # await asyncio.sleep(7)

        await self.start_round(quiz_channel)

    async def multiple_winners(self, quiz_channel, winners):
        for user in self.participants:
            self.participants[user][0] = 0

        if self.tiebreak_round:
            await quiz_channel.send(
                "We have another tie. This one last round will decide who wins.\n\n"
                f"Starting the final round in 5 seconds... \n"
                f"## {', '.join([f'<@{participant}>' for participant in self.participants])} "
                "Get ready.")

            channel = self.bot.get_channel(CHAN_ANSWERS)
            await self.tiebreaker_overwrites(channel, self.participants)

            await self.reset()

            self.tiebreaker_final_round = True

            await asyncio.sleep(5)
            await self.start_round(quiz_channel)
        else:
            await quiz_channel.send(
                f"We have a tie! The following participants now engage in a sudden death round: "
                f"{', '.join([f'<@{winner}>' for winner in winners])}"
            )

            channel = self.bot.get_channel(CHAN_ANSWERS)
            await self.tiebreaker_overwrites(channel, self.participants)

            await self.reset()

            self.tiebreak_round = True
            await asyncio.sleep(5)
            await self.start_round(quiz_channel)

    async def tiebreaker(self, quiz_channel):
        if self.current_round < self.questions_tiebreaker:
            await self.next_round(quiz_channel)
        else:
            await self.quiz_game_over(quiz_channel)

    async def tiebreaker_last_round(self, quiz_channel):
        await self.quiz_game_over(quiz_channel)

    @staticmethod
    async def tiebreaker_overwrites(channel, participants):
        overwrites = {
            channel.guild.default_role: discord.PermissionOverwrite(send_messages=False, view_channel=False)
        }

        for participant in participants:
            user = channel.guild.get_member(participant)
            if user:
                overwrites.update({user: discord.PermissionOverwrite(send_messages=True, view_channel=True)})

        await channel.edit(overwrites=overwrites)

    @staticmethod
    async def default_overwrites(channel):
        for user, perms in channel.overwrites.items():
            if isinstance(user, discord.Member):
                await channel.set_permissions(user, overwrite=None)

        await channel.set_permissions(channel.guild.default_role, send_messages=True, view_channel=False)

    @commands.Cog.listener('on_message')
    async def observer(self, message: discord.Message):
        if (message.guild is None or message.guild.id != GUILD_DDNET
                or message.channel.id != CHAN_ANSWERS or message.author.bot or not self._answer):
            return

        # asyncio.lock to prevent race condition issues
        if message.content.lower() == self._answer.lower():
            async with self.lock:
                await self.handle_correct_answer(message)

    @commands.has_role('Admin')
    @commands.command(name='qstart', help='Starts a quiz with specified parameters.', hidden=True)
    async def quiz_start(
            self,
            ctx: commands.Context,
            r: int = commands.parameter(
                description="Total amount of rounds per game",
                displayed_name='rounds'),
            rt: int = commands.parameter(
                description="Total amount of tiebreaker rounds per game",
                displayed_name='tiebreaker rounds')):

        if (ctx.guild is None or ctx.guild.id != GUILD_DDNET
                or ctx.channel.id != CHAN_ANSWERS or ctx.author.bot):
            return

        if not self.game_over:
            await ctx.reply('Quiz is already running.')
            return

        self.questions = int(r)
        self.questions_tiebreaker = int(rt)

        quiz_channel = self.bot.get_channel(TH_QUIZ)
        answer_channel = self.bot.get_channel(CHAN_ANSWERS)

        await self.default_overwrites(answer_channel)
        await ctx.message.delete()
        await self.start_round(quiz_channel)

    @commands.has_role('Admin')
    @commands.command(name='qstop', help='Stops an ongoing quiz', hidden=True)
    async def quiz_stop(self, ctx: commands.Context):
        if (ctx.guild is None or ctx.guild.id != GUILD_DDNET
                or ctx.channel.id != CHAN_ANSWERS or ctx.author.bot):
            return

        if self.game_over:
            reply = await ctx.reply('There is no ongoing quiz.')
            await reply.delete(delay=5)
            await ctx.message.delete(delay=5)
            return

        await self.reset(full_reset=True)

        quiz_channel = self.bot.get_channel(TH_QUIZ)
        await quiz_channel.purge()
        await ctx.message.delete()

    @commands.command(name='quiz_score')
    async def pull_score(self, ctx: commands.Context, *members: str):
        """
        Usage: $quiz_score <member>
        """
        _member = []
        _not_member = []

        if not members:
            _member = [ctx.author]

        for member_name in members:
            member = ctx.guild.get_member_named(member_name)
            if member:
                _member.append(member)
            else:
                _not_member.append(member_name)

        embed = discord.Embed(title='Quiz Scores', color=discord.Colour.random())

        for member in _member:
            try:
                rounds_won, maps_guessed = await self.get_score(str(member.id))
            except commands.MemberNotFound:
                _not_member.append(member.display_name)
                continue

            embed.add_field(
                name=member.display_name,
                value=f'```Rounds Won: {rounds_won}\nMaps Guessed: {maps_guessed}```',
                inline=False
            )

        if _not_member:
            embed.add_field(name='Members not found:', value='\n'.join(_not_member), inline=False)

        await ctx.reply(embed=embed)

    @commands.has_role('Admin')
    @commands.command()
    async def purge(self, ctx):
        if (ctx.guild is None or ctx.guild.id != GUILD_DDNET
                or ctx.channel.id != CHAN_ANSWERS or ctx.author.bot):
            return

        try:
            await ctx.send('Purging... This might take awhile.')
            await ctx.channel.purge(limit=50)
        except discord.Forbidden:
            await ctx.send("I don't have the necessary permissions to purge messages.")


async def setup(bot):
    await bot.add_cog(Teeguesser(bot))
