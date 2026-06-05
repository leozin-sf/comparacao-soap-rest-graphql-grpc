/**
 * Repositório com TODA a lógica de negócio — espelho fiel de
 * common/repository.py (Python). Cada rota do server.ts é apenas um adaptador
 * fino sobre estas funções, exatamente como no lado Python. Mesma semântica de
 * NotFound, mesmas consultas do enunciado.
 */
import { pool } from "./db.js";

export class NotFound extends Error {}

export interface UserDTO { id: number; name: string; email: string; }
export interface MusicDTO {
  id: number; title: string; artist: string;
  album: string | null; duration_seconds: number;
}
export interface PlaylistDTO { id: number; name: string; user_id: number; }

// =================== USERS ===================
export async function createUser(name: string, email: string): Promise<UserDTO> {
  const r = await pool.query(
    "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id, name, email",
    [name, email],
  );
  return r.rows[0];
}

export async function getUser(id: number): Promise<UserDTO> {
  const r = await pool.query("SELECT id, name, email FROM users WHERE id = $1", [id]);
  if (r.rowCount === 0) throw new NotFound(`user ${id}`);
  return r.rows[0];
}

export async function listUsers(limit = 100, offset = 0): Promise<UserDTO[]> {
  const r = await pool.query(
    "SELECT id, name, email FROM users ORDER BY id LIMIT $1 OFFSET $2",
    [limit, offset],
  );
  return r.rows;
}

export async function updateUser(
  id: number, name?: string | null, email?: string | null,
): Promise<UserDTO> {
  const r = await pool.query(
    `UPDATE users SET
       name  = COALESCE($2, name),
       email = COALESCE($3, email)
     WHERE id = $1
     RETURNING id, name, email`,
    [id, name ?? null, email ?? null],
  );
  if (r.rowCount === 0) throw new NotFound(`user ${id}`);
  return r.rows[0];
}

export async function deleteUser(id: number): Promise<boolean> {
  const r = await pool.query("DELETE FROM users WHERE id = $1", [id]);
  return (r.rowCount ?? 0) > 0;
}

// =================== MUSICS ===================
export async function createMusic(
  title: string, artist: string, album: string | null, durationSeconds = 0,
): Promise<MusicDTO> {
  const r = await pool.query(
    `INSERT INTO musics (title, artist, album, duration_seconds)
     VALUES ($1, $2, $3, $4)
     RETURNING id, title, artist, album, duration_seconds`,
    [title, artist, album, durationSeconds],
  );
  return r.rows[0];
}

export async function getMusic(id: number): Promise<MusicDTO> {
  const r = await pool.query(
    "SELECT id, title, artist, album, duration_seconds FROM musics WHERE id = $1", [id],
  );
  if (r.rowCount === 0) throw new NotFound(`music ${id}`);
  return r.rows[0];
}

export async function listMusics(limit = 100, offset = 0): Promise<MusicDTO[]> {
  const r = await pool.query(
    `SELECT id, title, artist, album, duration_seconds
     FROM musics ORDER BY id LIMIT $1 OFFSET $2`,
    [limit, offset],
  );
  return r.rows;
}

export async function updateMusic(
  id: number, title?: string | null, artist?: string | null,
  album?: string | null, durationSeconds?: number | null,
): Promise<MusicDTO> {
  const r = await pool.query(
    `UPDATE musics SET
       title            = COALESCE($2, title),
       artist           = COALESCE($3, artist),
       album            = COALESCE($4, album),
       duration_seconds = COALESCE($5, duration_seconds)
     WHERE id = $1
     RETURNING id, title, artist, album, duration_seconds`,
    [id, title ?? null, artist ?? null, album ?? null, durationSeconds ?? null],
  );
  if (r.rowCount === 0) throw new NotFound(`music ${id}`);
  return r.rows[0];
}

export async function deleteMusic(id: number): Promise<boolean> {
  const r = await pool.query("DELETE FROM musics WHERE id = $1", [id]);
  return (r.rowCount ?? 0) > 0;
}

// =================== PLAYLISTS ===================
export async function createPlaylist(name: string, userId: number): Promise<PlaylistDTO> {
  const u = await pool.query("SELECT 1 FROM users WHERE id = $1", [userId]);
  if (u.rowCount === 0) throw new NotFound(`user ${userId}`);
  const r = await pool.query(
    "INSERT INTO playlists (name, user_id) VALUES ($1, $2) RETURNING id, name, user_id",
    [name, userId],
  );
  return r.rows[0];
}

