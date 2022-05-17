# -*- coding: utf-8 -*-
import asyncio
from re import compile
from random import choice
from csv import writer
from PyMailGw import MailGwApi
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from os import environ
from time import time

_re = compile(r"https{0,1}:\/\/mega.nz\/#confirm[a-zA-Z0-9_-]{80,}")
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
        self.mapi = MailGwApi()
        self.email = await self.mapi.get_mail()
        if not self.email:
            for _ in range(3):
                await asyncio.sleep(3)
                self.email = await self.mapi.get_mail()
                if self.email:
                    break
        return self

    async def register(self):
        if not self.email: return
        registration = await asyncio.create_subprocess_shell(f"./megatools reg --scripted --register --email {self.email} --name {self.name} --password {self.password}", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
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
                if "MEGA" in mail["subject"]:
                    content = await self.mapi.get_message_content(mail['id'])
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
            await bot.edit_message_text(cid, mid, f"Ваше место в очереди: {len(users)-2} ({round(len(users)*0.3, 1)} минут).\n\nПодробнее - /help")
            m = True
            await asyncio.sleep(7)
        self.state = 2
        await bot.edit_message_text(cid, mid, "Получение временной почты...")
        try:
            acc = await MegaAccount("".join(choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") for x in range(24)), self.password).init_mail()
            await bot.edit_message_text(cid, mid, "Почта получена, регистрация...")
            await acc.register()
            await bot.edit_message_text(cid, mid, "Ожидание письма со ссылкой активации...")
            login, password = await acc.verify()
            await bot.edit_message_text(cid, mid, "Аккаунт зарегистрирован!")
            await bot.send_message(cid, f"Логин: `{login}`\nПароль: `{password}`", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            #print(e)
            await bot.send_message(cid, "Возникла неизвестная ошибка. Повторите попытку позже.")
        self.state = 3
        del users[self.id]

@bot.on_message(~filters.bot & filters.text & filters.command(["account"]))
async def command_account(_cl, message):
    if message.from_user.id in users:
        return await message.reply("Вы уже запросили аккаунт. Пожалуйста, подождите.")
    users[message.from_user.id] = User(message.from_user.id)
    return await message.reply("Отправьте пароль, который хотите установить на аккаунт (минимум 8 символов)")

@bot.on_message(~filters.bot & filters.text & (filters.command(["start"]) | filters.command(["help"])))
async def command_account(_cl, message):
    return await message.reply("Для получения аккаунта введите /account, а затем отправьте пароль, который вы хотите установить на аккаунт. Если нет очереди - вы получите аккаунт в течении 10-30 секунд. Очередь нужна для того, чтобы сервера временной почты и/или меги не получали слишком много запросов и в последствии не заблокировали работу бота.")

@bot.on_message(~filters.bot & filters.text)
async def message_account(_cl, message):
    if message.from_user.id not in users or not message.text:
        return
    if users[message.from_user.id].state != 0:
        return
    if len(message.text) < 8:
        return
    users[message.from_user.id].setPassword(message.text)
    msg = await message.reply(f"...")
    await users[message.from_user.id].register(msg.id, message.from_user.id)

if __name__ == "__main__":
    print("Bot running!")
    bot.run()