import re


issue_re = r'(?:(?P<owner>\w*)/)?(?P<repo>\w*)#(?P<id>\d+)\b'

matches = re.finditer(issue_re, '12pm/ddnet-discordbot#1')
for match in matches:
    print(match.groupdict())