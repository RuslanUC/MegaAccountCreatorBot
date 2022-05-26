# -*- coding: utf-8 -*-
import asyncio
from re import compile
from random import choice
from csv import writer
from PyOneSecMail import OneSecMailApi
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from os import environ
from time import time
from json import dumps as jdumps

_re = compile(r"https{0,1}:\/\/mega.nz\/#confirm[a-zA-Z0-9_-]{80,512}")
bot = Client(
    "MegaNzBot",
    api_id=int(environ.get("API_ID")),
    api_hash=environ.get("API_HASH"),
    bot_token=environ.get("TG_BOT_TOKEN")
)
users = {}

class MegaAccount:
    def __init__(self, name, password):
        self.name = name
        self.password = password

    async def init_mail(self):
        self.mapi = OneSecMailApi()
        self.email = await self.mapi.get_mail()
        return self

    async def register(self):
        if not self.email: return
        registration = await asyncio.create_subprocess_shell(f"./megatools --scripted --register --email {self.email} --name {self.name} --password {self.password}", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        stdout, _ = await registration.communicate()
        self.verify_command = stdout.decode("utf8").strip()

    async def verify(self):
        if not self.email: return
        content = None
        for i in range(10):
            if content is not None:
                break
            await asyncio.sleep(3)
            for mail in await self.mapi.fetch_inbox():
                if "MEGA" in mail.subject or "mega" in mail.text.lower() or "mega" in mail.mfrom.lower():
                    content = mail.text
                    break

        link = _re.findall(content)
        self.verify_command = "./"+self.verify_command.replace("@LINK@", link[0])

        try:
            verification = await asyncio.create_subprocess_shell(self.verify_command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            stdout, _ = await verification.communicate()
        except Exception as e:
            return

        return (self.email, self.password)

class User:
    def __init__(self, id):
        self.id = id
        self.state = 0
        self.time = time()

    def setPassword(self, password):
        self.password = password
        self.state = 1

    async def register(self, mid, cid):
        m = False
        while list(users.keys()).index(self.id) not in range(4):
            await bot.edit_message_text(cid, mid, f"Your place in queue: {len(users)-2} ({round(len(users)*0.3, 1)} minutes).\n\nDetails - /help")
            m = True
            await asyncio.sleep(7)
        self.state = 2
        await bot.edit_message_text(cid, mid, "Requesting temporary email...")
        try:
            acc = await MegaAccount("".join(choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") for x in range(24)), self.password).init_mail()
            await bot.edit_message_text(cid, mid, "Email received, registering...")
            await acc.register()
            await bot.edit_message_text(cid, mid, "Waiting for an email with an activation link...")
            login, password = await acc.verify()
            await bot.edit_message_text(cid, mid, "Account registered!")
            await bot.send_message(cid, f"Login: `{login}`\nPassword: `{password}`", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            print(e)
            await bot.send_message(cid, "An unknown error occured. Please try again later.")
        self.state = 3
        del users[self.id]

@bot.on_message(~filters.bot & filters.text & filters.command(["account"]))
async def command_account(_cl, message):
    if message.from_user.id in users:
        return await message.reply("You already requested an account. Wait, please.")
    users[message.from_user.id] = User(message.from_user.id)
    return await message.reply("Send the password you want to set for your account (min. 8 characters)")

@bot.on_message(~filters.bot & filters.text & (filters.command(["start"]) | filters.command(["help"])))
async def command_account(_cl, message):
    return await message.reply("To get an account enter /account, and then send the password you want to set for your account. If there is no queue - you will get an account within 10-30 seconds. The queue is needed so that the temporary mail servers and/or mega.nz do not receive too many requests and do not block the bot.")

@bot.on_message(~filters.bot & filters.text)
async def message_account(_cl, message):
    if message.from_user.id not in users or not message.text:
        return
    if users[message.from_user.id].state != 0:
        return
    if len(message.text.replace("\"", "").replace(" ", "")) < 8:
        return
    users[message.from_user.id].setPassword(message.text.replace("\"", "").replace(" ", ""))
    msg = await message.reply(f"...")
    await users[message.from_user.id].register(msg.id, message.from_user.id)

if __name__ == "__main__":
    print("Bot running!")
    bot.run()