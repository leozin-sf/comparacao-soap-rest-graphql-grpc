/**
 * Servidor gRPC em TypeScript (@grpc/grpc-js + @grpc/proto-loader).
 * Adaptador fino sobre o repositório compartilhado. Carrega o MESMO
 * streaming.proto usado pelo servidor gRPC em Python, garantindo contrato
 * idêntico. keepCase=true mantém os campos snake_case (user_id,
 * duration_seconds) iguais aos do repositório.
 */
import { fileURLToPath } from "node:url";
import * as grpc from "@grpc/grpc-js";
import * as protoLoader from "@grpc/proto-loader";
import { initDb, pool } from "../common/db.js";
import * as repo from "../common/repository.js";

const PROTO_PATH = fileURLToPath(new URL("../../proto/streaming.proto", import.meta.url));
const pkgDef = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true, longs: String, enums: String, defaults: true, oneofs: true,
});
const proto = grpc.loadPackageDefinition(pkgDef) as any;

const music = (m: repo.MusicDTO) => ({ ...m, album: m.album ?? "" });
type Cb = (err: grpc.ServiceError | null, res?: unknown) => void;

// Envolve um handler async, traduzindo NotFound -> status NOT_FOUND.
const h = (fn: (req: any) => Promise<unknown>) =>
  (call: { request: any }, cb: Cb) => {
    fn(call.request)
      .then((res) => cb(null, res))
      .catch((e: unknown) => {
        if (e instanceof repo.NotFound) {
          cb({ code: grpc.status.NOT_FOUND, message: e.message } as grpc.ServiceError);
        } else {
          console.error(e);
          cb({ code: grpc.status.INTERNAL, message: String(e) } as grpc.ServiceError);
        }
      });
  };

const impl = {
  // ---- users ----
  CreateUser: h((r) => repo.createUser(r.name, r.email)),
  GetUser:    h((r) => repo.getUser(r.id)),
  ListUsers:  h(async (r) => ({ users: await repo.listUsers(r.limit || 100, r.offset || 0) })),
  UpdateUser: h((r) => repo.updateUser(
    r.id,
    r.name || undefined,
    r.email || undefined,
  )),
  DeleteUser: h(async (r) => ({ ok: await repo.deleteUser(r.id) })),

  // ---- musics ----
  CreateMusic: h(async (r) => music(await repo.createMusic(r.title, r.artist, r.album, r.duration_seconds || 0))),
  GetMusic:    h(async (r) => music(await repo.getMusic(r.id))),
  ListMusics:  h(async (r) => ({ musics: (await repo.listMusics(r.limit || 100, r.offset || 0)).map(music) })),
  UpdateMusic: h(async (r) => music(await repo.updateMusic(r.id, r.title, r.artist, r.album, r.duration_seconds))),
  DeleteMusic: h(async (r) => ({ ok: await repo.deleteMusic(r.id) })),

  // ---- playlists ----
  CreatePlaylist: h((r) => repo.createPlaylist(r.name, r.user_id)),
  GetPlaylist:    h((r) => repo.getPlaylist(r.id)),
  ListPlaylists:  h(async (r) => ({ playlists: await repo.listPlaylists(r.limit || 100, r.offset || 0) })),
  UpdatePlaylist: h((r) => repo.updatePlaylist(r.id, r.name)),
  DeletePlaylist: h(async (r) => ({ ok: await repo.deletePlaylist(r.id) })),

  // ---- relações (consultas do enunciado) ----
  ListUserPlaylists:      h(async (r) => ({ playlists: await repo.listUserPlaylists(r.id) })),
  ListPlaylistMusics:     h(async (r) => ({ musics: (await repo.listPlaylistMusics(r.id)).map(music) })),
  ListPlaylistsWithMusic: h(async (r) => ({ playlists: await repo.listPlaylistsWithMusic(r.id) })),
  AddMusicToPlaylist:     h(async (r) => ({ ok: await repo.addMusicToPlaylist(r.playlist_id, r.music_id, r.position || 0) })),
  RemoveMusicFromPlaylist: h(async (r) => ({ ok: await repo.removeMusicFromPlaylist(r.playlist_id, r.music_id) })),
};

async function main() {
  await initDb();
  const server = new grpc.Server();
  server.addService(proto.streaming.StreamingService.service, impl as any);
  const PORT = process.env.PORT || "50052";
  server.bindAsync(`0.0.0.0:${PORT}`, grpc.ServerCredentials.createInsecure(), (err) => {
    if (err) { console.error(err); process.exit(1); }
    console.log(`gRPC (TypeScript) ouvindo na porta ${PORT}`);
  });
}

main().catch((e) => { console.error("Falha ao iniciar:", e); pool.end(); process.exit(1); });
