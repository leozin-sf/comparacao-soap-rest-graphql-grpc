"""Servidor gRPC. Adaptador fino sobre common.repository.

Os stubs streaming_pb2 / streaming_pb2_grpc são gerados a partir de
streaming.proto (ver Dockerfile / README).
"""
import os
import sys
from concurrent import futures
import grpc

sys.path.insert(0, os.path.dirname(__file__))
import streaming_pb2 as pb
import streaming_pb2_grpc as pbg

# permite importar o pacote common quando rodando de dentro de python/grpc
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from common import repository as repo
from common.db import init_db


def _user(d): return pb.User(id=d["id"], name=d["name"], email=d["email"])
def _music(d): return pb.Music(id=d["id"], title=d["title"], artist=d["artist"],
                               album=d["album"] or "",
                               duration_seconds=d["duration_seconds"])
def _playlist(d): return pb.Playlist(id=d["id"], name=d["name"],
                                     user_id=d["user_id"])


class Servicer(pbg.StreamingServiceServicer):
    # ---- users ----
    def CreateUser(self, req, ctx):
        return _user(repo.create_user(req.name, req.email))

    def GetUser(self, req, ctx):
        try:
            return _user(repo.get_user(req.id))
        except repo.NotFound:
            ctx.abort(grpc.StatusCode.NOT_FOUND, "user not found")

    def ListUsers(self, req, ctx):
        data = repo.list_users(req.limit or 100, req.offset)
        return pb.UserList(users=[_user(d) for d in data])

    def UpdateUser(self, req, ctx):
        try:
            return _user(repo.update_user(req.id, req.name or None,
                                          req.email or None))
        except repo.NotFound:
            ctx.abort(grpc.StatusCode.NOT_FOUND, "user not found")

    def DeleteUser(self, req, ctx):
        return pb.Ok(ok=repo.delete_user(req.id))

    # ---- musics ----
    def CreateMusic(self, req, ctx):
        return _music(repo.create_music(req.title, req.artist,
                                        req.album or None, req.duration_seconds))

    def GetMusic(self, req, ctx):
        try:
            return _music(repo.get_music(req.id))
        except repo.NotFound:
            ctx.abort(grpc.StatusCode.NOT_FOUND, "music not found")

    def ListMusics(self, req, ctx):
        data = repo.list_musics(req.limit or 100, req.offset)
        return pb.MusicList(musics=[_music(d) for d in data])

    def UpdateMusic(self, req, ctx):
        try:
            return _music(repo.update_music(
                req.id, req.title or None, req.artist or None,
                req.album or None,
                req.duration_seconds if req.duration_seconds else None))
        except repo.NotFound:
            ctx.abort(grpc.StatusCode.NOT_FOUND, "music not found")

    def DeleteMusic(self, req, ctx):
        return pb.Ok(ok=repo.delete_music(req.id))

    # ---- playlists ----
    def CreatePlaylist(self, req, ctx):
        try:
            return _playlist(repo.create_playlist(req.name, req.user_id))
        except repo.NotFound:
            ctx.abort(grpc.StatusCode.NOT_FOUND, "user not found")

    def GetPlaylist(self, req, ctx):
        try:
            return _playlist(repo.get_playlist(req.id))
        except repo.NotFound:
            ctx.abort(grpc.StatusCode.NOT_FOUND, "playlist not found")

    def ListPlaylists(self, req, ctx):
        data = repo.list_playlists(req.limit or 100, req.offset)
        return pb.PlaylistList(playlists=[_playlist(d) for d in data])

    def UpdatePlaylist(self, req, ctx):
        try:
            return _playlist(repo.update_playlist(req.id, req.name or None))
        except repo.NotFound:
            ctx.abort(grpc.StatusCode.NOT_FOUND, "playlist not found")

    def DeletePlaylist(self, req, ctx):
        return pb.Ok(ok=repo.delete_playlist(req.id))

    # ---- relações ----
    def ListUserPlaylists(self, req, ctx):
        data = repo.list_user_playlists(req.id)
        return pb.PlaylistList(playlists=[_playlist(d) for d in data])

    def ListPlaylistMusics(self, req, ctx):
        data = repo.list_playlist_musics(req.id)
        return pb.MusicList(musics=[_music(d) for d in data])

    def ListPlaylistsWithMusic(self, req, ctx):
        data = repo.list_playlists_with_music(req.id)
        return pb.PlaylistList(playlists=[_playlist(d) for d in data])

    def AddMusicToPlaylist(self, req, ctx):
        try:
            ok = repo.add_music_to_playlist(req.playlist_id, req.music_id,
                                            req.position)
            return pb.Ok(ok=ok)
        except repo.NotFound:
            ctx.abort(grpc.StatusCode.NOT_FOUND, "not found")

    def RemoveMusicFromPlaylist(self, req, ctx):
        return pb.Ok(ok=repo.remove_music_from_playlist(req.playlist_id,
                                                        req.music_id))


def serve():
    init_db()
    port = os.getenv("PORT", "50051")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))
    pbg.add_StreamingServiceServicer_to_server(Servicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"gRPC server ouvindo na porta {port}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
