"""Isolated SOAP CRUD scenarios.

Select exactly one class:
  locust -f locustfile_soap_crud.py SoapGetUser \
    --host http://localhost:8000
"""

from __future__ import annotations

import random
import re
from uuid import uuid4

import requests
from locust import HttpUser, between, task


N_USERS, N_MUSICS, N_PLAYLISTS = 400, 4000, 600
NS = (
    'xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
    'xmlns:tns="streaming.soap"'
)
HEADERS = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": '""'}


def envelope(body: str) -> str:
    return (
        f'<?xml version="1.0"?><soapenv:Envelope {NS}>'
        f"<soapenv:Body>{body}</soapenv:Body></soapenv:Envelope>"
    )


class SoapCrudUser(HttpUser):
    abstract = True
    wait_time = between(0.05, 0.2)

    def _endpoint(self) -> str:
        return f"{self.host.rstrip('/')}/"

    def _direct(self, body: str) -> str:
        response = requests.post(
            self._endpoint(),
            data=envelope(body),
            headers=HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        if "Fault" in response.text:
            raise RuntimeError("SOAP Fault")
        return response.text

    def _call(self, body: str, name: str) -> str | None:
        with self.client.post(
            "/",
            data=envelope(body),
            headers=HEADERS,
            name=name,
            catch_response=True,
        ) as response:
            if response.status_code != 200 or "Fault" in response.text:
                response.failure(f"soap fault/http {response.status_code}")
                return None
            response.success()
            return response.text

    def _id(self, xml: str) -> int:
        match = re.search(r"<[^>]*id>(\d+)<", xml)
        if not match:
            raise RuntimeError("id ausente na resposta SOAP")
        return int(match.group(1))

    def _setup_user(self) -> int:
        return self._id(
            self._direct(
                "<tns:createUser><tns:name>CRUD setup</tns:name>"
                f"<tns:email>crud-{uuid4().hex}@load.test</tns:email>"
                "</tns:createUser>"
            )
        )

    def _setup_music(self) -> int:
        return self._id(
            self._direct(
                "<tns:createMusic><tns:title>CRUD setup</tns:title>"
                "<tns:artist>Load test</tns:artist>"
                "<tns:album>Temporary</tns:album>"
                "<tns:duration_seconds>180</tns:duration_seconds>"
                "</tns:createMusic>"
            )
        )

    def _setup_playlist(self) -> int:
        return self._id(
            self._direct(
                "<tns:createPlaylist><tns:name>CRUD setup</tns:name>"
                f"<tns:user_id>{random.randint(1, N_USERS)}</tns:user_id>"
                "</tns:createPlaylist>"
            )
        )

    def _cleanup(self, resource: str, resource_id: int) -> None:
        operation = {
            "user": "deleteUser",
            "music": "deleteMusic",
            "playlist": "deletePlaylist",
        }[resource]
        self._direct(
            f"<tns:{operation}><tns:id>{resource_id}</tns:id>"
            f"</tns:{operation}>"
        )


# ---------- users ----------
class SoapListUsers(SoapCrudUser):
    @task
    def list_users(self):
        self._call(
            "<tns:listUsers><tns:limit>50</tns:limit>"
            "<tns:offset>0</tns:offset></tns:listUsers>",
            "listUsers",
        )


class SoapGetUser(SoapCrudUser):
    @task
    def get_user(self):
        resource_id = random.randint(1, N_USERS)
        self._call(
            f"<tns:getUser><tns:id>{resource_id}</tns:id></tns:getUser>",
            "getUser",
        )


class SoapCreateUser(SoapCrudUser):
    @task
    def create_user(self):
        xml = self._call(
            "<tns:createUser><tns:name>CRUD load</tns:name>"
            f"<tns:email>crud-{uuid4().hex}@load.test</tns:email>"
            "</tns:createUser>",
            "createUser",
        )
        if xml:
            self._cleanup("user", self._id(xml))


class SoapUpdateUser(SoapCrudUser):
    def on_start(self):
        self.resource_id = self._setup_user()

    @task
    def update_user(self):
        self._call(
            f"<tns:updateUser><tns:id>{self.resource_id}</tns:id>"
            f"<tns:name>Updated {uuid4().hex[:8]}</tns:name>"
            "</tns:updateUser>",
            "updateUser",
        )

    def on_stop(self):
        self._cleanup("user", self.resource_id)


class SoapDeleteUser(SoapCrudUser):
    @task
    def delete_user(self):
        resource_id = self._setup_user()
        self._call(
            f"<tns:deleteUser><tns:id>{resource_id}</tns:id>"
            "</tns:deleteUser>",
            "deleteUser",
        )


# ---------- musics ----------
class SoapListMusics(SoapCrudUser):
    @task
    def list_musics(self):
        self._call(
            "<tns:listMusics><tns:limit>50</tns:limit>"
            "<tns:offset>0</tns:offset></tns:listMusics>",
            "listMusics",
        )


class SoapGetMusic(SoapCrudUser):
    @task
    def get_music(self):
        resource_id = random.randint(1, N_MUSICS)
        self._call(
            f"<tns:getMusic><tns:id>{resource_id}</tns:id></tns:getMusic>",
            "getMusic",
        )


class SoapCreateMusic(SoapCrudUser):
    @task
    def create_music(self):
        xml = self._call(
            f"<tns:createMusic><tns:title>Music {uuid4().hex[:8]}</tns:title>"
            "<tns:artist>Load test</tns:artist>"
            "<tns:album>Temporary</tns:album>"
            "<tns:duration_seconds>180</tns:duration_seconds>"
            "</tns:createMusic>",
            "createMusic",
        )
        if xml:
            self._cleanup("music", self._id(xml))


class SoapUpdateMusic(SoapCrudUser):
    def on_start(self):
        self.resource_id = self._setup_music()

    @task
    def update_music(self):
        self._call(
            f"<tns:updateMusic><tns:id>{self.resource_id}</tns:id>"
            f"<tns:title>Updated {uuid4().hex[:8]}</tns:title>"
            "</tns:updateMusic>",
            "updateMusic",
        )

    def on_stop(self):
        self._cleanup("music", self.resource_id)


class SoapDeleteMusic(SoapCrudUser):
    @task
    def delete_music(self):
        resource_id = self._setup_music()
        self._call(
            f"<tns:deleteMusic><tns:id>{resource_id}</tns:id>"
            "</tns:deleteMusic>",
            "deleteMusic",
        )


# ---------- playlists ----------
class SoapListPlaylists(SoapCrudUser):
    @task
    def list_playlists(self):
        self._call(
            "<tns:listPlaylists><tns:limit>50</tns:limit>"
            "<tns:offset>0</tns:offset></tns:listPlaylists>",
            "listPlaylists",
        )


class SoapGetPlaylist(SoapCrudUser):
    @task
    def get_playlist(self):
        resource_id = random.randint(1, N_PLAYLISTS)
        self._call(
            f"<tns:getPlaylist><tns:id>{resource_id}</tns:id>"
            "</tns:getPlaylist>",
            "getPlaylist",
        )


class SoapCreatePlaylist(SoapCrudUser):
    @task
    def create_playlist(self):
        xml = self._call(
            f"<tns:createPlaylist><tns:name>Playlist {uuid4().hex[:8]}</tns:name>"
            f"<tns:user_id>{random.randint(1, N_USERS)}</tns:user_id>"
            "</tns:createPlaylist>",
            "createPlaylist",
        )
        if xml:
            self._cleanup("playlist", self._id(xml))


class SoapUpdatePlaylist(SoapCrudUser):
    def on_start(self):
        self.resource_id = self._setup_playlist()

    @task
    def update_playlist(self):
        self._call(
            f"<tns:updatePlaylist><tns:id>{self.resource_id}</tns:id>"
            f"<tns:name>Updated {uuid4().hex[:8]}</tns:name>"
            "</tns:updatePlaylist>",
            "updatePlaylist",
        )

    def on_stop(self):
        self._cleanup("playlist", self.resource_id)


class SoapDeletePlaylist(SoapCrudUser):
    @task
    def delete_playlist(self):
        resource_id = self._setup_playlist()
        self._call(
            f"<tns:deletePlaylist><tns:id>{resource_id}</tns:id>"
            "</tns:deletePlaylist>",
            "deletePlaylist",
        )
