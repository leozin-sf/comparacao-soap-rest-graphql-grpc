/**
 * Servidor REST em TypeScript (Express). Adaptador fino sobre repository.ts.
 * Espelha rota a rota o servidor REST em Python (rest/app.py): mesmos caminhos,
 * mesmos códigos de status (201/204/404), mesmos formatos de corpo.
 */
import express, { Request, Response, NextFunction } from "express";
import { initDb } from "../common/db.js";
import * as repo from "../common/repository.js";

const app = express();
app.use(express.json());

// Traduz NotFound -> 404; demais erros -> 500. Mantém o adaptador fino.
const wrap = (fn: (req: Request, res: Response) => Promise<void>) =>
  (req: Request, res: Response, next: NextFunction) => fn(req, res).catch(next);

const qInt = (v: unknown, def: number): number => {
  const n = parseInt(String(v ?? ""), 10);
  return Number.isFinite(n) ? n : def;
};

// ---------- health ----------
app.get("/health", wrap(async (_req, res) => {
  res.json({ status: "ok", ...(await repo.counts()) });
}));

// ---------- users ----------
app.post("/users", wrap(async (req, res) => {
  const { name, email } = req.body;
  res.status(201).json(await repo.createUser(name, email));
}));

app.get("/users", wrap(async (req, res) => {
  res.json(await repo.listUsers(qInt(req.query.limit, 100), qInt(req.query.offset, 0)));
}));

app.get("/users/:id", wrap(async (req, res) => {
  res.json(await repo.getUser(qInt(req.params.id, 0)));
}));

app.patch("/users/:id", wrap(async (req, res) => {
  const { name, email } = req.body;
  res.json(await repo.updateUser(qInt(req.params.id, 0), name, email));
}));

app.delete("/users/:id", wrap(async (req, res) => {
  if (!(await repo.deleteUser(qInt(req.params.id, 0)))) {
    res.status(404).json({ detail: "user not found" }); return;
  }
  res.status(204).end();
}));

app.get("/users/:id/playlists", wrap(async (req, res) => {
  res.json(await repo.listUserPlaylists(qInt(req.params.id, 0)));
}));

// ---------- musics ----------
app.post("/musics", wrap(async (req, res) => {
  const { title, artist, album = null, duration_seconds = 0 } = req.body;
  res.status(201).json(await repo.createMusic(title, artist, album, duration_seconds));
}));

app.get("/musics", wrap(async (req, res) => {
  res.json(await repo.listMusics(qInt(req.query.limit, 100), qInt(req.query.offset, 0)));
}));

app.get("/musics/:id", wrap(async (req, res) => {
  res.json(await repo.getMusic(qInt(req.params.id, 0)));
}));

app.patch("/musics/:id", wrap(async (req, res) => {
  const { title, artist, album, duration_seconds } = req.body;
  res.json(await repo.updateMusic(qInt(req.params.id, 0), title, artist, album, duration_seconds));
}));

app.delete("/musics/:id", wrap(async (req, res) => {
  if (!(await repo.deleteMusic(qInt(req.params.id, 0)))) {
    res.status(404).json({ detail: "music not found" }); return;
  }
  res.status(204).end();
}));

app.get("/musics/:id/playlists", wrap(async (req, res) => {
  res.json(await repo.listPlaylistsWithMusic(qInt(req.params.id, 0)));
}));

// ---------- playlists ----------
app.post("/playlists", wrap(async (req, res) => {
  const { name, user_id } = req.body;
  res.status(201).json(await repo.createPlaylist(name, user_id));
}));

app.get("/playlists", wrap(async (req, res) => {
  res.json(await repo.listPlaylists(qInt(req.query.limit, 100), qInt(req.query.offset, 0)));
}));

app.get("/playlists/:id", wrap(async (req, res) => {
  res.json(await repo.getPlaylist(qInt(req.params.id, 0)));
}));

app.patch("/playlists/:id", wrap(async (req, res) => {
  res.json(await repo.updatePlaylist(qInt(req.params.id, 0), req.body.name));
}));

app.delete("/playlists/:id", wrap(async (req, res) => {
  if (!(await repo.deletePlaylist(qInt(req.params.id, 0)))) {
    res.status(404).json({ detail: "playlist not found" }); return;
  }
  res.status(204).end();
}));

app.get("/playlists/:id/musics", wrap(async (req, res) => {
  res.json(await repo.listPlaylistMusics(qInt(req.params.id, 0)));
}));

app.put("/playlists/:id/musics/:musicId", wrap(async (req, res) => {
  await repo.addMusicToPlaylist(
    qInt(req.params.id, 0), qInt(req.params.musicId, 0), qInt(req.query.position, 0),
  );
  res.status(204).end();
}));

app.delete("/playlists/:id/musics/:musicId", wrap(async (req, res) => {
  if (!(await repo.removeMusicFromPlaylist(qInt(req.params.id, 0), qInt(req.params.musicId, 0)))) {
    res.status(404).json({ detail: "link not found" }); return;
  }
  res.status(204).end();
}));

// ---------- handler de erros (NotFound -> 404) ----------
app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  if (err instanceof repo.NotFound) {
    res.status(404).json({ detail: err.message });
  } else {
    console.error(err);
    res.status(500).json({ detail: "internal error" });
  }
});

const PORT = parseInt(process.env.PORT || "8011", 10);
initDb()
  .then(() => app.listen(PORT, "0.0.0.0",
    () => console.log(`REST (TypeScript) ouvindo na porta ${PORT}`)))
  .catch((e) => { console.error("Falha ao iniciar:", e); process.exit(1); });
