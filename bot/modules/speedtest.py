from pyrogram import filters
from subprocess import run as srun
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import bot, CMD_SUFFIX

async def speed_test(client, message):
    try:
        from speedtest import Speedtest
    except ImportError:
        srun(['pip3', 'install', 'speedtest-cli'])
        from speedtest import Speedtest
    st = Speedtest()
    download_speed = st.download() / 1_000_000 / 8
    upload_speed = st.upload() / 1_000_000 / 8
    msg = f"Download Speed: {download_speed:.2f} Mbps"
    msg += f"\nUpload Speed: {upload_speed:.2f} Mbps"
    await message.reply(msg)

bot.add_handler(MessageHandler(speed_test, filters=command(f"speedtest{CMD_SUFFIX}")))
