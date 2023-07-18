# transcript.py: Collects all messages from a channel and writes them to a file.

async def transcript(bot, channel_id, filename):
    channel = await bot.fetch_channel(channel_id)
    messages = []
    async for message in channel.history(limit=None, oldest_first=True):
        if message.author.bot:
            continue
        created_at = message.created_at.replace(microsecond=0, tzinfo=None)
        content = f"{created_at} {message.author}: {message.content}"

        if len(message.attachments) > 0:
            attachments = [attachment.url for attachment in message.attachments]
            attachment_link = '\n'.join(attachments)
            content += f"\nAttachments:\n{attachment_link}"

        messages.append(content)

    if len(messages) < 2:
        return

    transcript = "\n".join(messages)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(transcript)
