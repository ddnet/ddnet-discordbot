#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import enum
import re

import discord
from discord.ext import commands

CHAN_DEVELOPER = 293493549758939136

_ISSUE_RE = r'(?:(?P<owner>\w+)/)?(?P<repo>[\w-]*)#(?P<id>[1-9]\d*)\b'
_REF_RE = r'[-\w]+'

def filter_empty(obj: dict) -> dict:
    return {k: v for k, v in obj.items() if v}


class BuildStatus(enum.Enum):
    UNKNOWN     = '❔'
    PENDING     = '🟡'
    FAILED      = '🔴'
    SUCCESS     = '🟢'

    def __str__(self) -> str:
        return self.value


class GithubException(Exception):
    pass


class GitHubBase():

    bot = None

    async def _fetch(self, url: str) -> dict:
        headers = {'Accept:': 'application/vnd.github.v3+json, application/vnd.github.antiope-preview+json'}
        async with self.bot.session.get(f'https://api.github.com/{url}', headers=headers) as resp:
            if resp.status != 200:
                raise RuntimeError

            return await resp.json()


class Commit(GitHubBase):
    def __init__(self, owner: str='ddnet', repo: str='ddnet', ref: str='master'):
        self.url = f'repos/{owner}/{repo}/commits/{ref}/check-suites'

    @classmethod
    async def convert(cls, ctx: commands.Context, argument: str):
        match = re.match(_ISSUE_RE, argument)
        if match:
            issue = await Issue.retrieve(**filter_empty(match.groupdict()))
            return await issue.get_pr_head()

        match = re.match(_REF_RE, argument)
        if match:
            return cls(ref=argument)

        raise GithubException('Invalid reference')

    async def get_status(self) -> BuildStatus:
        try:
            data = await self._fetch(self.url)
        except RuntimeError:
            raise GithubException('Commit/ref not found')

        if data['total_count'] == 0:
            return BuildStatus.UNKNOWN
        elif any(c['conclusion'] not in ('success', 'neutral') for c in data['check_suites']):
            return BuildStatus.FAILED
        elif any(c['status'] == 'pending' for c in data['check_suites']):
            return BuildStatus.PENDING
        else:
            return BuildStatus.SUCCESS


class Issue(GitHubBase):
    def __init__(self, owner: str, repo: str, id: str):
        self.owner = owner
        self.repo = repo
        self.id = id

    @classmethod
    async def retrieve(cls, *, owner: str='ddnet', repo: str='ddnet', id: str):
        self = cls(owner, repo , id)

        try:
            self.data = await self._fetch(f'repos/{owner}/{repo}/issues/{id}')
        except RuntimeError:
            raise GithubException('Issue not found')

        return self

    @property
    def link(self) -> str:
        return self.data['html_url']

    async def get_pr_head(self) -> Commit:
        if 'pull_request' not in self.data:
            raise GithubException('Given issue is not a PR')

        data = await self._fetch(f'repos/{self.owner}/{self.repo}/pulls/{self.id}')
        return Commit(self.owner, self.repo, data['head']['sha'])


class Github(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = GitHubBase.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id != CHAN_DEVELOPER or (message.content and message.content[0] == self.bot.command_prefix) or message.author.bot:
            return

        matches = re.finditer(_ISSUE_RE, message.content)
        links = []
        for match in matches:
            try:
                issue = await Issue.retrieve(**filter_empty(match.groupdict()))
            except GithubException:
                continue
            else:
                links.append(issue.link)

        if links:
            await message.channel.send('\n'.join(links))

    @commands.command(usage='[commit]')
    async def build_status(self, ctx: commands.Context, commit: Commit=Commit()):
        """Show the build status of a PR/commit"""
        status = await commit.get_status()
        await ctx.send(status)

    @build_status.error
    async def build_status_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error.original, GithubException):
            await ctx.send(error.original)


def setup(bot: commands.bot):
    bot.add_cog(Github(bot))
