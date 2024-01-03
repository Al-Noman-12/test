from pyrogram import filters
from speedtest import Speedtest
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import bot

async def speed_test(client, message):
    st = Speedtest()
    download_speed = st.download() / 1_000_000 / 8
    upload_speed = st.upload() / 1_000_000 / 8
    msg = f"Download Speed: {download_speed:.2f} Mbps"
    msg+ = f"\nUpload Speed: {upload_speed:.2f} Mbps"
    await message.reply(msg)

bot.add_handler(MessageHandler(speed_test, filters=command(f"speedtest{CMD_SUFFIX}")))
