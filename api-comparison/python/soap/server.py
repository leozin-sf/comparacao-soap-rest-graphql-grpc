"""Servidor SOAP (Spyne, SOAP 1.1). Adaptador fino sobre common.repository.

WSDL disponível em: http://host:8000/?wsdl
"""
import os
import sys
import _compat  # noqa: F401  (deve vir antes de qualquer import spyne)
from concurrent.futures import ThreadPoolExecutor

from spyne import Application, rpc, ServiceBase, Integer, Unicode, Boolean
from spyne.model.complex import ComplexModel, Array
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from wsgiref.simple_server import make_server, WSGIServer
from socketserver import ThreadingMixIn


class ThreadPoolWSGIServer(ThreadingMixIn, WSGIServer):
    """WSGI server com concorrência limitada para evitar uma thread por conexão."""

    daemon_threads = True
    request_queue_size = 1024

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        workers = int(os.getenv("SOAP_WORKERS", "100"))
        self.executor = ThreadPoolExecutor(max_workers=workers)

    def process_request(self, request, client_address):
        self.executor.submit(
            self.process_request_thread,
            request,
            client_address,
        )

    def server_close(self):
        super().server_close()
        self.executor.shutdown(wait=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from common import repository as repo
from common.db import init_db


# ---------- tipos complexos ----------
class UserT(ComplexModel):
    id = Integer
    name = Unicode
    email = Unicode


class MusicT(ComplexModel):
    id = Integer
    title = Unicode
    artist = Unicode
    album = Unicode
    duration_seconds = Integer


class PlaylistT(ComplexModel):
    id = Integer
    name = Unicode
    user_id = Integer


def _u(d): return UserT(id=d["id"], name=d["name"], email=d["email"])
def _m(d): return MusicT(id=d["id"], title=d["title"], artist=d["artist"],
                         album=d["album"], duration_seconds=d["duration_seconds"])
def _p(d): return PlaylistT(id=d["id"], name=d["name"], user_id=d["user_id"])


class StreamingService(ServiceBase):
    # ---- users ----
    @rpc(Unicode, Unicode, _returns=UserT)
    def createUser(ctx, name, email):
        return _u(repo.create_user(name, email))

    @rpc(Integer, _returns=UserT)
    def getUser(ctx, id):
        return _u(repo.get_user(id))

    @rpc(Integer, Integer, _returns=Array(UserT))
    def listUsers(ctx, limit, offset):
        return [_u(d) for d in repo.list_users(limit or 100, offset or 0)]

    @rpc(Integer, Unicode, Unicode, _returns=UserT)
    def updateUser(ctx, id, name, email):
        return _u(repo.update_user(id, name, email))

    @rpc(Integer, _returns=Boolean)
    def deleteUser(ctx, id):
        return repo.delete_user(id)

    # ---- musics ----
    @rpc(Unicode, Unicode, Unicode, Integer, _returns=MusicT)
    def createMusic(ctx, title, artist, album, duration_seconds):
        return _m(repo.create_music(title, artist, album,
                                    duration_seconds or 0))

    @rpc(Integer, _returns=MusicT)
    def getMusic(ctx, id):
        return _m(repo.get_music(id))

    @rpc(Integer, Integer, _returns=Array(MusicT))
    def listMusics(ctx, limit, offset):
        return [_m(d) for d in repo.list_musics(limit or 100, offset or 0)]

    @rpc(Integer, Unicode, Unicode, Unicode, Integer, _returns=MusicT)
    def updateMusic(ctx, id, title, artist, album, duration_seconds):
        return _m(repo.update_music(id, title, artist, album, duration_seconds))

    @rpc(Integer, _returns=Boolean)
    def deleteMusic(ctx, id):
        return repo.delete_music(id)

    # ---- playlists ----
    @rpc(Unicode, Integer, _returns=PlaylistT)
    def createPlaylist(ctx, name, user_id):
        return _p(repo.create_playlist(name, user_id))

    @rpc(Integer, _returns=PlaylistT)
    def getPlaylist(ctx, id):
        return _p(repo.get_playlist(id))

    @rpc(Integer, Integer, _returns=Array(PlaylistT))
    def listPlaylists(ctx, limit, offset):
        return [_p(d) for d in repo.list_playlists(limit or 100, offset or 0)]

    @rpc(Integer, Unicode, _returns=PlaylistT)
    def updatePlaylist(ctx, id, name):
        return _p(repo.update_playlist(id, name))

    @rpc(Integer, _returns=Boolean)
    def deletePlaylist(ctx, id):
        return repo.delete_playlist(id)

    # ---- relações ----
    @rpc(Integer, _returns=Array(PlaylistT))
    def listUserPlaylists(ctx, user_id):
        return [_p(d) for d in repo.list_user_playlists(user_id)]

    @rpc(Integer, _returns=Array(MusicT))
    def listPlaylistMusics(ctx, playlist_id):
        return [_m(d) for d in repo.list_playlist_musics(playlist_id)]

    @rpc(Integer, _returns=Array(PlaylistT))
    def listPlaylistsWithMusic(ctx, music_id):
        return [_p(d) for d in repo.list_playlists_with_music(music_id)]

    @rpc(Integer, Integer, Integer, _returns=Boolean)
    def addMusicToPlaylist(ctx, playlist_id, music_id, position):
        return repo.add_music_to_playlist(playlist_id, music_id, position or 0)

    @rpc(Integer, Integer, _returns=Boolean)
    def removeMusicFromPlaylist(ctx, playlist_id, music_id):
        return repo.remove_music_from_playlist(playlist_id, music_id)


application = Application(
    [StreamingService],
    tns="streaming.soap",
    in_protocol=Soap11(validator="lxml"),
    out_protocol=Soap11(),
)
wsgi_app = WsgiApplication(application)


if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", "8000"))
    print(f"SOAP server (WSDL em /?wsdl) na porta {port}")
    make_server("0.0.0.0", port, wsgi_app,
                server_class=ThreadPoolWSGIServer).serve_forever()
