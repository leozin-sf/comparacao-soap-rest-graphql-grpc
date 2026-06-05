"""Repositório com TODA a lógica de negócio (CRUD + consultas do enunciado).

Cada servidor (SOAP/REST/GraphQL/gRPC) é apenas um adaptador fino sobre estas
funções. Nenhuma regra de negócio vive na camada de protocolo.

Convenção: as funções retornam dicionários simples (DTOs) para que cada
protocolo serialize do seu jeito sem acoplar ao ORM.
"""
from typing import Optional
from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session
from .db import SessionLocal, User, Music, Playlist, PlaylistMusic


# ---------- serialização para DTO ----------
def _user_dto(u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email}


def _music_dto(m: Music) -> dict:
    return {
        "id": m.id, "title": m.title, "artist": m.artist,
        "album": m.album, "duration_seconds": m.duration_seconds,
    }


def _playlist_dto(p: Playlist) -> dict:
    return {"id": p.id, "name": p.name, "user_id": p.user_id}


class NotFound(Exception):
    pass


# =================== USERS ===================
def create_user(name: str, email: str) -> dict:
    with SessionLocal() as s:
        u = User(name=name, email=email)
        s.add(u); s.commit(); s.refresh(u)
        return _user_dto(u)


def get_user(user_id: int) -> dict:
    with SessionLocal() as s:
        u = s.get(User, user_id)
        if not u:
            raise NotFound(f"user {user_id}")
        return _user_dto(u)


def list_users(limit: int = 100, offset: int = 0) -> list[dict]:
    with SessionLocal() as s:
        rows = s.scalars(
            select(User).order_by(User.id).limit(limit).offset(offset)
        ).all()
        return [_user_dto(u) for u in rows]


def update_user(user_id: int, name: Optional[str], email: Optional[str]) -> dict:
    with SessionLocal() as s:
        u = s.get(User, user_id)
        if not u:
            raise NotFound(f"user {user_id}")
        if name is not None:
            u.name = name
        if email is not None:
            u.email = email
        s.commit(); s.refresh(u)
        return _user_dto(u)


def delete_user(user_id: int) -> bool:
    with SessionLocal() as s:
        u = s.get(User, user_id)
        if not u:
            return False
        s.delete(u); s.commit()
        return True


# =================== MUSICS ===================
def create_music(title: str, artist: str, album: Optional[str],
                 duration_seconds: int) -> dict:
    with SessionLocal() as s:
        m = Music(title=title, artist=artist, album=album,
                  duration_seconds=duration_seconds)
        s.add(m); s.commit(); s.refresh(m)
        return _music_dto(m)


def get_music(music_id: int) -> dict:
    with SessionLocal() as s:
        m = s.get(Music, music_id)
        if not m:
            raise NotFound(f"music {music_id}")
        return _music_dto(m)


def list_musics(limit: int = 100, offset: int = 0) -> list[dict]:
    with SessionLocal() as s:
        rows = s.scalars(
            select(Music).order_by(Music.id).limit(limit).offset(offset)
        ).all()
        return [_music_dto(m) for m in rows]


def update_music(music_id: int, title: Optional[str], artist: Optional[str],
                 album: Optional[str], duration_seconds: Optional[int]) -> dict:
    with SessionLocal() as s:
        m = s.get(Music, music_id)
        if not m:
            raise NotFound(f"music {music_id}")
        if title is not None:
            m.title = title
        if artist is not None:
            m.artist = artist
        if album is not None:
            m.album = album
        if duration_seconds is not None:
            m.duration_seconds = duration_seconds
        s.commit(); s.refresh(m)
        return _music_dto(m)


def delete_music(music_id: int) -> bool:
    with SessionLocal() as s:
        m = s.get(Music, music_id)
        if not m:
            return False
        s.delete(m); s.commit()
        return True


