# transcript.py: Collects all messages from a channel and writes them to a file.
import zipfile


async def transcript(bot, channel_id, transcript_filename, attachment_zip_filename):
    messages = []
    attachments_zip = []
    attachments_names = set()

    channel = await bot.fetch_channel(channel_id)

    async for message in channel.history(limit=None, oldest_first=True):
        if message.author.bot:
            continue

        created_at = message.created_at.replace(microsecond=0, tzinfo=None)
        content = f"{created_at} {message.author}: {message.content}"

        if message.attachments:
            for attachment in message.attachments:
                attachment_name = attachment.filename

                if attachment_name in attachments_names:
                    base_name, extension = attachment_name.rsplit('.', 1)
                    counter = 1
                    while f"{base_name}_{counter}.{extension}" in attachments_names:
                        counter += 1
                    attachment_name = f"{base_name}_{counter}.{extension}"

                attachments_names.add(attachment_name)

                if attachment.filename.endswith(
                        ('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.avi', '.mkv', '.demo', '.txt', '.log', '.RTP')):
                    attachments_zip.append((attachment_name, await attachment.read()))

                content += f"\nAttachments:\n{attachment_name}"

        messages.append(content)

    if len(messages) < 2:
        return

    transcript = "\n".join(messages)
    with open(transcript_filename, "w", encoding="utf-8") as f:
        f.write(transcript)

    if attachments_zip:
        with zipfile.ZipFile(attachment_zip_filename, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for attachment_name, file_data in attachments_zip:
                zip_file.writestr(attachment_name, file_data)

    return transcript_filename, attachment_zip_filename
