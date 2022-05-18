from aiohttp import ClientSession
from os import environ
from urllib.parse import quote
from random import choice
from datetime import datetime

class Message:
    def __init__(self, id, mfrom, subject, date, body, text, html):
        self.id = id
        self.mfrom = mfrom
        self.subject = subject
        self.date = date
        self.body = body
        self.text = text
        self.html = html

class OneSecMailApi:
    def __init__(self):
        self.base_url = 'https://www.1secmail.com/api/v1/'
        self.email = None
        self.login = None
        self.domain = None
        self.mailbox = []

    def getUrl(self, url):
        if (pdomain := environ.get("PROXY_DOMAIN")) and (pkey := environ.get("PROXY_KEY")):
            return f"https://{pdomain}/?url={quote(url)}&key={pkey}"
        return url

    async def get_mail(self):
        try:
            async with ClientSession() as session:
                async with session.get(self.getUrl(f'{self.base_url}/?action=genRandomMailbox&count=10')) as resp:
                    mail = choice(await resp.json())
                    self.email = mail
                    self.login, self.domain = mail.split("@")
                    return mail
        except Exception as e:
            print(f"{e.__class__.__name__}: {e!s}")
            return None
    
    async def fetch_inbox(self):
        async with ClientSession() as session:
            async with session.get(self.getUrl(f'{self.base_url}?action=getMessages&login={self.login}&domain={self.domain}')) as resp:
                for message in await resp.json():
                    if [m for m in self.mailbox if m.id == message["id"]]:
                        continue
                    self.mailbox.append(await self.get_message(message["id"]))
        return self.mailbox.copy()
    
    async def get_message(self, message_id):
        async with ClientSession() as session:
            async with session.get(self.getUrl(f'{self.base_url}?action=readMessage&login={self.login}&domain={self.domain}&id={message_id}')) as resp:
                j = await resp.json()
                msg = Message(
                    id=j.get("id"),
                    mfrom=j.get("from"),
                    subject=j.get("subject"),
                    date=datetime.fromisoformat(j.get("date")),
                    body=j.get("body"),
                    text=j.get("textBody"),
                    html=j.get("htmlBody")
                )
        return msg