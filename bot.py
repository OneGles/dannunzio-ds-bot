import discord
from discord.ext import tasks
from datetime import time
from zoneinfo import ZoneInfo
from discord import AllowedMentions
import random
import os
import logging

TOKEN = os.getenv("TOKEN")  # token bot ds
SOURCE_CHANNEL_ID = int(os.getenv("SOURCE_CHANNEL_ID"))  # canale perle
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))  # canale dove scrive il bot
ROLE_ID = int(os.getenv("ROLE_ID"))  # ruolo dei membri da taggare
MAX_UPLOAD_SIZE = 8 * 1024 * 1024  # 8 MB di limite per colpa di ds
cached_messages = []  # salvataggio messaggi senza leggerli ogni volta

# timezone for scheduled tasks (IANA name, e.g. 'UTC' or 'Europe/Rome')
TIMEZONE = os.getenv("TIMEZONE", "UTC")
TZ = ZoneInfo(TIMEZONE)

intents = discord.Intents.default()
intents.message_content = True

# creazione client
client = discord.Client(intents=intents)
logger = logging.getLogger(__name__)

# ensure this module's logger emits INFO messages (add handler if needed)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s %(levelname)s:%(name)s: %(message)s")
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


# carica tutte le perle in array
async def load_messages():
    global cached_messages

    logger.info("Loading messages from source channel...")

    source_channel = client.get_channel(SOURCE_CHANNEL_ID)
    cached_messages = []

    async for msg in source_channel.history(limit=None):
        if msg.author.bot:
            continue

        # Carica Testo e url del mex originale
        if msg.content.strip():
            cached_messages.append(
                {
                    "type": "text",
                    "content": msg.content,
                    "attachments": [],
                    "jump_url": msg.jump_url,
                }
            )

        # Carica url e file del canale target
        if msg.attachments:
            cached_messages.append(
                {
                    "type": "attachment",
                    "jump_url": msg.jump_url,
                    "attachments": [
                        {"url": a.url, "size": a.size, "filename": a.filename}
                        for a in msg.attachments
                    ],
                }
            )

    logger.info("Loaded %d items", len(cached_messages))


@tasks.loop(time=time(hour=21, minute=0, second=0, tzinfo=TZ))
async def daily_post():
    logger.info("Posting daily message...")
    if not cached_messages:
        logger.info("No messages cached")
        return

    # index random compreso negli elementi dell'array, poi pop
    index = random.randrange(len(cached_messages))
    item = cached_messages.pop(index)

    # item = random.choice(cached_messages)

    # collegamento al canale target, tag del ruolo e link al mex originale
    target_channel = client.get_channel(TARGET_CHANNEL_ID)
    role_mention = f"<@&{ROLE_ID}>"
    source_link = f"\n\nMessaggio originale:\n{item['jump_url']}"

    # se è una stringa condividi il content e tagga
    if item["type"] == "text":
        await target_channel.send(
            content=f"{role_mention}\n{item['content']}{source_link}",
            allowed_mentions=AllowedMentions(roles=True),
        )

    # se è un file non stringa carica il file e tagga, se il file è troppo grande invia url
    elif item["type"] == "attachment":
        attachments = item["attachments"]

        total_size = sum(a["size"] for a in attachments)

        # caso 1: upload possibile
        if total_size <= MAX_UPLOAD_SIZE:
            files = []
            for a in attachments:
                file = await discord.File.from_url(a["url"], filename=a["filename"])
                files.append(file)

            await target_channel.send(
                content=f"{role_mention}{source_link}",
                files=files,
                allowed_mentions=AllowedMentions(roles=True),
            )

        # caso 2: troppo grandi → URL
        else:
            urls = "\n".join(a["url"] for a in attachments)
            await target_channel.send(
                content=f"{role_mention}\n{urls}{source_link}",
                allowed_mentions=AllowedMentions(roles=True),
            )

    logger.info("Posted daily message")


# viene chiamato una volta sola quando il bot è online
@client.event
async def on_ready():
    logger.info("Logged in as %s", client.user)

    await load_messages()
    # start short-running test loop and the daily poster
    daily_post.start()


# avvio bot
client.run(TOKEN)
