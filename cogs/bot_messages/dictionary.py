# Okey this is a bit annoying. In order to have the bot link to the channels and roles, it needs the channel/role ids.

# Channels
WELCOME             = 1125706766999629854
ANNOUNCEMENTS       = 420565311863914496
MAP_RELEASES        = 392853737099624449
RECORDS             = 338779500085116938

DEVELOPER           = 293493549758939136
BUGS                = 757720336274948198

GENERAL             = 342454474117218334
SHOWROOM            = 295908390956433410
QUESTIONS           = 745926398140612678
WIKI                = 871738312849752104
OFF_TOPIC           = 252358080522747904
MAPPING             = 746534464984973323
BOT_CMDS            = 500032072455290880

TICKETS             = 1124657351442579486
SKIN_INFO           = 985554143525601350
SKIN_SUBM           = 985717921600929872
TESTING_INFO        = 1139589065759531038
TESTING_SUBM        = 455392372663123989

# Roles
ADMIN               = 293495272892399616
DISCORD_MOD         = 737776812234506270
MODERATOR           = 252523225810993153
TESTER              = 293543421426008064
TRIAL_TESTER        = 1193593067744284744
SKIN_DB_CREW        = 390516461741015040
WIKI_CONTRIBUTOR    = 1085663898910339072
DEV                 = 293541515781996568
TOURNAMENT_WINNER   = 400715872647249920
TESTING             = 455814387169755176

welcome_main = """
Welcome to the official DDraceNetwork Discord Server!

This server serves as the central hub for our vibrant gaming community. Here, you can chat with friends, forge new friendships, and engage in discussions about the game's development.

Feel free to ask any questions you may have, whether it's about mastering the mechanics of the game or troubleshooting any issues you encounter. Our dedicated community members and knowledgeable staff are here to assist you every step of the way.

**For more information about the game, you can visit the game’s Steam Store page:**
<https://store.steampowered.com/app/412220/DDraceNetwork/>
"""

welcome_rules = f"""
`#1` **Be nice** – Don't insult others or engage in lazy negativity towards other people's projects, even as a joke.
`#2` **No NSFW** - No pornography, gore, or anything that could be considered Not Safe For Work.
`#3` **Don't spam** - Includes all types of spamming (messages, emojis, reactions, etc.).
`#4` **Use channels only for their named purpose** - Off-topic goes to <#{OFF_TOPIC}>, Teeworlds related images and videos go to <#{SHOWROOM}>.
`#5` **Use English whenever possible** - If you want to talk in another language, do so in #off-topic.
`#6` **Keep drama out of here** - Sort out personal conflicts in DMs.
`#7` **Don't promote or encourage illegal activities** - Includes botting/cheating.
"""

welcome_channel_listing = f"""
**「INFO CATEGORY」**
<#{WELCOME}> - Welcome! Here you'll find basic information about our server and it's rules!
<#{ANNOUNCEMENTS}> - Any announcements about the game are posted here, including game update notes.
<#{MAP_RELEASES}> - Upcoming map releases are announcened in this channel!
<#{RECORDS}> - Every new record done on our official servers are posted in this channel.

**「Development」**
<#{DEVELOPER}> - Get a glimpse into the exciting realm of game development!
<#{BUGS}> - Here you can report bugs highlighting unintentional errors in the game.

**「DDraceNetwork」**
<#{GENERAL}> - This channel is for all Teeworlds, DDNet and related chat!
<#{SHOWROOM}> - Post videos, screenshots, and other content from the game here!
<#{QUESTIONS}> - Got Questions? Need Help? Ask Away!
<#{WIKI}> - A channel for collaborative knowledge building and discussions.
<#{MAPPING}> - Mapping discussions, questions, and map rating requests.
<#{OFF_TOPIC}> - Discuss anything unrelated to DDNet. Any languages allowed.
<#{BOT_CMDS}> - Game and server stats commands. Type /help for more info.

**「Tickets」**
<#{TICKETS}>- This channel is dedicated to addressing various issues and requests.

Here's a quick overview of the available categories:
- Report (For in-game issues, like race blockers)
- Rename Requests
- Ban Appeals
- Complaints
- Admin-Mail (for miscellaneous issues)
  * Note: No technical support.

**「Skin Submissions」**
<#{SKIN_INFO}> - Skin submission information and rules.
<#{SKIN_SUBM}> - Share and evaluate user-submitted player skins for our official database.

**「Map Testing」**
<#{TESTING_INFO}> - Discover the vital rules map creators must adhere to for their community-created maps to be released on DDNet in this channel.
<#{TESTING_SUBM}> - This is the channel where creators can upload their map creations for evaluation.
"""

