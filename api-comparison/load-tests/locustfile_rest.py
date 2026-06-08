"""Locust - REST.
Executar: locust -f locustfile_rest.py --host http://localhost:8001
Cenário típico do enunciado: criar/consultar usuário, listar músicas,
criar playlist, adicionar música em playlist, consultar playlists.
"""
import random
from uuid import uuid4
from locust import HttpUser, task, between, tag

# faixas conhecidas após o seed (500 users, 1000 musics, 100 playlists)
N_USERS, N_MUSICS, N_PLAYLISTS = 400, 4000, 600


class RestUser(HttpUser):
    wait_time = between(0.05, 0.2)

    @tag("read", "get", "list_musics")
    @task(5)
    def list_musics(self):
        self.client.get("/musics?limit=50", name="GET /musics")

    @tag("read", "get", "get_user")
    @task(4)
    def get_user(self):
        uid = random.randint(1, N_USERS)
        self.client.get(f"/users/{uid}", name="GET /users/:id")

    @tag("read", "get", "user_playlists")
    @task(3)
    def list_user_playlists(self):
        uid = random.randint(1, N_USERS)
        self.client.get(f"/users/{uid}/playlists", name="GET /users/:id/playlists")

    @tag("read", "get", "playlist_musics")
    @task(3)
    def list_playlist_musics(self):
        pid = random.randint(1, N_PLAYLISTS)
        self.client.get(f"/playlists/{pid}/musics", name="GET /playlists/:id/musics")

    @tag("write", "create", "post", "create_user")
    @task(2)
    def create_user(self):
        self.client.post("/users", name="POST /users", json={
            "name": f"User {random.random()}",
            "email": f"u{uuid4().hex}@load.test",
        })

    @tag("write", "create", "relation", "create_playlist_and_add")
    @task(1)
    def create_playlist_and_add(self):
        uid = random.randint(1, N_USERS)
        r = self.client.post("/playlists", name="POST /playlists",
                             json={"name": "Load PL", "user_id": uid})
        if r.status_code == 201:
            pid = r.json()["id"]
            mid = random.randint(1, N_MUSICS)
            self.client.put(f"/playlists/{pid}/musics/{mid}",
                            name="PUT /playlists/:id/musics/:id")
