"""Isolated GraphQL CRUD scenarios.

Select exactly one class:
  locust -f locustfile_graphql_crud.py GraphQLGetUser \
    --host http://localhost:8002
"""

from __future__ import annotations

import random
from uuid import uuid4

import requests
from locust import HttpUser, between, task


N_USERS, N_MUSICS, N_PLAYLISTS = 400, 4000, 600


class GraphQLCrudUser(HttpUser):
    abstract = True
    wait_time = between(0.05, 0.2)

    def _endpoint(self) -> str:
        return f"{self.host.rstrip('/')}/graphql"

    def _direct(self, query: str) -> dict:
        response = requests.post(
            self._endpoint(),
            json={"query": query},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            raise RuntimeError(payload["errors"])
        return payload["data"]

    def _gql(self, query: str, name: str) -> dict | None:
        with self.client.post(
            "/graphql",
            name=name,
            json={"query": query},
            catch_response=True,
        ) as response:
            try:
                payload = response.json()
            except ValueError:
                response.failure("invalid json")
                return None
            if response.status_code != 200:
                response.failure(f"http {response.status_code}")
                return None
            if payload.get("errors"):
                response.failure("graphql errors")
                return None
            response.success()
            return payload.get("data")

    def _setup_user(self) -> int:
        data = self._direct(
            f'mutation{{createUser(name:"CRUD setup",'
            f'email:"crud-{uuid4().hex}@load.test"){{id}}}}'
        )
        return int(data["createUser"]["id"])

    def _setup_music(self) -> int:
        data = self._direct(
            'mutation{createMusic(title:"CRUD setup",artist:"Load test",'
            'album:"Temporary",durationSeconds:180){id}}'
        )
        return int(data["createMusic"]["id"])

    def _setup_playlist(self) -> int:
        data = self._direct(
            'mutation{createPlaylist(name:"CRUD setup",'
            f"userId:{random.randint(1, N_USERS)}){{id}}}}"
        )
        return int(data["createPlaylist"]["id"])

    def _cleanup(self, resource: str, resource_id: int) -> None:
        mutation = {
            "user": "deleteUser",
            "music": "deleteMusic",
            "playlist": "deletePlaylist",
        }[resource]
        self._direct(f"mutation{{{mutation}(id:{resource_id})}}")


# ---------- users ----------
class GraphQLListUsers(GraphQLCrudUser):
    @task
    def list_users(self):
        self._gql("{users(limit:50){id name email}}", "users")


class GraphQLGetUser(GraphQLCrudUser):
    @task
    def get_user(self):
        self._gql(
            f"{{user(id:{random.randint(1, N_USERS)}){{id name email}}}}",
            "user",
        )


class GraphQLCreateUser(GraphQLCrudUser):
    @task
    def create_user(self):
        data = self._gql(
            f'mutation{{createUser(name:"CRUD load",'
            f'email:"crud-{uuid4().hex}@load.test"){{id}}}}',
            "createUser",
        )
        if data and data.get("createUser"):
            self._cleanup("user", int(data["createUser"]["id"]))


class GraphQLUpdateUser(GraphQLCrudUser):
    def on_start(self):
        self.resource_id = self._setup_user()

    @task
    def update_user(self):
        self._gql(
            f'mutation{{updateUser(id:{self.resource_id},'
            f'name:"Updated {uuid4().hex[:8]}"){{id name}}}}',
            "updateUser",
        )

    def on_stop(self):
        self._cleanup("user", self.resource_id)


class GraphQLDeleteUser(GraphQLCrudUser):
    @task
    def delete_user(self):
        resource_id = self._setup_user()
        self._gql(
            f"mutation{{deleteUser(id:{resource_id})}}",
            "deleteUser",
        )


# ---------- musics ----------
class GraphQLListMusics(GraphQLCrudUser):
    @task
    def list_musics(self):
        self._gql(
            "{musics(limit:50){id title artist album durationSeconds}}",
            "musics",
        )


class GraphQLGetMusic(GraphQLCrudUser):
    @task
    def get_music(self):
        self._gql(
            f"{{music(id:{random.randint(1, N_MUSICS)})"
            "{id title artist album durationSeconds}}",
            "music",
        )


class GraphQLCreateMusic(GraphQLCrudUser):
    @task
    def create_music(self):
        data = self._gql(
            f'mutation{{createMusic(title:"Music {uuid4().hex[:8]}",'
            'artist:"Load test",album:"Temporary",durationSeconds:180){id}}',
            "createMusic",
        )
        if data and data.get("createMusic"):
            self._cleanup("music", int(data["createMusic"]["id"]))


class GraphQLUpdateMusic(GraphQLCrudUser):
    def on_start(self):
        self.resource_id = self._setup_music()

    @task
    def update_music(self):
        self._gql(
            f'mutation{{updateMusic(id:{self.resource_id},'
            f'title:"Updated {uuid4().hex[:8]}"){{id title}}}}',
            "updateMusic",
        )

    def on_stop(self):
        self._cleanup("music", self.resource_id)


class GraphQLDeleteMusic(GraphQLCrudUser):
    @task
    def delete_music(self):
        resource_id = self._setup_music()
        self._gql(
            f"mutation{{deleteMusic(id:{resource_id})}}",
            "deleteMusic",
        )


# ---------- playlists ----------
class GraphQLListPlaylists(GraphQLCrudUser):
    @task
    def list_playlists(self):
        self._gql("{playlists(limit:50){id name userId}}", "playlists")


class GraphQLGetPlaylist(GraphQLCrudUser):
    @task
    def get_playlist(self):
        self._gql(
            f"{{playlist(id:{random.randint(1, N_PLAYLISTS)})"
            "{id name userId}}",
            "playlist",
        )


class GraphQLCreatePlaylist(GraphQLCrudUser):
    @task
    def create_playlist(self):
        data = self._gql(
            f'mutation{{createPlaylist(name:"Playlist {uuid4().hex[:8]}",'
            f"userId:{random.randint(1, N_USERS)}){{id}}}}",
            "createPlaylist",
        )
        if data and data.get("createPlaylist"):
            self._cleanup("playlist", int(data["createPlaylist"]["id"]))


class GraphQLUpdatePlaylist(GraphQLCrudUser):
    def on_start(self):
        self.resource_id = self._setup_playlist()

    @task
    def update_playlist(self):
        self._gql(
            f'mutation{{updatePlaylist(id:{self.resource_id},'
            f'name:"Updated {uuid4().hex[:8]}"){{id name}}}}',
            "updatePlaylist",
        )

    def on_stop(self):
        self._cleanup("playlist", self.resource_id)


class GraphQLDeletePlaylist(GraphQLCrudUser):
    @task
    def delete_playlist(self):
        resource_id = self._setup_playlist()
        self._gql(
            f"mutation{{deletePlaylist(id:{resource_id})}}",
            "deletePlaylist",
        )
