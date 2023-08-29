#!/usr/bin/env python3
from asyncio import Event
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import bot_name, config_dict, queued_dl, queued_up, non_queued_up, non_queued_dl, queue_dict_lock, LOGGER, download_dict, OWNER_ID, user_data
from bot.helper.ext_utils.fs_utils import get_base_name, check_storage_threshold
from bot.helper.ext_utils.bot_utils import sync_to_async, get_telegraph_list, checking_access, get_readable_file_size, get_user_tasks
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import forcesub, BotPm_check, send_to_pm


async def stop_duplicate_check(name, listener, isClone=None):
    msg = ""
    message = listener.message
    user_id = message.from_user.id
    
    if username := message.from_user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention

    if not isClone and (not config_dict['STOP_DUPLICATE'] or listener.isLeech or listener.upPath != 'gd' or listener.select):
        return False, None

    if listener.compress:
        name = f"{name}.zip"
    elif listener.extract:
        try:
            name = get_base_name(name)
        except:
            name = None
    if name is not None:
        telegraph_content, contents_no = await sync_to_async(GoogleDriveHelper(user_id=user_id).drive_list, name, stopDup=True)
        if telegraph_content:
            if config_dict['BOT_PM'] and message.chat.type != message.chat.type.PRIVATE:
                msg = f"\n\nFile/Folder is already available in Drive.\n\nI have sent available file link in pm."
                pmmsg = f"Hey {tag}.\n\nFile/Folder is already available in Drive.\n\nHere are {contents_no} list results:"
                pmbutton = await get_telegraph_list(telegraph_content)
                keyboard = InlineKeyboardButton("📥 Click Here To Go Bot PM", url=f"https://t.me/{bot_name}")
                button = InlineKeyboardMarkup([[keyboard]])
                await send_to_pm(message, text=pmmsg, buttons=pmbutton)
            else:
                msg = f"\n\nFile/Folder is already available in Drive.\n\nHere are {contents_no} list results:"
                button = await get_telegraph_list(telegraph_content)
        return msg, button
    return False, None


async def is_queued(uid):
    all_limit = config_dict['QUEUE_ALL']
    dl_limit = config_dict['QUEUE_DOWNLOAD']
    event = None
    added_to_queue = False
    if all_limit or dl_limit:
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            if (all_limit and dl + up >= all_limit and (not dl_limit or dl >= dl_limit)) or (dl_limit and dl >= dl_limit):
                added_to_queue = True
                event = Event()
                queued_dl[uid] = event
    return added_to_queue, event


def start_dl_from_queued(uid):
    queued_dl[uid].set()
    del queued_dl[uid]


def start_up_from_queued(uid):
    queued_up[uid].set()
    del queued_up[uid]


async def start_from_queued():
    if all_limit := config_dict['QUEUE_ALL']:
        dl_limit = config_dict['QUEUE_DOWNLOAD']
        up_limit = config_dict['QUEUE_UPLOAD']
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            all_ = dl + up
            if all_ < all_limit:
                f_tasks = all_limit - all_
                if queued_up and (not up_limit or up < up_limit):
                    for index, uid in enumerate(list(queued_up.keys()), start=1):
                        f_tasks = all_limit - all_
                        start_up_from_queued(uid)
                        f_tasks -= 1
                        if f_tasks == 0 or (up_limit and index >= up_limit - up):
                            break
                if queued_dl and (not dl_limit or dl < dl_limit) and f_tasks != 0:
                    for index, uid in enumerate(list(queued_dl.keys()), start=1):
                        start_dl_from_queued(uid)
                        if (dl_limit and index >= dl_limit - dl) or index == f_tasks:
                            break
        return

    if up_limit := config_dict['QUEUE_UPLOAD']:
        async with queue_dict_lock:
            up = len(non_queued_up)
            if queued_up and up < up_limit:
                f_tasks = up_limit - up
                for index, uid in enumerate(list(queued_up.keys()), start=1):
                    start_up_from_queued(uid)
                    if index == f_tasks:
                        break
    else:
        async with queue_dict_lock:
            if queued_up:
                for uid in list(queued_up.keys()):
                    start_up_from_queued(uid)

    if dl_limit := config_dict['QUEUE_DOWNLOAD']:
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            if queued_dl and dl < dl_limit:
                f_tasks = dl_limit - dl
                for index, uid in enumerate(list(queued_dl.keys()), start=1):
                    start_dl_from_queued(uid)
                    if index == f_tasks:
                        break
    else:
        async with queue_dict_lock:
            if queued_dl:
                for uid in list(queued_dl.keys()):
                    start_dl_from_queued(uid)


