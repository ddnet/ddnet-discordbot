# transcript.py: Collects all messages from a channel and writes them to a file.
import zipfile

MAX_ZIP_SIZE = 80 * 1024 * 1024

async def transcript(bot, ticket_channel):
    messages = []
    attachments = []
    zipped_files = []
    attachments_names = set()
    transcript_file = f'data/ticket-system/transcripts-temp/{ticket_channel.name}-{ticket_channel.id}.txt'
    attachment_zip_base = f'data/ticket-system/attachments-temp/attachments-{ticket_channel.name}-{ticket_channel.id}'

    channel = await bot.fetch_channel(ticket_channel.id)

    await ticket_channel.send(f'Collecting messages...')
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
                        ('.jpg', '.jpeg', '.png', '.gif',
                         '.mp4', '.avi', '.mkv', '.webm',
                         '.demo', '.map' '.txt', '.log', '.RTP')):
                    attachments.append((attachment_name, await attachment.read()))

                content += f"\nAttachments:\n{attachment_name}"

        messages.append(content)

    if len(messages) >= 2:
        transcript_data = "\n".join(messages)
        with open(transcript_file, "w", encoding="utf-8") as transcript:
            transcript.write(transcript_data)
    else:
        await ticket_channel.send(f'No messages found...')
        transcript_file = None

    if attachments:
        await ticket_channel.send(f'Compressing files...')
        zip_number = 1
        current_zip_size = 0
        current_zip = None

        for attachment_name, file_data in attachments:
            if current_zip is None or current_zip_size + len(file_data) > MAX_ZIP_SIZE:
                if current_zip is not None:
                    current_zip.close()
                    zipped_files.append(f"{attachment_zip_base}_{zip_number}.zip")
                    zip_number += 1
                current_zip_size = 0
                current_zip = zipfile.ZipFile(f"{attachment_zip_base}_{zip_number}.zip", 'w', zipfile.ZIP_STORED)

            current_zip.writestr(attachment_name, file_data)
            current_zip_size += len(file_data)

        if current_zip is not None:
            current_zip.close()
            zipped_files.append(f"{attachment_zip_base}_{zip_number}.zip")
    else:
        zipped_files = None

    return transcript_file, zipped_files
