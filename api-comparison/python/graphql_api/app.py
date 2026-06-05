"""Servidor GraphQL (Strawberry + FastAPI). Adaptador fino sobre o repositório.

Endpoint: POST /graphql  (GraphiQL habilitado em GET /graphql).
"""
from typing import Optional, List
import strawberry
from strawberry.fastapi import GraphQLRouter
from fastapi import FastAPI
from common import repository as repo
from common.db import init_db


# ---------- tipos ----------
@strawberry.type
class User:
    id: int
    name: str
    email: str


@strawberry.type
class Music:
    id: int
    title: str
    artist: str
    album: Optional[str]
    duration_seconds: int


@strawberry.type
class Playlist:
    id: int
    name: str
    user_id: int


def _u(d): return User(**d)
def _m(d): return Music(**d)
def _p(d): return Playlist(**d)


# ---------- queries ----------
@strawberry.type
class Query:
    @strawberry.field
    def users(self, limit: int = 100, offset: int = 0) -> List[User]:
        return [_u(d) for d in repo.list_users(limit, offset)]

    @strawberry.field
    def user(self, id: int) -> Optional[User]:
        try:
            return _u(repo.get_user(id))
        except repo.NotFound:
            return None

    @strawberry.field
    def musics(self, limit: int = 100, offset: int = 0) -> List[Music]:
        return [_m(d) for d in repo.list_musics(limit, offset)]

    @strawberry.field
    def music(self, id: int) -> Optional[Music]:
        try:
            return _m(repo.get_music(id))
        except repo.NotFound:
            return None

    @strawberry.field
    def playlists(self, limit: int = 100, offset: int = 0) -> List[Playlist]:
        return [_p(d) for d in repo.list_playlists(limit, offset)]

    @strawberry.field
    def playlist(self, id: int) -> Optional[Playlist]:
        try:
            return _p(repo.get_playlist(id))
        except repo.NotFound:
            return None

    @strawberry.field
    def user_playlists(self, user_id: int) -> List[Playlist]:
        return [_p(d) for d in repo.list_user_playlists(user_id)]

    @strawberry.field
    def playlist_musics(self, playlist_id: int) -> List[Music]:
        return [_m(d) for d in repo.list_playlist_musics(playlist_id)]

    @strawberry.field
    def playlists_with_music(self, music_id: int) -> List[Playlist]:
        return [_p(d) for d in repo.list_playlists_with_music(music_id)]


# ---------- mutations ----------
@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_user(self, name: str, email: str) -> User:
        return _u(repo.create_user(name, email))

    @strawberry.mutation
    def update_user(self, id: int, name: Optional[str] = None,
                    email: Optional[str] = None) -> Optional[User]:
        try:
            return _u(repo.update_user(id, name, email))
        except repo.NotFound:
            return None

    @strawberry.mutation
    def delete_user(self, id: int) -> bool:
        return repo.delete_user(id)

    @strawberry.mutation
    def create_music(self, title: str, artist: str,
                     album: Optional[str] = None,
                     duration_seconds: int = 0) -> Music:
        return _m(repo.create_music(title, artist, album, duration_seconds))

    @strawberry.mutation
    def update_music(self, id: int, title: Optional[str] = None,
                     artist: Optional[str] = None, album: Optional[str] = None,
                     duration_seconds: Optional[int] = None) -> Optional[Music]:
        try:
            return _m(repo.update_music(id, title, artist, album,
                                        duration_seconds))
        except repo.NotFound:
            return None

    @strawberry.mutation
    def delete_music(self, id: int) -> bool:
        return repo.delete_music(id)

    @strawberry.mutation
    def create_playlist(self, name: str, user_id: int) -> Optional[Playlist]:
        try:
            return _p(repo.create_playlist(name, user_id))
        except repo.NotFound:
            return None

    @strawberry.mutation
    def update_playlist(self, id: int,
                        name: Optional[str] = None) -> Optional[Playlist]:
        try:
            return _p(repo.update_playlist(id, name))
        except repo.NotFound:
            return None

    @strawberry.mutation
    def delete_playlist(self, id: int) -> bool:
        return repo.delete_playlist(id)

    @strawberry.mutation
    def add_music_to_playlist(self, playlist_id: int, music_id: int,
                              position: int = 0) -> bool:
        try:
            return repo.add_music_to_playlist(playlist_id, music_id, position)
        except repo.NotFound:
            return False

    @strawberry.mutation
    def remove_music_from_playlist(self, playlist_id: int,
                                   music_id: int) -> bool:
        return repo.remove_music_from_playlist(playlist_id, music_id)


schema = strawberry.Schema(query=Query, mutation=Mutation)
app = FastAPI(title="Streaming - GraphQL")


@app.on_event("startup")
def _startup():
    init_db()


app.include_router(GraphQLRouter(schema), prefix="/graphql")