# =================== PLAYLISTS ===================
def create_playlist(name: str, user_id: int) -> dict:
    with SessionLocal() as s:
        if not s.get(User, user_id):
            raise NotFound(f"user {user_id}")
        p = Playlist(name=name, user_id=user_id)
        s.add(p); s.commit(); s.refresh(p)
        return _playlist_dto(p)


def get_playlist(playlist_id: int) -> dict:
    with SessionLocal() as s:
        p = s.get(Playlist, playlist_id)
        if not p:
            raise NotFound(f"playlist {playlist_id}")
        return _playlist_dto(p)


def list_playlists(limit: int = 100, offset: int = 0) -> list[dict]:
    with SessionLocal() as s:
        rows = s.scalars(
            select(Playlist).order_by(Playlist.id).limit(limit).offset(offset)
        ).all()
        return [_playlist_dto(p) for p in rows]


def update_playlist(playlist_id: int, name: Optional[str]) -> dict:
    with SessionLocal() as s:
        p = s.get(Playlist, playlist_id)
        if not p:
            raise NotFound(f"playlist {playlist_id}")
        if name is not None:
            p.name = name
        s.commit(); s.refresh(p)
        return _playlist_dto(p)


def delete_playlist(playlist_id: int) -> bool:
    with SessionLocal() as s:
        p = s.get(Playlist, playlist_id)
        if not p:
            return False
        s.delete(p); s.commit()
        return True


# =========== CONSULTAS DO ENUNCIADO (relações) ===========
def list_user_playlists(user_id: int) -> list[dict]:
    """Todas as playlists de um determinado usuário."""
    with SessionLocal() as s:
        rows = s.scalars(
            select(Playlist).where(Playlist.user_id == user_id)
            .order_by(Playlist.id)
        ).all()
        return [_playlist_dto(p) for p in rows]


def list_playlist_musics(playlist_id: int) -> list[dict]:
    """Todas as músicas de uma determinada playlist (ordenadas por posição)."""
    with SessionLocal() as s:
        rows = s.execute(
            select(Music).join(PlaylistMusic, PlaylistMusic.music_id == Music.id)
            .where(PlaylistMusic.playlist_id == playlist_id)
            .order_by(PlaylistMusic.position)
        ).scalars().all()
        return [_music_dto(m) for m in rows]


def list_playlists_with_music(music_id: int) -> list[dict]:
    """Todas as playlists que contêm uma determinada música."""
    with SessionLocal() as s:
        rows = s.execute(
            select(Playlist).join(PlaylistMusic, PlaylistMusic.playlist_id == Playlist.id)
            .where(PlaylistMusic.music_id == music_id)
            .order_by(Playlist.id)
        ).scalars().all()
        return [_playlist_dto(p) for p in rows]


def add_music_to_playlist(playlist_id: int, music_id: int,
                          position: int = 0) -> bool:
    with SessionLocal() as s:
        if not s.get(Playlist, playlist_id):
            raise NotFound(f"playlist {playlist_id}")
        if not s.get(Music, music_id):
            raise NotFound(f"music {music_id}")
        exists = s.get(PlaylistMusic, (playlist_id, music_id))
        if exists:
            return True
        s.add(PlaylistMusic(playlist_id=playlist_id, music_id=music_id,
                            position=position))
        s.commit()
        return True


def remove_music_from_playlist(playlist_id: int, music_id: int) -> bool:
    with SessionLocal() as s:
        res = s.execute(
            delete(PlaylistMusic).where(
                PlaylistMusic.playlist_id == playlist_id,
                PlaylistMusic.music_id == music_id,
            )
        )
        s.commit()
        return res.rowcount > 0


def counts() -> dict:
    with SessionLocal() as s:
        return {
            "users": s.scalar(select(func.count()).select_from(User)),
            "musics": s.scalar(select(func.count()).select_from(Music)),
            "playlists": s.scalar(select(func.count()).select_from(Playlist)),
        }