export async function getPlaylist(id: number): Promise<PlaylistDTO> {
  const r = await pool.query("SELECT id, name, user_id FROM playlists WHERE id = $1", [id]);
  if (r.rowCount === 0) throw new NotFound(`playlist ${id}`);
  return r.rows[0];
}

export async function listPlaylists(limit = 100, offset = 0): Promise<PlaylistDTO[]> {
  const r = await pool.query(
    "SELECT id, name, user_id FROM playlists ORDER BY id LIMIT $1 OFFSET $2",
    [limit, offset],
  );
  return r.rows;
}

export async function updatePlaylist(id: number, name?: string | null): Promise<PlaylistDTO> {
  const r = await pool.query(
    `UPDATE playlists SET name = COALESCE($2, name)
     WHERE id = $1 RETURNING id, name, user_id`,
    [id, name ?? null],
  );
  if (r.rowCount === 0) throw new NotFound(`playlist ${id}`);
  return r.rows[0];
}

export async function deletePlaylist(id: number): Promise<boolean> {
  const r = await pool.query("DELETE FROM playlists WHERE id = $1", [id]);
  return (r.rowCount ?? 0) > 0;
}

// =========== CONSULTAS DO ENUNCIADO (relações) ===========
/** Todas as playlists de um determinado usuário. */
export async function listUserPlaylists(userId: number): Promise<PlaylistDTO[]> {
  const r = await pool.query(
    "SELECT id, name, user_id FROM playlists WHERE user_id = $1 ORDER BY id",
    [userId],
  );
  return r.rows;
}

/** Todas as músicas de uma determinada playlist (ordenadas por posição). */
export async function listPlaylistMusics(playlistId: number): Promise<MusicDTO[]> {
  const r = await pool.query(
    `SELECT m.id, m.title, m.artist, m.album, m.duration_seconds
     FROM musics m
     JOIN playlist_musics pm ON pm.music_id = m.id
     WHERE pm.playlist_id = $1
     ORDER BY pm.position`,
    [playlistId],
  );
  return r.rows;
}

/** Todas as playlists que contêm uma determinada música. */
export async function listPlaylistsWithMusic(musicId: number): Promise<PlaylistDTO[]> {
  const r = await pool.query(
    `SELECT p.id, p.name, p.user_id
     FROM playlists p
     JOIN playlist_musics pm ON pm.playlist_id = p.id
     WHERE pm.music_id = $1
     ORDER BY p.id`,
    [musicId],
  );
  return r.rows;
}

export async function addMusicToPlaylist(
  playlistId: number, musicId: number, position = 0,
): Promise<boolean> {
  const p = await pool.query("SELECT 1 FROM playlists WHERE id = $1", [playlistId]);
  if (p.rowCount === 0) throw new NotFound(`playlist ${playlistId}`);
  const m = await pool.query("SELECT 1 FROM musics WHERE id = $1", [musicId]);
  if (m.rowCount === 0) throw new NotFound(`music ${musicId}`);
  await pool.query(
    `INSERT INTO playlist_musics (playlist_id, music_id, position)
     VALUES ($1, $2, $3)
     ON CONFLICT (playlist_id, music_id) DO NOTHING`,
    [playlistId, musicId, position],
  );
  return true;
}

export async function removeMusicFromPlaylist(
  playlistId: number, musicId: number,
): Promise<boolean> {
  const r = await pool.query(
    "DELETE FROM playlist_musics WHERE playlist_id = $1 AND music_id = $2",
    [playlistId, musicId],
  );
  return (r.rowCount ?? 0) > 0;
}

export async function counts(): Promise<{ users: number; musics: number; playlists: number; }> {
  const r = await pool.query(
    `SELECT
       (SELECT COUNT(*) FROM users)     AS users,
       (SELECT COUNT(*) FROM musics)    AS musics,
       (SELECT COUNT(*) FROM playlists) AS playlists`,
  );
  const row = r.rows[0];
  return {
    users: Number(row.users),
    musics: Number(row.musics),
    playlists: Number(row.playlists),
  };
}
