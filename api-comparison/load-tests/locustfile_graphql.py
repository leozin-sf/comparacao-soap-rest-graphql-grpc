"""Locust - GraphQL.
Executar: locust -f locustfile_graphql.py --host http://localhost:8002
Mesmo cenário do REST, expresso em queries/mutations GraphQL.
"""
import random
from uuid import uuid4
from locust import HttpUser, task, between, tag

N_USERS, N_MUSICS, N_PLAYLISTS = 400, 4000, 600


class GraphQLUser(HttpUser):
    wait_time = between(0.05, 0.2)

    def _gql(self, query, name):
        # validar erros GraphQL (HTTP 200 mesmo com erro) p/ refletir na taxa de erro
        with self.client.post("/graphql", name=name, json={"query": query},
                              catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"http {resp.status_code}")
            elif "errors" in (resp.json() or {}):
                resp.failure("graphql errors")
            else:
                resp.success()
        return resp

    @tag("read", "query", "list_musics")
    @task(5)
    def list_musics(self):
        self._gql("{ musics(limit:50){ id title artist } }", "musics")

    @tag("read", "query", "get_user")
    @task(4)
    def get_user(self):
        uid = random.randint(1, N_USERS)
        self._gql(f"{{ user(id:{uid}){{ id name email }} }}", "user")

    @tag("read", "query", "user_playlists")
    @task(3)
    def user_playlists(self):
        uid = random.randint(1, N_USERS)
        self._gql(f"{{ userPlaylists(userId:{uid}){{ id name }} }}", "userPlaylists")

    @tag("read", "query", "playlist_musics")
    @task(3)
    def playlist_musics(self):
        pid = random.randint(1, N_PLAYLISTS)
        self._gql(f"{{ playlistMusics(playlistId:{pid}){{ id title }} }}",
                  "playlistMusics")

    @tag("write", "mutation", "create", "create_user")
    @task(2)
    def create_user(self):
        e = f"u{uuid4().hex}@load.test"
        self._gql(f'mutation{{ createUser(name:"Load",email:"{e}"){{ id }} }}',
                  "createUser")

    @tag("write", "mutation", "create", "relation", "create_playlist_and_add")
    @task(1)
    def create_playlist_and_add(self):
        uid = random.randint(1, N_USERS)
        mid = random.randint(1, N_MUSICS)
        r = self._gql(f'mutation{{ createPlaylist(name:"PL",userId:{uid}){{ id }} }}',
                      "createPlaylist")
        try:
            pid = r.json()["data"]["createPlaylist"]["id"]
        except Exception:
            return
        self._gql(f"mutation{{ addMusicToPlaylist(playlistId:{pid},musicId:{mid}) }}",
                  "addMusicToPlaylist")
