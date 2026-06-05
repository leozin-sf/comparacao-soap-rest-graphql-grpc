/**
 * Servidor SOAP 1.1 em TypeScript. Adaptador fino sobre o repositório
 * compartilhado. Reproduz fielmente o formato de fio do serviço SOAP em
 * Python (Spyne) — mesmos nomes de operação, mesmo namespace (streaming.soap),
 * mesma estrutura de resposta ({op}Response/{op}Result, itens UserT/MusicT/
 * PlaylistT) — e serve o MESMO WSDL. Assim o mesmo locustfile_soap.py exercita
 * tanto o servidor Python quanto este sem qualquer alteração.
 *
 * Optou-se por um endpoint SOAP 1.1 enxuto (sem framework SOAP pesado) para
 * manter a pilha depurável e isolar o custo do protocolo na comparação.
 */
import { fileURLToPath } from "node:url";
import { readFileSync } from "node:fs";
import express, { Request, Response } from "express";
import { initDb } from "../common/db.js";
import * as repo from "../common/repository.js";

const TNS = "streaming.soap";
const PORT = parseInt(process.env.PORT || "8013", 10);

const WSDL = readFileSync(
  fileURLToPath(new URL("../../proto/streaming.wsdl", import.meta.url)), "utf-8",
).replace(/:8000\//g, `:${PORT}/`);

// ---------- (de)serialização XML ----------
const esc = (v: unknown) =>
  String(v ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");

const ENV_OPEN =
  `<?xml version='1.0' encoding='UTF-8'?>` +
  `<soap11env:Envelope xmlns:soap11env="http://schemas.xmlsoap.org/soap/envelope/"` +
  ` xmlns:tns="${TNS}"><soap11env:Body>`;
const ENV_CLOSE = `</soap11env:Body></soap11env:Envelope>`;

const userXml = (u: repo.UserDTO) =>
  `<tns:id>${u.id}</tns:id><tns:name>${esc(u.name)}</tns:name><tns:email>${esc(u.email)}</tns:email>`;
const musicXml = (m: repo.MusicDTO) =>
  `<tns:id>${m.id}</tns:id><tns:title>${esc(m.title)}</tns:title>` +
  `<tns:artist>${esc(m.artist)}</tns:artist><tns:album>${esc(m.album ?? "")}</tns:album>` +
  `<tns:duration_seconds>${m.duration_seconds}</tns:duration_seconds>`;
const playlistXml = (p: repo.PlaylistDTO) =>
  `<tns:id>${p.id}</tns:id><tns:name>${esc(p.name)}</tns:name><tns:user_id>${p.user_id}</tns:user_id>`;

const scalar = (op: string, inner: string) =>
  ENV_OPEN + `<tns:${op}Response><tns:${op}Result>${inner}</tns:${op}Result></tns:${op}Response>` + ENV_CLOSE;
const array = (op: string, itemTag: string, items: string[]) =>
  scalar(op, items.map((i) => `<tns:${itemTag}>${i}</tns:${itemTag}>`).join(""));
const boolean = (op: string, v: boolean) => scalar(op, v ? "true" : "false");
const fault = () =>
  ENV_OPEN +
  `<soap11env:Fault><faultcode>soap11env:Server</faultcode>` +
  `<faultstring>Internal Error</faultstring><faultactor></faultactor></soap11env:Fault>` +
  ENV_CLOSE;

// Extrai a operação (1º filho do Body) e seus parâmetros escalares.
function parse(xml: string): { op: string; p: Record<string, string> } {
  const body = xml.replace(/\s+/g, " ");
  const opMatch = body.match(/<(?:\w+:)?Body[^>]*>\s*<(?:\w+:)?([A-Za-z]\w*)[ >]/);
  const op = opMatch ? opMatch[1] : "";
  const p: Record<string, string> = {};
  const re = /<(?:\w+:)?([A-Za-z]\w*)>([^<]*)<\/(?:\w+:)?\1>/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(body)) !== null) {
    if (m[1] !== op) p[m[1]] = m[2];
  }
  return { op, p };
}
const int = (v: string | undefined, d = 0) => {
  const n = parseInt(v ?? "", 10); return Number.isFinite(n) ? n : d;
};