async def limit_checker(size, listener, isTorrent=False, isMega=False, isDriveLink=False, isLeech=False, isYtdlp=False):
    LOGGER.info('Checking Size Limit of link/file/folder/tasks...')
    user_id = listener.message.from_user.id
    if user_id == OWNER_ID or user_id in user_data and user_data[user_id].get('is_sudo'):
        return
    limit_exceeded = ''
    if listener.isClone:
        if CLONE_LIMIT := config_dict['CLONE_LIMIT']:
            limit = CLONE_LIMIT * 1024**3
            if size > limit:
                limit_exceeded = f'\nClone limit is {get_readable_file_size(limit)}'
    elif isMega:
        if MEGA_LIMIT := config_dict['MEGA_LIMIT']:
            limit = MEGA_LIMIT * 1024**3
            if size > limit:
                limit_exceeded = f'\nMega limit is {get_readable_file_size(limit)}'
    elif isDriveLink:
        if GDRIVE_LIMIT := config_dict['GDRIVE_LIMIT']:
            limit = GDRIVE_LIMIT * 1024**3
            if size > limit:
                limit_exceeded = f'\nGoogle drive limit is {get_readable_file_size(limit)}'
    elif isYtdlp:
        if YTDLP_LIMIT := config_dict['YTDLP_LIMIT']:
            limit = YTDLP_LIMIT * 1024**3
            if size > limit:
                limit_exceeded = f'\nYtdlp limit is {get_readable_file_size(limit)}'
    elif isTorrent:
        if TORRENT_LIMIT := config_dict['TORRENT_LIMIT']:
            limit = TORRENT_LIMIT * 1024**3
            if size > limit:
                limit_exceeded = f'\nTorrent limit is {get_readable_file_size(limit)}'
    elif MIRROR_LIMIT := config_dict['MIRROR_LIMIT']:
        limit = MIRROR_LIMIT * 1024**3
        if size > limit:
            limit_exceeded = f'\nDirect limit is {get_readable_file_size(limit)}'
    if not limit_exceeded:
        if (LEECH_LIMIT := config_dict['LEECH_LIMIT']) and listener.isLeech:
            limit = LEECH_LIMIT * 1024**3
            if size > limit:
                limit_exceeded = f'\nLeech limit is {get_readable_file_size(limit)}'
        
        if (STORAGE_THRESHOLD := config_dict['STORAGE_THRESHOLD']) and not listener.isClone:
            arch = any([listener.compress, listener.extract])
            limit = STORAGE_THRESHOLD * 1024**3
            acpt = await sync_to_async(check_storage_threshold, size, limit, arch)
            if not acpt:
                limit_exceeded = f'\nYou must leave {get_readable_file_size(limit)} free storage.'
    if limit_exceeded:
        return f"{limit_exceeded}.\nYour File/Folder size is {get_readable_file_size(size)}."


async def task_utils(message):
    msg = []
    button = None
    user_id = message.from_user.id
    user_dict = user_data.get(user_id, {})
    user = await message._client.get_users(user_id)
    
    if user_id == OWNER_ID:
        return msg, button
        
    token_msg, button = checking_access(message, button)
    if token_msg is not None:
        msg.append(token_msg)
        
    if ids := config_dict['FSUB_IDS']:
        _msg, button = await forcesub(message, ids, button)
        if _msg:
            msg.append(_msg)
            
    if config_dict['BOT_PM'] or user_dict.get('bot_pm'):
        if user.status == user.status.LONG_AGO:
            _msg, button = await BotPm_check(message, button)
            if _msg:
                msg.append(_msg)
        return msg, button
        
    if len(download_dict) >= config_dict['BOT_MAX_TASKS']:
        msg.append(f"Bot max tasks limit exceeded.\nBot max tasks limit is {config_dict['BOT_MAX_TASKS']}.\nPlease wait for the completion of other tasks.")
        return msg, button
        
    if (maxtask := config_dict['USER_MAX_TASKS']) and await get_user_tasks(message.from_user.id, maxtask):
        msg.append(f"User's max tasks limit is {maxtask}.\nPlease wait to complete your old tasks.")
    return msg, button
