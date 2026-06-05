-- Modelo de dados do Serviço de Streaming de Músicas
-- Três recursos centrais: usuários, músicas e playlists.
-- Relação N:N entre playlist e música via playlist_musics.

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
