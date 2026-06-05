"""Locust - GraphQL.
Executar: locust -f locustfile_graphql.py --host http://localhost:8002
Mesmo cenário do REST, expresso em queries/mutations GraphQL.
"""
import random
from locust import HttpUser, task, between

N_USERS, N_MUSICS, N_PLAYLISTS = 500, 1000, 100


class GraphQLUser(HttpUser):
    wait_time = between(0.1, 0.5)

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

    @task(5)
    def list_musics(self):
        self._gql("{ musics(limit:50){ id title artist } }", "musics")

    @task(4)
    def get_user(self):
        uid = random.randint(1, N_USERS)
        self._gql(f"{{ user(id:{uid}){{ id name email }} }}", "user")

    @task(3)
    def user_playlists(self):
        uid = random.randint(1, N_USERS)
        self._gql(f"{{ userPlaylists(userId:{uid}){{ id name }} }}", "userPlaylists")

    @task(3)
    def playlist_musics(self):
        pid = random.randint(1, N_PLAYLISTS)
        self._gql(f"{{ playlistMusics(playlistId:{pid}){{ id title }} }}",
                  "playlistMusics")

    @task(2)
    def create_user(self):
        e = f"u{random.randint(0, 10**9)}@load.test"
        self._gql(f'mutation{{ createUser(name:"Load",email:"{e}"){{ id }} }}',
                  "createUser")

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
