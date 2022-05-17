from aiohttp import ClientSession
from os import environ
from urllib.parse import quote
from random import choice
import string

class MailGwApi:
    def __init__(self):
        self.headers = {}
        self.base_url = 'https://api.mail.gw'

    def getUrl(self, url):
        if (pdomain := environ.get("PROXY_DOMAIN")) and (pkey := environ.get("PROXY_KEY")):
            return f"https://{pdomain}/?url={quote(url)}&key={pkey}"
        return url
    
    async def get_domains(self):
        domains = []
        async with ClientSession() as session:
            async with session.get(self.getUrl(f'{self.base_url}/domains'), headers=self.headers) as resp:
                j = await resp.json()
                domains += [it["domain"] for it in j["hydra:member"]]

        return domains

    async def get_mail(self, name=None, password=None, domain=None):
        if not name:
            name = ''.join(choice(string.ascii_lowercase) for _ in range(15))
        mail = f'{name}@{domain if domain != None else (await self.get_domains())[0]}'

        try:
            async with ClientSession() as session:
                async with session.post(self.getUrl(f'{self.base_url}/accounts'), json={'address': mail, 'password': mail}, headers=self.headers) as resp:
                    assert resp.status == 201
                async with session.post(self.getUrl(f'{self.base_url}/token'), json={'address': mail, 'password': mail if password == None else password}, headers=self.headers) as resp:
                    j = await resp.json()
                    token = j['token']
                    self.headers['authorization'] = f'Bearer {token}'
                    return mail
        except Exception as e:
            print(f"{e.__class__.__name__}: {e!s}")
            return None
    
    async def fetch_inbox(self):
        print(self.headers)
        async with ClientSession() as session:
            async with session.get(self.getUrl(f'{self.base_url}/messages'), headers=self.headers) as resp:
                j = await resp.json()
        print(j)
        return j.get('hydra:member')
    
    async def get_message(self, message_id):
        async with ClientSession() as session:
            async with session.get(self.getUrl(f'{self.base_url}/messages/{message_id}'), headers=self.headers) as resp:
                j = await resp.json()
        return j
    
    async def get_message_content(self, message_id):
        return (await self.get_message(message_id))['text']