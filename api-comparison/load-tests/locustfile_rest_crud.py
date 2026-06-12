"""Locust scenarios for isolated REST CRUD measurements.

Select exactly one user class on the command line:
  locust -f locustfile_rest_crud.py RestGetUser --host http://localhost:8001
"""

from __future__ import annotations

import random
from uuid import uuid4

from locust import HttpUser, between, task


N_USERS, N_MUSICS, N_PLAYLISTS = 400, 4000, 600


class RestCrudUser(HttpUser):
    abstract = True
    wait_time = between(0.05, 0.2)
    auxiliary_timeout = 60

    def _auxiliary_request(
        self,
        method: str,
        path: str,
        name: str,
        **kwargs,
    ):
        return self.client.request(
            method,
            path,
            name=name,
            timeout=self.auxiliary_timeout,
            **kwargs,
        )

    def _report_auxiliary_error(self, error: Exception) -> None:
        self.environment.events.user_error.fire(
            user_instance=self,
            exception=error,
            tb=error.__traceback__,
        )

    def _prepare(self, setup):
        try:
            return setup()
        except Exception as error:
            self._report_auxiliary_error(error)
            return None

    def _setup_post(self, path: str, json: dict) -> int:
        response = self._auxiliary_request(
            "POST",
            path,
            name=f"POST {path}",
            json=json,
        )
        response.raise_for_status()
        return int(response.json()["id"])

    def _cleanup(self, path: str, resource_id: int | None) -> None:
        if resource_id is not None:
            try:
                response = self._auxiliary_request(
                    "DELETE",
                    f"{path}/{resource_id}",
                    name=f"DELETE {path}/:id",
                )
                response.raise_for_status()
            except Exception as error:
                self._report_auxiliary_error(error)

    def _setup_user(self) -> int:
        return self._setup_post(
            "/users",
            {
                "name": "CRUD setup",
                "email": f"crud-{uuid4().hex}@load.test",
            },
        )

    def _setup_music(self) -> int:
        return self._setup_post(
            "/musics",
            {
                "title": "CRUD setup",
                "artist": "Load test",
                "album": "Temporary",
                "duration_seconds": 180,
            },
        )

    def _setup_playlist(self) -> int:
        return self._setup_post(
            "/playlists",
            {
                "name": "CRUD setup",
                "user_id": random.randint(1, N_USERS),
            },
        )


# ---------- users ----------
class RestListUsers(RestCrudUser):
    @task
    def list_users(self):
        self.client.get("/users?limit=50", name="GET /users")


class RestGetUser(RestCrudUser):
    @task
    def get_user(self):
        user_id = random.randint(1, N_USERS)
        self.client.get(f"/users/{user_id}", name="GET /users/:id")


class RestCreateUser(RestCrudUser):
    @task
    def create_user(self):
        response = self.client.post(
            "/users",
            name="POST /users",
            json={
                "name": "CRUD load",
                "email": f"crud-{uuid4().hex}@load.test",
            },
        )
        if response.status_code == 201:
            self._cleanup("/users", int(response.json()["id"]))


class RestUpdateUser(RestCrudUser):
    @task
    def update_user(self):
        resource_id = random.randint(1, N_USERS)
        self.client.patch(
            f"/users/{resource_id}",
            name="PATCH /users/:id",
            json={"name": f"Updated {uuid4().hex[:8]}"},
        )

class RestDeleteUser(RestCrudUser):
    @task
    def delete_user(self):
        resource_id = self._prepare(self._setup_user)
        if resource_id is None:
            return
        self.client.delete(f"/users/{resource_id}", name="DELETE /users/:id")


# ---------- musics ----------
class RestListMusics(RestCrudUser):
    @task
    def list_musics(self):
        self.client.get("/musics?limit=50", name="GET /musics")


class RestGetMusic(RestCrudUser):
    @task
    def get_music(self):
        music_id = random.randint(1, N_MUSICS)
        self.client.get(f"/musics/{music_id}", name="GET /musics/:id")


class RestCreateMusic(RestCrudUser):
    @task
    def create_music(self):
        response = self.client.post(
            "/musics",
            name="POST /musics",
            json={
                "title": f"Music {uuid4().hex[:8]}",
                "artist": "Load test",
                "album": "Temporary",
                "duration_seconds": 180,
            },
        )
        if response.status_code == 201:
            self._cleanup("/musics", int(response.json()["id"]))


class RestUpdateMusic(RestCrudUser):
    @task
    def update_music(self):
        resource_id = random.randint(1, N_MUSICS)
        self.client.patch(
            f"/musics/{resource_id}",
            name="PATCH /musics/:id",
            json={"title": f"Updated {uuid4().hex[:8]}"},
        )

class RestDeleteMusic(RestCrudUser):
    @task
    def delete_music(self):
        resource_id = self._prepare(self._setup_music)
        if resource_id is None:
            return
        self.client.delete(
            f"/musics/{resource_id}",
            name="DELETE /musics/:id",
        )


# ---------- playlists ----------
class RestListPlaylists(RestCrudUser):
    @task
    def list_playlists(self):
        self.client.get("/playlists?limit=50", name="GET /playlists")


class RestGetPlaylist(RestCrudUser):
    @task
    def get_playlist(self):
        playlist_id = random.randint(1, N_PLAYLISTS)
        self.client.get(
            f"/playlists/{playlist_id}",
            name="GET /playlists/:id",
        )


class RestCreatePlaylist(RestCrudUser):
    @task
    def create_playlist(self):
        response = self.client.post(
            "/playlists",
            name="POST /playlists",
            json={
                "name": f"Playlist {uuid4().hex[:8]}",
                "user_id": random.randint(1, N_USERS),
            },
        )
        if response.status_code == 201:
            self._cleanup("/playlists", int(response.json()["id"]))


class RestUpdatePlaylist(RestCrudUser):
    @task
    def update_playlist(self):
        resource_id = random.randint(1, N_PLAYLISTS)
        self.client.patch(
            f"/playlists/{resource_id}",
            name="PATCH /playlists/:id",
            json={"name": f"Updated {uuid4().hex[:8]}"},
        )

class RestDeletePlaylist(RestCrudUser):
    @task
    def delete_playlist(self):
        resource_id = self._prepare(self._setup_playlist)
        if resource_id is None:
            return
        self.client.delete(
            f"/playlists/{resource_id}",
            name="DELETE /playlists/:id",
        )