// ---------- dispatch (espelha as operações do StreamingService Spyne) ----------
async function dispatch(op: string, p: Record<string, string>): Promise<string> {
  switch (op) {
    // users
    case "createUser": return scalar(op, userXml(await repo.createUser(p.name, p.email)));
    case "getUser":    return scalar(op, userXml(await repo.getUser(int(p.id))));
    case "listUsers":  return array(op, "UserT", (await repo.listUsers(int(p.limit, 100), int(p.offset))).map(userXml));
    case "updateUser": return scalar(op, userXml(await repo.updateUser(int(p.id), p.name, p.email)));
    case "deleteUser": return boolean(op, await repo.deleteUser(int(p.id)));
    // musics
    case "createMusic": return scalar(op, musicXml(await repo.createMusic(p.title, p.artist, p.album ?? null, int(p.duration_seconds))));
    case "getMusic":    return scalar(op, musicXml(await repo.getMusic(int(p.id))));
    case "listMusics":  return array(op, "MusicT", (await repo.listMusics(int(p.limit, 100), int(p.offset))).map(musicXml));
    case "updateMusic": return scalar(op, musicXml(await repo.updateMusic(int(p.id), p.title, p.artist, p.album, p.duration_seconds ? int(p.duration_seconds) : undefined)));
    case "deleteMusic": return boolean(op, await repo.deleteMusic(int(p.id)));
    // playlists
    case "createPlaylist": return scalar(op, playlistXml(await repo.createPlaylist(p.name, int(p.user_id))));
    case "getPlaylist":    return scalar(op, playlistXml(await repo.getPlaylist(int(p.id))));
    case "listPlaylists":  return array(op, "PlaylistT", (await repo.listPlaylists(int(p.limit, 100), int(p.offset))).map(playlistXml));
    case "updatePlaylist": return scalar(op, playlistXml(await repo.updatePlaylist(int(p.id), p.name)));
    case "deletePlaylist": return boolean(op, await repo.deletePlaylist(int(p.id)));
    // relações
    case "listUserPlaylists":      return array(op, "PlaylistT", (await repo.listUserPlaylists(int(p.user_id))).map(playlistXml));
    case "listPlaylistMusics":     return array(op, "MusicT", (await repo.listPlaylistMusics(int(p.playlist_id))).map(musicXml));
    case "listPlaylistsWithMusic": return array(op, "PlaylistT", (await repo.listPlaylistsWithMusic(int(p.music_id))).map(playlistXml));
    case "addMusicToPlaylist":     return boolean(op, await repo.addMusicToPlaylist(int(p.playlist_id), int(p.music_id), int(p.position)));
    case "removeMusicFromPlaylist": return boolean(op, await repo.removeMusicFromPlaylist(int(p.playlist_id), int(p.music_id)));
    default: throw new repo.NotFound(`operação desconhecida: ${op}`);
  }
}

const app = express();
app.use(express.text({ type: () => true, limit: "1mb" }));

app.get("/", (req: Request, res: Response) => {
  if (req.query.wsdl !== undefined || "wsdl" in req.query) {
    res.type("text/xml").send(WSDL); return;
  }
  res.type("text/xml").send(WSDL);
});

app.post("/", async (req: Request, res: Response) => {
  const { op, p } = parse(typeof req.body === "string" ? req.body : "");
  try {
    const xml = await dispatch(op, p);
    res.type("text/xml").status(200).send(xml);
  } catch (e) {
    // NotFound e demais erros viram Fault (HTTP 500), como no Spyne.
    res.type("text/xml").status(500).send(fault());
  }
});

initDb()
  .then(() => app.listen(PORT, "0.0.0.0", () =>
    console.log(`SOAP (TypeScript) na porta ${PORT} (WSDL em /?wsdl)`)))
  .catch((e) => { console.error("Falha ao iniciar:", e); process.exit(1); });
