"""Locust - SOAP.
Executar: locust -f locustfile_soap.py --host http://localhost:8000
Envia envelopes SOAP 1.1 crus por HTTP POST.
"""
import random
from uuid import uuid4
from locust import HttpUser, task, between, tag

N_USERS, N_MUSICS, N_PLAYLISTS = 400, 4000, 600
NS = 'xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="streaming.soap"'
HEADERS = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": '""'}


def envelope(body: str) -> str:
    return (f'<?xml version="1.0"?><soapenv:Envelope {NS}>'
            f'<soapenv:Body>{body}</soapenv:Body></soapenv:Envelope>')


class SoapUser(HttpUser):
    wait_time = between(0.05, 0.2)

    def _call(self, body, name):
        with self.client.post("/", data=envelope(body), headers=HEADERS,
                              name=name, catch_response=True) as r:
            if r.status_code != 200 or "Fault" in r.text:
                r.failure(f"soap fault/http {r.status_code}")
            else:
                r.success()
        return r

    @tag("read", "list_musics")
    @task(5)
    def list_musics(self):
        self._call("<tns:listMusics><tns:limit>50</tns:limit>"
                   "<tns:offset>0</tns:offset></tns:listMusics>", "listMusics")

    @tag("read", "get_user")
    @task(4)
    def get_user(self):
        uid = random.randint(1, N_USERS)
        self._call(f"<tns:getUser><tns:id>{uid}</tns:id></tns:getUser>", "getUser")

    @tag("read", "user_playlists")
    @task(3)
    def user_playlists(self):
        uid = random.randint(1, N_USERS)
        self._call(f"<tns:listUserPlaylists><tns:user_id>{uid}</tns:user_id>"
                   "</tns:listUserPlaylists>", "listUserPlaylists")

    @tag("read", "playlist_musics")
    @task(3)
    def playlist_musics(self):
        pid = random.randint(1, N_PLAYLISTS)
        self._call(f"<tns:listPlaylistMusics><tns:playlist_id>{pid}"
                   "</tns:playlist_id></tns:listPlaylistMusics>", "listPlaylistMusics")

    @tag("write", "create", "create_user")
    @task(2)
    def create_user(self):
        e = f"u{uuid4().hex}@load.test"
        self._call(f"<tns:createUser><tns:name>Load</tns:name>"
                   f"<tns:email>{e}</tns:email></tns:createUser>", "createUser")

    @tag("write", "create", "relation", "create_playlist_and_add")
    @task(1)
    def create_playlist_and_add(self):
        uid = random.randint(1, N_USERS)
        mid = random.randint(1, N_MUSICS)
        r = self._call(f"<tns:createPlaylist><tns:name>PL</tns:name>"
                       f"<tns:user_id>{uid}</tns:user_id></tns:createPlaylist>",
                       "createPlaylist")
        # extrai o id da playlist criada do XML de resposta
        import re
        m = re.search(r"<[^>]*id>(\d+)<", r.text)
        if m:
            pid = m.group(1)
            self._call(f"<tns:addMusicToPlaylist><tns:playlist_id>{pid}"
                       f"</tns:playlist_id><tns:music_id>{mid}</tns:music_id>"
                       f"<tns:position>0</tns:position></tns:addMusicToPlaylist>",
                       "addMusicToPlaylist")
