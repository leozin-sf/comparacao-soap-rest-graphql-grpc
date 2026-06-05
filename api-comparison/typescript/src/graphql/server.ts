/**
 * Servidor GraphQL em TypeScript (graphql-yoga). Adaptador fino sobre o
 * repositório compartilhado (../common/repository.ts). Espelha o schema do
 * serviço GraphQL em Python (Strawberry): mesmos tipos, queries e mutations.
 * Endpoint: POST /graphql (GraphiQL em GET /graphql).
 */
import { createServer } from "node:http";
import { createYoga, createSchema } from "graphql-yoga";
import { initDb } from "../common/db.js";
import * as repo from "../common/repository.js";

// O repositório devolve chaves snake_case (duration_seconds, user_id);
// o schema GraphQL usa camelCase (como o Strawberry gera). Mapeamos aqui.
const toMusic = (m: repo.MusicDTO) => ({
  id: m.id, title: m.title, artist: m.artist,
  album: m.album, durationSeconds: m.duration_seconds,
});
const toPlaylist = (p: repo.PlaylistDTO) => ({
  id: p.id, name: p.name, userId: p.user_id,
});

const typeDefs = /* GraphQL */ `
  type User     { id: Int!, name: String!, email: String! }
  type Music     { id: Int!, title: String!, artist: String!, album: String, durationSeconds: Int! }
  type Playlist { id: Int!, name: String!, userId: Int! }

  type Query {
    users(limit: Int = 100, offset: Int = 0): [User!]!
    user(id: Int!): User
    musics(limit: Int = 100, offset: Int = 0): [Music!]!
    music(id: Int!): Music
    playlists(limit: Int = 100, offset: Int = 0): [Playlist!]!
    playlist(id: Int!): Playlist
    userPlaylists(userId: Int!): [Playlist!]!
    playlistMusics(playlistId: Int!): [Music!]!
    playlistsWithMusic(musicId: Int!): [Playlist!]!
  }

  type Mutation {
    createUser(name: String!, email: String!): User!
    updateUser(id: Int!, name: String, email: String): User
    deleteUser(id: Int!): Boolean!
    createMusic(title: String!, artist: String!, album: String, durationSeconds: Int = 0): Music!
    updateMusic(id: Int!, title: String, artist: String, album: String, durationSeconds: Int): Music
    deleteMusic(id: Int!): Boolean!
    createPlaylist(name: String!, userId: Int!): Playlist
    updatePlaylist(id: Int!, name: String): Playlist
    deletePlaylist(id: Int!): Boolean!
    addMusicToPlaylist(playlistId: Int!, musicId: Int!, position: Int = 0): Boolean!
    removeMusicFromPlaylist(playlistId: Int!, musicId: Int!): Boolean!
  }
`;

const nullOnNotFound = async <T>(fn: () => Promise<T>): Promise<T | null> => {
  try { return await fn(); }
  catch (e) { if (e instanceof repo.NotFound) return null; throw e; }
};

const resolvers = {
  Query: {
    users: (_: unknown, a: { limit: number; offset: number }) =>
      repo.listUsers(a.limit, a.offset),
    user: (_: unknown, a: { id: number }) =>
      nullOnNotFound(() => repo.getUser(a.id)),
    musics: async (_: unknown, a: { limit: number; offset: number }) =>
      (await repo.listMusics(a.limit, a.offset)).map(toMusic),
    music: (_: unknown, a: { id: number }) =>
      nullOnNotFound(async () => toMusic(await repo.getMusic(a.id))),
    playlists: async (_: unknown, a: { limit: number; offset: number }) =>
      (await repo.listPlaylists(a.limit, a.offset)).map(toPlaylist),
    playlist: (_: unknown, a: { id: number }) =>
      nullOnNotFound(async () => toPlaylist(await repo.getPlaylist(a.id))),
    userPlaylists: async (_: unknown, a: { userId: number }) =>
      (await repo.listUserPlaylists(a.userId)).map(toPlaylist),
    playlistMusics: async (_: unknown, a: { playlistId: number }) =>
      (await repo.listPlaylistMusics(a.playlistId)).map(toMusic),
    playlistsWithMusic: async (_: unknown, a: { musicId: number }) =>
      (await repo.listPlaylistsWithMusic(a.musicId)).map(toPlaylist),
  },
  Mutation: {
    createUser: (_: unknown, a: { name: string; email: string }) =>
      repo.createUser(a.name, a.email),
    updateUser: (_: unknown, a: { id: number; name?: string; email?: string }) =>
      nullOnNotFound(() => repo.updateUser(a.id, a.name, a.email)),
    deleteUser: (_: unknown, a: { id: number }) => repo.deleteUser(a.id),
    createMusic: async (_: unknown, a: { title: string; artist: string; album?: string; durationSeconds?: number }) =>
      toMusic(await repo.createMusic(a.title, a.artist, a.album ?? null, a.durationSeconds ?? 0)),
    updateMusic: (_: unknown, a: { id: number; title?: string; artist?: string; album?: string; durationSeconds?: number }) =>
      nullOnNotFound(async () => toMusic(await repo.updateMusic(a.id, a.title, a.artist, a.album, a.durationSeconds))),
    deleteMusic: (_: unknown, a: { id: number }) => repo.deleteMusic(a.id),
    createPlaylist: (_: unknown, a: { name: string; userId: number }) =>
      nullOnNotFound(async () => toPlaylist(await repo.createPlaylist(a.name, a.userId))),
    updatePlaylist: (_: unknown, a: { id: number; name?: string }) =>
      nullOnNotFound(async () => toPlaylist(await repo.updatePlaylist(a.id, a.name))),
    deletePlaylist: (_: unknown, a: { id: number }) => repo.deletePlaylist(a.id),
    addMusicToPlaylist: async (_: unknown, a: { playlistId: number; musicId: number; position?: number }) => {
      try { return await repo.addMusicToPlaylist(a.playlistId, a.musicId, a.position ?? 0); }
      catch (e) { if (e instanceof repo.NotFound) return false; throw e; }
    },
    removeMusicFromPlaylist: (_: unknown, a: { playlistId: number; musicId: number }) =>
      repo.removeMusicFromPlaylist(a.playlistId, a.musicId),
  },
};

const yoga = createYoga({ schema: createSchema({ typeDefs, resolvers }) });
const PORT = parseInt(process.env.PORT || "8012", 10);

initDb()
  .then(() => createServer(yoga).listen(PORT, () =>
    console.log(`GraphQL (TypeScript) ouvindo na porta ${PORT} (/graphql)`)))
  .catch((e) => { console.error("Falha ao iniciar:", e); process.exit(1); });
