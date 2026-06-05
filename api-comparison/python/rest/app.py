"""Servidor REST (FastAPI). Adaptador fino sobre common.repository."""
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from common import repository as repo
from common.db import init_db

app = FastAPI(title="Streaming - REST")


@app.on_event("startup")
def _startup():
    init_db()


# ---------- schemas ----------
class UserIn(BaseModel):
    name: str
    email: str


class UserPatch(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class MusicIn(BaseModel):
    title: str
    artist: str
    album: Optional[str] = None
    duration_seconds: int = 0


class MusicPatch(BaseModel):
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    duration_seconds: Optional[int] = None


class PlaylistIn(BaseModel):
    name: str
    user_id: int


class PlaylistPatch(BaseModel):
    name: Optional[str] = None


def _nf(e):  # helper p/ traduzir NotFound em 404
    return HTTPException(status_code=404, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok", **repo.counts()}


# ---------- users ----------
@app.post("/users", status_code=201)
def create_user(body: UserIn):
    return repo.create_user(body.name, body.email)


@app.get("/users")
def list_users(limit: int = 100, offset: int = 0):
    return repo.list_users(limit, offset)


@app.get("/users/{user_id}")
def get_user(user_id: int):
    try:
        return repo.get_user(user_id)
    except repo.NotFound as e:
        raise _nf(e)


@app.patch("/users/{user_id}")
def update_user(user_id: int, body: UserPatch):
    try:
        return repo.update_user(user_id, body.name, body.email)
    except repo.NotFound as e:
        raise _nf(e)


@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int):
    if not repo.delete_user(user_id):
        raise HTTPException(404, "user not found")


@app.get("/users/{user_id}/playlists")
def user_playlists(user_id: int):
    return repo.list_user_playlists(user_id)


# ---------- musics ----------
@app.post("/musics", status_code=201)
def create_music(body: MusicIn):
    return repo.create_music(body.title, body.artist, body.album,
                             body.duration_seconds)


@app.get("/musics")
def list_musics(limit: int = 100, offset: int = 0):
    return repo.list_musics(limit, offset)


@app.get("/musics/{music_id}")
def get_music(music_id: int):
    try:
        return repo.get_music(music_id)
    except repo.NotFound as e:
        raise _nf(e)


@app.patch("/musics/{music_id}")
def update_music(music_id: int, body: MusicPatch):
    try:
        return repo.update_music(music_id, body.title, body.artist,
                                 body.album, body.duration_seconds)
    except repo.NotFound as e:
        raise _nf(e)


@app.delete("/musics/{music_id}", status_code=204)
def delete_music(music_id: int):
    if not repo.delete_music(music_id):
        raise HTTPException(404, "music not found")


@app.get("/musics/{music_id}/playlists")
def music_playlists(music_id: int):
    return repo.list_playlists_with_music(music_id)


# ---------- playlists ----------
@app.post("/playlists", status_code=201)
def create_playlist(body: PlaylistIn):
    try:
        return repo.create_playlist(body.name, body.user_id)
    except repo.NotFound as e:
        raise _nf(e)


@app.get("/playlists")
def list_playlists(limit: int = 100, offset: int = 0):
    return repo.list_playlists(limit, offset)


@app.get("/playlists/{playlist_id}")
def get_playlist(playlist_id: int):
    try:
        return repo.get_playlist(playlist_id)
    except repo.NotFound as e:
        raise _nf(e)


@app.patch("/playlists/{playlist_id}")
def update_playlist(playlist_id: int, body: PlaylistPatch):
    try:
        return repo.update_playlist(playlist_id, body.name)
    except repo.NotFound as e:
        raise _nf(e)


@app.delete("/playlists/{playlist_id}", status_code=204)
def delete_playlist(playlist_id: int):
    if not repo.delete_playlist(playlist_id):
        raise HTTPException(404, "playlist not found")


@app.get("/playlists/{playlist_id}/musics")
def playlist_musics(playlist_id: int):
    return repo.list_playlist_musics(playlist_id)


@app.put("/playlists/{playlist_id}/musics/{music_id}", status_code=204)
def add_music(playlist_id: int, music_id: int, position: int = 0):
    try:
        repo.add_music_to_playlist(playlist_id, music_id, position)
    except repo.NotFound as e:
        raise _nf(e)


@app.delete("/playlists/{playlist_id}/musics/{music_id}", status_code=204)
def remove_music(playlist_id: int, music_id: int):
    if not repo.remove_music_from_playlist(playlist_id, music_id):
        raise HTTPException(404, "link not found")
