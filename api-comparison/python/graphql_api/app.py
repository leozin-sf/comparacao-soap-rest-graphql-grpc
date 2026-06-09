"""Servidor GraphQL (Strawberry + FastAPI). Adaptador fino sobre o repositório.

Endpoint: POST /graphql  (GraphiQL habilitado em GET /graphql).
"""
from typing import Optional, List
import strawberry
from strawberry.fastapi import GraphQLRouter
from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool
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
    async def users(self, limit: int = 100, offset: int = 0) -> List[User]:
        data = await run_in_threadpool(repo.list_users, limit, offset)
        return [_u(d) for d in data]

    @strawberry.field
    async def user(self, id: int) -> Optional[User]:
        try:
            return _u(await run_in_threadpool(repo.get_user, id))
        except repo.NotFound:
            return None

    @strawberry.field
    async def musics(self, limit: int = 100, offset: int = 0) -> List[Music]:
        data = await run_in_threadpool(repo.list_musics, limit, offset)
        return [_m(d) for d in data]

    @strawberry.field
    async def music(self, id: int) -> Optional[Music]:
        try:
            return _m(await run_in_threadpool(repo.get_music, id))
        except repo.NotFound:
            return None

    @strawberry.field
    async def playlists(
        self, limit: int = 100, offset: int = 0
    ) -> List[Playlist]:
        data = await run_in_threadpool(repo.list_playlists, limit, offset)
        return [_p(d) for d in data]

    @strawberry.field
    async def playlist(self, id: int) -> Optional[Playlist]:
        try:
            return _p(await run_in_threadpool(repo.get_playlist, id))
        except repo.NotFound:
            return None

    @strawberry.field
    async def user_playlists(self, user_id: int) -> List[Playlist]:
        data = await run_in_threadpool(repo.list_user_playlists, user_id)
        return [_p(d) for d in data]

    @strawberry.field
    async def playlist_musics(self, playlist_id: int) -> List[Music]:
        data = await run_in_threadpool(
            repo.list_playlist_musics,
            playlist_id,
        )
        return [_m(d) for d in data]

    @strawberry.field
    async def playlists_with_music(self, music_id: int) -> List[Playlist]:
        data = await run_in_threadpool(
            repo.list_playlists_with_music,
            music_id,
        )
        return [_p(d) for d in data]


# ---------- mutations ----------
@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_user(self, name: str, email: str) -> User:
        return _u(await run_in_threadpool(repo.create_user, name, email))

    @strawberry.mutation
    async def update_user(
        self,
        id: int,
        name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Optional[User]:
        try:
            return _u(
                await run_in_threadpool(
                    repo.update_user,
                    id,
                    name,
                    email,
                )
            )
        except repo.NotFound:
            return None

    @strawberry.mutation
    async def delete_user(self, id: int) -> bool:
        return await run_in_threadpool(repo.delete_user, id)

    @strawberry.mutation
    async def create_music(
        self,
        title: str,
        artist: str,
        album: Optional[str] = None,
        duration_seconds: int = 0,
    ) -> Music:
        return _m(
            await run_in_threadpool(
                repo.create_music,
                title,
                artist,
                album,
                duration_seconds,
            )
        )

    @strawberry.mutation
    async def update_music(
        self,
        id: int,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ) -> Optional[Music]:
        try:
            return _m(
                await run_in_threadpool(
                    repo.update_music,
                    id,
                    title,
                    artist,
                    album,
                    duration_seconds,
                )
            )
        except repo.NotFound:
            return None

    @strawberry.mutation
    async def delete_music(self, id: int) -> bool:
        return await run_in_threadpool(repo.delete_music, id)

    @strawberry.mutation
    async def create_playlist(
        self,
        name: str,
        user_id: int,
    ) -> Optional[Playlist]:
        try:
            return _p(
                await run_in_threadpool(
                    repo.create_playlist,
                    name,
                    user_id,
                )
            )
        except repo.NotFound:
            return None

    @strawberry.mutation
    async def update_playlist(
        self,
        id: int,
        name: Optional[str] = None,
    ) -> Optional[Playlist]:
        try:
            return _p(
                await run_in_threadpool(
                    repo.update_playlist,
                    id,
                    name,
                )
            )
        except repo.NotFound:
            return None

    @strawberry.mutation
    async def delete_playlist(self, id: int) -> bool:
        return await run_in_threadpool(repo.delete_playlist, id)

    @strawberry.mutation
    async def add_music_to_playlist(
        self,
        playlist_id: int,
        music_id: int,
        position: int = 0,
    ) -> bool:
        try:
            return await run_in_threadpool(
                repo.add_music_to_playlist,
                playlist_id,
                music_id,
                position,
            )
        except repo.NotFound:
            return False

    @strawberry.mutation
    async def remove_music_from_playlist(
        self,
        playlist_id: int,
        music_id: int,
    ) -> bool:
        return await run_in_threadpool(
            repo.remove_music_from_playlist,
            playlist_id,
            music_id,
        )


schema = strawberry.Schema(query=Query, mutation=Mutation)
app = FastAPI(title="Streaming - GraphQL")


@app.on_event("startup")
def _startup():
    init_db()


app.include_router(GraphQLRouter(schema), prefix="/graphql")
