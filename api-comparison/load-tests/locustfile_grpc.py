"""Locust - gRPC.
Executar: locust -f locustfile_grpc.py --host localhost:50051
Usa um interceptor para medir latência de cada chamada e reportar ao Locust.
Os stubs streaming_pb2*/ são gerados a partir do .proto (ver Dockerfile).
"""
import time
import random
import grpc
from locust import User, task, between, events

import streaming_pb2 as pb
import streaming_pb2_grpc as pbg

N_USERS, N_MUSICS, N_PLAYLISTS = 500, 1000, 100


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
    wait_time = between(0.1, 0.5)

    def on_start(self):
        target = self.host or "localhost:50051"
        channel = grpc.insecure_channel(target)
        channel = grpc.intercept_channel(channel, _Interceptor())
        self.stub = pbg.StreamingServiceStub(channel)

    @task(5)
    def list_musics(self):
        self.stub.ListMusics(pb.Page(limit=50, offset=0))

    @task(4)
    def get_user(self):
        self.stub.GetUser(pb.Id(id=random.randint(1, N_USERS)))

    @task(3)
    def user_playlists(self):
        self.stub.ListUserPlaylists(pb.Id(id=random.randint(1, N_USERS)))

    @task(3)
    def playlist_musics(self):
        self.stub.ListPlaylistMusics(pb.Id(id=random.randint(1, N_PLAYLISTS)))

    @task(2)
    def create_user(self):
        self.stub.CreateUser(pb.UserInput(
            name="Load", email=f"u{random.randint(0, 10**9)}@load.test"))

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
