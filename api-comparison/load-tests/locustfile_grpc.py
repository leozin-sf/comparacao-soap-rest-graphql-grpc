"""Locust - gRPC.
Executar: locust -f locustfile_grpc.py --host localhost:50051
Usa um interceptor para medir latência de cada chamada e reportar ao Locust.
Os stubs streaming_pb2*/ são gerados a partir do .proto (ver Dockerfile).
"""
import random
from uuid import uuid4
import grpc
from grpc.experimental import gevent as grpc_gevent
from locust import User, task, between, events, tag
import time

import streaming_pb2 as pb
import streaming_pb2_grpc as pbg

# Permite que cada usuario virtual aguarde a RPC sem bloquear os demais
# greenlets do mesmo processo Locust.
grpc_gevent.init_gevent()

N_USERS, N_MUSICS, N_PLAYLISTS = 400, 4000, 600


class _Interceptor(grpc.UnaryUnaryClientInterceptor):
    """Mede o tempo de cada RPC e reporta como request_type='grpc'."""
    def intercept_unary_unary(self, continuation, details, request):
        start = time.perf_counter()
        exception = None
        resp = None
        try:
            resp = continuation(details, request)
            resp.result()  # força a conclusão p/ capturar erro/latência reais
        except grpc.RpcError as e:
            exception = e
        total = (time.perf_counter() - start) * 1000
        events.request.fire(
            request_type="grpc",
            name=details.method,
            response_time=total,
            response_length=resp.result().ByteSize() if (resp and not exception) else 0,
            exception=exception,
            context=None,
        )
        return resp


class GrpcUser(User):
    wait_time = between(0.05, 0.2)

    def on_start(self):
        target = self.host or "localhost:50051"
        channel = grpc.insecure_channel(target)
        channel = grpc.intercept_channel(channel, _Interceptor())
        self.stub = pbg.StreamingServiceStub(channel)

    @tag("read", "list_musics")
    @task(5)
    def list_musics(self):
        self.stub.ListMusics(pb.Page(limit=50, offset=0))

    @tag("read", "get_user")
    @task(4)
    def get_user(self):
        self.stub.GetUser(pb.Id(id=random.randint(1, N_USERS)))

    @tag("read", "user_playlists")
    @task(3)
    def user_playlists(self):
        self.stub.ListUserPlaylists(pb.Id(id=random.randint(1, N_USERS)))

    @tag("read", "playlist_musics")
    @task(3)
    def playlist_musics(self):
        self.stub.ListPlaylistMusics(pb.Id(id=random.randint(1, N_PLAYLISTS)))

    @tag("write", "create", "create_user")
    @task(2)
    def create_user(self):
        try:
            self.stub.CreateUser(pb.UserInput(
                name="Load", email=f"u{uuid4().hex}@load.test"))
        except grpc.RpcError:
            pass

    @tag("write", "create", "relation", "create_playlist_and_add")
    @task(1)
    def create_playlist_and_add(self):
        try:
            p = self.stub.CreatePlaylist(pb.PlaylistInput(
                name="PL", user_id=random.randint(1, N_USERS)))
            self.stub.AddMusicToPlaylist(pb.PlaylistMusicInput(
                playlist_id=p.id, music_id=random.randint(1, N_MUSICS),
                position=0))
        except grpc.RpcError:
            pass
