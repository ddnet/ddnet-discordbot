#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import time
from aiohttp import ClientSession
import asyncio
import enum
import discord
from discord.ext import commands

gh_api_base = "https://api.github.com"
gh_api_headers = {'Accept:': 'application/vnd.github.v3+json, application/vnd.github.antiope-preview+json'}

CHAN_DEVELOPER = 293493549758939136

issue_re = re.compile(r"(?:(\w*)/)?(\w*)#(\d+)\b")
branch_re = re.compile(r"[-\w]+")

class BuildStatus(enum.Enum):
    UNKNOWN     = '❔'
    PENDING     = '🟡'
    FAILED      = '🔴'
    SUCCESS     = '🟢'

    def __str__(self) -> str:
        return self.value

class CommitNotFound(Exception):
    pass

class IssueNotFound(Exception):
    pass

class IssueNotPR(Exception):
    pass

class Commit():
    def __init__(self, __owner: str, __repo: str, __ref: str):
        self.uri = gh_api_base + "/repos/{}/{}/commits/{}".format(__owner, __repo, __ref)
        self.commit = None

    async def get_status(self, session: ClientSession) -> BuildStatus:
        try:
            async with session.get(self.uri + "/check-suites", headers=gh_api_headers, raise_for_status=True) as resp:
                status = await resp.json()
        except:
            raise CommitNotFound

        if status['total_count'] == 0:
            return BuildStatus.UNKNOWN

        pending = False
        for c in status['check_suites']:
            if c['status'] == 'completed' and c['conclusion'] not in ['success', 'neutral']:
                return BuildStatus.FAILED
            elif c['status'] == 'pending':
                pending = True

        return BuildStatus.SUCCESS if not pending else BuildStatus.PENDING

class Issue():
    def resolve(self):
        if not self.owner:
            self.owner = "ddnet"
        if self.owner == "ddnet" and not self.repo:
            self.repo = "ddnet"
    def __init__(self, owner: str, repo: str, id: int):
        self.id = id
        self.owner = owner
        self.repo = repo
        self.issue = None
        self.resolve()

    async def get_issue(self, session: ClientSession) -> dict:
        if self.issue:
            return self.issue

        try:
            async with session.get(gh_api_base + "/repos/{}/{}/issues/{}".format(self.owner, self.repo, self.id), headers=gh_api_headers, raise_for_status=True) as resp:
                self.issue = await resp.json()
        except:
            raise IssueNotFound

        return self.issue

    async def get_link(self, session: ClientSession) -> str:
        issue = await self.get_issue(session)

        return issue['html_url']

    async def get_pr_head(self, session: ClientSession) -> Commit:
        issue = await self.get_issue(session)

        if not 'pull_request' in issue:
            raise IssueNotPR

        async with session.get(issue['pull_request']['url'], headers=gh_api_headers, raise_for_status=True) as resp:
            pr = await resp.json()

        return Commit(self.owner, self.repo, pr['head']['sha'])


class Github(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def cog_check(self, ctx: commands.Context):
        return ctx.channel.id == CHAN_DEVELOPER

    @commands.Cog.listener('on_message')
    async def get_ghlinks(self, message: discord.Message):
        if message.channel.id != CHAN_DEVELOPER or message.content[0] == self.bot.command_prefix or message.author.bot:
            return

        matches = issue_re.findall(message.content)
        matches = [(m[1], m[2], int(m[3])) for m in matches if int(m[2]) > 0]
        issues = [Issue(*m) for m in matches]
        links = await asyncio.gather(*[i.get_link(self.bot.session) for i in issues], return_exceptions=True)
        links = list(filter(lambda t: not isinstance(t, Exception), links))

        await message.channel.send('\n'.join(links))

    @commands.command()
    async def build_status(self, ctx: commands.Context, *args):
        if len(args) > 1:
            raise commands.TooManyArguments()

        commit = None
        if len(args) > 0:
            m = issue_re.fullmatch(args[0])
            if m:
                issue = Issue(m[1], m[2], int(m[3]))
                try:
                    commit = await issue.get_pr_head(self.bot.session)
                except IssueNotPR:
                    await ctx.channel.send("Given issue is not a PR")
                    return
                except IssueNotFound:
                    await ctx.channel.send("Issue not found")
                    return
            else:
                m = branch_re.fullmatch(args[0])
                if m:
                    commit = Commit("ddnet", "ddnet", args[0])
        else:
            commit = Commit("ddnet", "ddnet", "master")

        if commit:
            try:
                status = await commit.get_status(self.bot.session)
            except CommitNotFound:
                status = "Commit/ref not found"
            await ctx.channel.send(status)
        else:
            await ctx.channel.send("Invalid reference")

def setup(bot: commands.bot):
    bot.add_cog(Github(bot))
