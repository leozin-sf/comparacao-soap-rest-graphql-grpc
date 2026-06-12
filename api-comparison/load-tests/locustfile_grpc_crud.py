"""Isolated gRPC CRUD scenarios.

Select exactly one class:
  locust -f locustfile_grpc_crud.py GrpcGetUser --host localhost:50051
"""

from __future__ import annotations

import random
import time
from uuid import uuid4

import grpc
from grpc.experimental import gevent as grpc_gevent
from locust import User, between, events, task

import streaming_pb2 as pb
import streaming_pb2_grpc as pbg


grpc_gevent.init_gevent()

N_USERS, N_MUSICS, N_PLAYLISTS = 400, 4000, 600


class _Interceptor(grpc.UnaryUnaryClientInterceptor):
    def intercept_unary_unary(self, continuation, details, request):
        started = time.perf_counter()
        exception = None
        response = None
        try:
            response = continuation(details, request)
            response.result()
        except grpc.RpcError as error:
            exception = error
        elapsed = (time.perf_counter() - started) * 1000
        events.request.fire(
            request_type="grpc",
            name=details.method,
            response_time=elapsed,
            response_length=(
                response.result().ByteSize()
                if response is not None and exception is None
                else 0
            ),
            exception=exception,
            context=None,
        )
        return response


class GrpcCrudUser(User):
    abstract = True
    wait_time = between(0.05, 0.2)

    def on_start(self):
        target = self.host or "localhost:50051"
        measured_channel = grpc.insecure_channel(target)
        self.measured_channel = grpc.intercept_channel(
            measured_channel,
            _Interceptor(),
        )
        self.stub = pbg.StreamingServiceStub(self.measured_channel)

    def on_stop(self):
        self.measured_channel.close()

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

    def _setup_user(self) -> int:
        result = self.stub.CreateUser(
            pb.UserInput(
                name="CRUD setup",
                email=f"crud-{uuid4().hex}@load.test",
            ),
            timeout=60,
        )
        return result.id

    def _setup_music(self) -> int:
        result = self.stub.CreateMusic(
            pb.MusicInput(
                title="CRUD setup",
                artist="Load test",
                album="Temporary",
                duration_seconds=180,
            ),
            timeout=60,
        )
        return result.id

    def _setup_playlist(self) -> int:
        result = self.stub.CreatePlaylist(
            pb.PlaylistInput(
                name="CRUD setup",
                user_id=random.randint(1, N_USERS),
            ),
            timeout=60,
        )
        return result.id

    def _cleanup(self, resource: str, resource_id: int) -> None:
        method = {
            "user": self.stub.DeleteUser,
            "music": self.stub.DeleteMusic,
            "playlist": self.stub.DeletePlaylist,
        }[resource]
        try:
            method(pb.Id(id=resource_id), timeout=60)
        except Exception as error:
            self._report_auxiliary_error(error)


# ---------- users ----------
class GrpcListUsers(GrpcCrudUser):
    @task
    def list_users(self):
        self.stub.ListUsers(pb.Page(limit=50, offset=0))


class GrpcGetUser(GrpcCrudUser):
    @task
    def get_user(self):
        self.stub.GetUser(pb.Id(id=random.randint(1, N_USERS)))


class GrpcCreateUser(GrpcCrudUser):
    @task
    def create_user(self):
        result = self.stub.CreateUser(
            pb.UserInput(
                name="CRUD load",
                email=f"crud-{uuid4().hex}@load.test",
            )
        )
        self._cleanup("user", result.id)


class GrpcUpdateUser(GrpcCrudUser):
    @task
    def update_user(self):
        self.stub.UpdateUser(
            pb.UserPatch(
                id=random.randint(1, N_USERS),
                name=f"Updated {uuid4().hex[:8]}",
            )
        )

class GrpcDeleteUser(GrpcCrudUser):
    @task
    def delete_user(self):
        resource_id = self._prepare(self._setup_user)
        if resource_id is None:
            return
        self.stub.DeleteUser(pb.Id(id=resource_id))


# ---------- musics ----------
class GrpcListMusics(GrpcCrudUser):
    @task
    def list_musics(self):
        self.stub.ListMusics(pb.Page(limit=50, offset=0))


class GrpcGetMusic(GrpcCrudUser):
    @task
    def get_music(self):
        self.stub.GetMusic(pb.Id(id=random.randint(1, N_MUSICS)))


class GrpcCreateMusic(GrpcCrudUser):
    @task
    def create_music(self):
        result = self.stub.CreateMusic(
            pb.MusicInput(
                title=f"Music {uuid4().hex[:8]}",
                artist="Load test",
                album="Temporary",
                duration_seconds=180,
            )
        )
        self._cleanup("music", result.id)


class GrpcUpdateMusic(GrpcCrudUser):
    @task
    def update_music(self):
        self.stub.UpdateMusic(
            pb.MusicPatch(
                id=random.randint(1, N_MUSICS),
                title=f"Updated {uuid4().hex[:8]}",
                artist="Load test",
                album="Temporary",
                duration_seconds=180,
            )
        )

class GrpcDeleteMusic(GrpcCrudUser):
    @task
    def delete_music(self):
        resource_id = self._prepare(self._setup_music)
        if resource_id is None:
            return
        self.stub.DeleteMusic(pb.Id(id=resource_id))


# ---------- playlists ----------
class GrpcListPlaylists(GrpcCrudUser):
    @task
    def list_playlists(self):
        self.stub.ListPlaylists(pb.Page(limit=50, offset=0))


class GrpcGetPlaylist(GrpcCrudUser):
    @task
    def get_playlist(self):
        self.stub.GetPlaylist(pb.Id(id=random.randint(1, N_PLAYLISTS)))


class GrpcCreatePlaylist(GrpcCrudUser):
    @task
    def create_playlist(self):
        result = self.stub.CreatePlaylist(
            pb.PlaylistInput(
                name=f"Playlist {uuid4().hex[:8]}",
                user_id=random.randint(1, N_USERS),
            )
        )
        self._cleanup("playlist", result.id)


class GrpcUpdatePlaylist(GrpcCrudUser):
    @task
    def update_playlist(self):
        self.stub.UpdatePlaylist(
            pb.PlaylistPatch(
                id=random.randint(1, N_PLAYLISTS),
                name=f"Updated {uuid4().hex[:8]}",
            )
        )

class GrpcDeletePlaylist(GrpcCrudUser):
    @task
    def delete_playlist(self):
        resource_id = self._prepare(self._setup_playlist)
        if resource_id is None:
            return
        self.stub.DeletePlaylist(pb.Id(id=resource_id))
