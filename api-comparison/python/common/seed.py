"""Popula a base com massa de dados de teste (Faker).

Volume padrão: 500 usuários, 1000 músicas, 100 playlists, e relações
playlist<->música distribuídas aleatoriamente.

Uso:
    python -m common.seed            # volumes padrão
    USERS=500 MUSICS=1000 PLAYLISTS=100 python -m common.seed
"""
import os
import random
from faker import Faker
from sqlalchemy import select, func
from .db import engine, SessionLocal, Base, User, Music, Playlist, PlaylistMusic

fake = Faker("pt_BR")

N_USERS = int(os.getenv("USERS", 500))
N_MUSICS = int(os.getenv("MUSICS", 1000))
N_PLAYLISTS = int(os.getenv("PLAYLISTS", 100))

GENRES = ["Rock", "Pop", "MPB", "Jazz", "Eletrônica", "Hip-Hop", "Clássica",
          "Sertanejo", "Forró", "Reggae", "Metal", "Indie"]


def run() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        already = s.scalar(select(func.count()).select_from(User))
        if already and already > 0:
            print(f"[seed] base já populada ({already} usuários). Pulando.")
            return

        print("[seed] inserindo usuários...")
        users = []
        seen_emails = set()
        for _ in range(N_USERS):
            email = fake.unique.email()
            seen_emails.add(email)
            users.append(User(name=fake.name(), email=email))
        s.add_all(users); s.commit()

        print("[seed] inserindo músicas...")
        musics = [
            Music(
                title=fake.sentence(nb_words=3).rstrip("."),
                artist=fake.name(),
                album=f"{random.choice(GENRES)} {fake.word().capitalize()}",
                duration_seconds=random.randint(90, 420),
            )
            for _ in range(N_MUSICS)
        ]
        s.add_all(musics); s.commit()

        print("[seed] inserindo playlists...")
        user_ids = [u.id for u in s.scalars(select(User)).all()]
        playlists = [
            Playlist(name=f"{fake.word().capitalize()} Mix",
                     user_id=random.choice(user_ids))
            for _ in range(N_PLAYLISTS)
        ]
        s.add_all(playlists); s.commit()

        print("[seed] vinculando músicas às playlists...")
        music_ids = [m.id for m in s.scalars(select(Music)).all()]
        playlist_ids = [p.id for p in s.scalars(select(Playlist)).all()]
        links = []
        max_k = min(30, len(music_ids))
        min_k = min(5, max_k)
        for pid in playlist_ids:
            k = random.randint(min_k, max_k) if max_k > 0 else 0
            chosen = random.sample(music_ids, k=k)
            for pos, mid in enumerate(chosen):
                links.append(PlaylistMusic(playlist_id=pid, music_id=mid,
                                           position=pos))
        s.add_all(links); s.commit()

        print(f"[seed] OK: {N_USERS} usuários, {N_MUSICS} músicas, "
              f"{N_PLAYLISTS} playlists, {len(links)} vínculos.")


if __name__ == "__main__":
    run()