welcome_ddnet_links = f"""
<https://ddnet.org/> - The official DDNet homepage
<https://forum.ddnet.org/> - Our forums for staff applications, Events, Tutorials and more
<https://wiki.ddnet.org/> - The official DDNet wiki, maintained by: <@!97739437772902400> and <@!846386020756226098>

**「For Developers」**
<https://github.com/ddnet/> - All ddnet related repositories that assist in managing our complete infrastructure

**「Our Discord Invite Links」**
<https://ddnet.org/discord/> OR <https://discord.gg/ddracenetwork>
"""

welcome_ddnet_roles = f"""
**「DDNet Staff」**
<@&{ADMIN}>: The administrators of DDNet.
<@&{DISCORD_MOD}>: People who keep our Discord server in check.
<@&{MODERATOR}>: People who moderate our in-game & discord server(s).

<@&{TESTER}>: Testers assess map suitability for our map pool, ensuring quality and reporting bugs to submitters.
<@&{TRIAL_TESTER}>: Much like the previous role, all incoming Testers will begin as Trial Testers.

<@&{SKIN_DB_CREW}>: The Skin Database Crew manages our skin database, ensuring suitability and quality.

**「Achievement Roles」**
<@&{WIKI_CONTRIBUTOR}>: Can be earned for Wiki contributions that are deemed significant.
<@&{DEV}>: Assigned to users with accepted pull requests on our main repository.
<@&{TOURNAMENT_WINNER}>: Assigned to users who have won tournaments.

**「Other」**
<@&{TESTING}>: All users can obtain this role in <#{TESTING_INFO}> to access all existing testing channels.
"""

welcome_community_links = """
**「Sites」**
<https://teeworlds.com/> - The official Teeworlds homepage
<https://skins.tw/> - A database containing game assets for both Teeworlds 0.6 and 0.7
<https://ddstats.org/status> || <https://ddstats.org/> - Alternative to https://ddnet.org/status/
<https://db.ddstats.org/> - Datasette instance of the official DDNet record database
<https://trashmap.ddnet.org/> - DDNet Trashmap is a service for mappers who can't host their own servers.

**「Other Community Servers」**
<https://discord.kog.tw/> - KoG (King of Gores)
<https://discord.gg/utB4Rs3> - FNG, hosted by @noby
<https://discord.gg/gbgEs7m6kK> - Unique, a server network that prioritizes maps specifically designed for racing.
<https://gores.pro/> - Gores Champions Ladder, Competitive Gores Mode
<https://discord.gg/mTVQuEDzzc> - Teeworlds Data, a hub for game asset resources.
<https://discord.gg/YnwAXPB3zj> - Tee Directory, another hub for game asset resources.
<https://discord.gg/fYaBTzY> - Blockworlds
<https://discord.gg/vYtgKvuvTS> - Tee Café, a server for making new friends and simply playing with other people to stay in touch!
<https://discord.gg/NUfhgTe> - iF|City, a city mod server to hang out with friends.

**「Non English Speaking Servers」**
<https://discord.gg/CauG396Waa> - Tee Olympics :flag_fr:
<https://discord.gg/2hdeGVtKdt> - New Generation Clan [NwG] + Community :flag_es:
<https://discord.gg/mpvWdvH> <> [QQ](https://qun.qq.com/qqweb/qunpro/share?_wv=3&_wwv=128&inviteCode=AI8a2&from=246610&biz=ka#/out) - Teeworlds中文社区 :flag_cn:
<https://discord.gg/vxgcBSnPPC> - DDRusNetwork :flag_ru:
<https://discord.gg/8SDH76SfXM> - 好問題 𝔾ძωт :flag_tw:
"""

testing_info_header = f"""
# :ddnet: Map release requirements
If you want to have your map released on DDNet, it has to follow the [mapping rules](https://ddnet.org/rules/).
If you're looking for tips on how to improve your submission, be sure to check out our [guidelines](https://ddnet.org/guidelines/).
"""

testing_info = f"""
# 📬 Map submissions
When you are ready to release it, send it in <#{TESTING_SUBM}>.
The message has to contain the map's details as follows: "<map_name>" by <mapper> [<server_type>]
```markdown
# Server Types
👶 Novice
🌸 Moderate
💪 Brutal
💀 Insane
♿ Dummy
👴 Oldschool
⚡ Solo
🏁 Race
🎉 Fun
```
`[Credits: Cøke, Jao, Ravie, Lady Saavik, Pipou, Patiga, Learath, RayB, Soreu, hi_leute_gll, Knight, Oblique. & Index]`
"""

testing_channel_access = f"""
# Accessing testing channels
- To see all channels, add a ✅ reaction to this message
- To see individual testing channels, add a ✅ reaction to the submission message in <#{TESTING_SUBM}> of the map's channel you want to see,
  removing the reaction reverts it
- Find archived channels at https://ddnet.org/testlogs/ 
"""
