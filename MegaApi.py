from random import randint
from os import urandom
from codecs import latin_1_encode
from struct import unpack, pack
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from base64 import urlsafe_b64encode, urlsafe_b64decode as _urlsafe_b64decode
from aiohttp import ClientSession
from json import dumps as jdumps
from re import compile

def urlsafe_b64decode(data):
    data = data + b'=' * (-len(data) % 4)
    return _urlsafe_b64decode(data)

_re = compile(r"(?:https{0,1}:\/\/mega.nz\/#confirm)?([a-zA-Z0-9_-]{80,512})")

class Crypto:
    @staticmethod
    def make_random_key():
        return urandom(16)

    @staticmethod
    def make_rsa_keys():
        rsa = RSA.generate(2048)
        return (rsa.publickey().exportKey('DER'), rsa.exportKey('DER'))

    @staticmethod
    def make_password_key(password):
        pkey = [0x93C467E3, 0x7DB0C7A4, 0xD1BE3F81, 0x0152CB56]
        for r in range(0x10000):
            for j in range(0, len(password), 4):
                key = [0, 0, 0, 0]
                for i in range(4):
                    if i + j < len(password):
                        key[i] = password[i + j]
                pkey = Crypto.aes_cbc_encrypt_a32(pkey, key)
        return pkey

    @staticmethod
    def aes_cbc_encrypt_a32(data, key):
        return Crypto.str_to_a32(Crypto.aes_cbc_encrypt(Crypto.a32_to_str(data), Crypto.a32_to_str(key)))

    @staticmethod
    def str_to_a32(b):
        if isinstance(b, str):
            b = latin_1_encode(b)[0]
        if len(b) % 4:
            b += b'\0' * (4 - len(b) % 4)
        return unpack('>%dI' % (len(b) / 4), b)

    @staticmethod
    def a32_to_str(a):
        return pack('>%dI' % len(a), *a)

    @staticmethod
    def aes_cbc_encrypt(data, key):
        return AES.new(key, AES.MODE_CBC, latin_1_encode('\0' * 16)[0]).encrypt(data)

    @staticmethod
    def aes_cbc_decrypt(data, key):
        return AES.new(key, AES.MODE_CBC, latin_1_encode('\0' * 16)[0]).decrypt(data)

    @staticmethod
    def b64_aes_encrypt(data, key):
        return urlsafe_b64encode(Crypto.aes_cbc_encrypt(data, key))

    @staticmethod
    def b64_aes_decrypt(data, key):
        return Crypto.aes_cbc_decrypt(urlsafe_b64decode(data), key)

    @staticmethod
    def get_email_hash(email, key):
        hash = [0]*16

        for i in range(len(email)):
            hash[i%16] ^= email[i]

        hash = bytearray(hash)
        hash = Crypto.aes_cbc_encrypt(hash, key)
        oh = hash[:4]+hash[8:12]
        return urlsafe_b64encode(oh)

class MegaApi:
    def __init__(self):
        self.sid = None
        self.seq = randint(0, 0xFFFFFFFF)
        self.host = "https://g.api.mega.co.nz/cs"

    async def _api_call(self, j):
        p = {"id": self.seq}
        if self.sid:
            p["sid"] = self.sid
        if not isinstance(j, str):
            j = jdumps(j)
        async with ClientSession() as session:
            async with session.post(self.host, params=p, data=j) as resp:
                return await resp.json()

    async def register(self, login, password, name):
        master_key = Crypto.make_random_key()
        password_key = Crypto.a32_to_str(Crypto.make_password_key(Crypto.str_to_a32(password)))
        ts_data = Crypto.b64_aes_encrypt(urandom(32), master_key).decode("utf8")
        anon_user = (await self._api_call([{"a": "up", "k": Crypto.b64_aes_encrypt(master_key, password_key).decode("utf8"), "ts": ts_data}]))[0]
        self.sid = (await self._api_call([{"a": "us", "user": anon_user}]))[0]["tsid"]
        await self._api_call([{"a": "ug"}])
        await self._api_call([{"a": "up", "name": name}])
        c_data = master_key+urandom(4)+b"\x00"*8+urandom(4)
        c_data = Crypto.b64_aes_encrypt(c_data, password_key).decode("utf8")
        await self._api_call([{"a": "uc", "c": c_data, "n": urlsafe_b64encode(bytes(name, "utf8")).decode("utf8"), "m": urlsafe_b64encode(bytes(login, "utf8")).decode("utf8")}])
        self.password_key = password_key
        self.challenge = c_data[16:]

    async def verify(self, link):
        signup_key = _re.findall(link)
        if not signup_key:
            return
        signup_key = signup_key[0]
        data = (await self._api_call([{"a": "ud", "c": signup_key}]))[0]
        if len(data) != 5:
            return
        email = urlsafe_b64decode(bytes(data[0], "utf8"))
        master_key = Crypto.b64_aes_decrypt(bytes(data[3], "utf8"), self.password_key)
        uh = Crypto.get_email_hash(email.lower(), self.password_key).decode("utf8")
        await self._api_call([{"a": "up", "c": signup_key, "uh": uh}])
        self.sid = (await self._api_call([{"a": "us", "user": email.lower().decode("utf8"), "uh": uh}]))[0]["tsid"]
        pb, pr = Crypto.make_rsa_keys()
        await self._api_call([{"a": "up", "pubk": urlsafe_b64encode(pb).decode("utf8"), "privk": Crypto.b64_aes_encrypt(pr + b'\x00' * (-len(pr) % 16), master_key).decode("utf8")}])


async def main():
    m = MegaApi()
    await m.register("bhkquzykt@bluebasketbooks.com.au", "ksjdfhksjhd", "asdfasg")
    link = input("Link: ")
    await m.verify(link)

if __name__ == "__main__":
    import asyncio
    asyncio.get_event_loop().run_until_complete(main())