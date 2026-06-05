/**
 * Conexão e bootstrap de schema, espelho de common/db.py (Python).
 * Usa node-postgres (pg) com a MESMA base/tabelas que os serviços Python,
 * de modo que TS e Python compartilham persistência idêntica — a única
 * variável da comparação cross-linguagem é a stack de execução.
 */
import pg from "pg";
const { Pool } = pg;

// Em Docker, DATABASE_URL aponta para o container `db`.
const connectionString =
  process.env.DATABASE_URL_TS ||
  "postgresql://app:app@localhost:5432/streaming";

// Pool dimensionado para suportar a carga do Locust (paralelo ao Python).
export const pool = new Pool({
  connectionString,
  max: 20,
});

const SCHEMA = `
CREATE TABLE IF NOT EXISTS users (
    id    SERIAL PRIMARY KEY,
    name  VARCHAR(120) NOT NULL,
    email VARCHAR(180) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS musics (
    id               SERIAL PRIMARY KEY,
    title            VARCHAR(200) NOT NULL,
    artist           VARCHAR(160) NOT NULL,
    album            VARCHAR(200),
    duration_seconds INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS playlists (
    id      SERIAL PRIMARY KEY,
    name    VARCHAR(160) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS playlist_musics (
    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    music_id    INTEGER NOT NULL REFERENCES musics(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (playlist_id, music_id)
);
CREATE INDEX IF NOT EXISTS idx_playlists_user ON playlists(user_id);
CREATE INDEX IF NOT EXISTS idx_pm_music      ON playlist_musics(music_id);
`;

export async function initDb(): Promise<void> {
  await pool.query(SCHEMA);
}
