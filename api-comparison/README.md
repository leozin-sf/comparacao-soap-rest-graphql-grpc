# Comparação de Tecnologias de API — SOAP × REST × GraphQL × gRPC

# ATUALIZAÇÃO IMPORTANTE: GRÁFICOS E RESPOSTAS DAS APIS AJUSTADOS

> **Eu ajustei os gráficos e as respostas das APIs.**
>
> - Corrigi os gráficos para utilizarem escala linear iniciada em zero.
> - Corrigi e conferi os tamanhos das respostas retornadas pelas APIs.
> - Validei que REST, GraphQL, SOAP e gRPC consultam as APIs e o PostgreSQL
>   corretamente, sem respostas fabricadas pelo script Bash.
> - Confirmei a equivalência dos dados retornados em Python e TypeScript,
>   considerando as diferenças de serialização de JSON, XML e Protobuf.
> - Executei novamente os benchmarks e regenerei os relatórios e gráficos.

Prova de conceito (PoC) para a disciplina de **Computação Distribuída**
(Prof. Nabor C. Mendonça). O objetivo é comparar, de forma **justa e
mensurável**, quatro tecnologias de comunicação de APIs — **SOAP, REST,
GraphQL e gRPC** — usando um mesmo domínio de aplicação: um **serviço de
streaming de músicas**.

## Domínio (conforme os slides do trabalho)

Três recursos centrais e uma relação N:N:

- **Usuários** (`users`)
- **Músicas** (`musics`) — com `title`, `artist`, `album`, `duration_seconds`
- **Playlists** (`playlists`) — pertencem a um usuário
- **playlist_musics** — relação N:N entre playlist e música (com `position`)

Consultas exigidas pelo enunciado (todas implementadas em **todos** os
protocolos):

1. Listar usuários
2. Listar músicas
3. Listar as playlists de um usuário
4. Listar as músicas de uma playlist
5. Listar as playlists que contêm uma determinada música

Além disso, há **CRUD completo** dos três recursos e operações de
adicionar/remover música em playlist.

## A ideia central: comparação justa

A única variável que queremos medir é a **tecnologia de comunicação**. Por
isso, em cada linguagem, **toda a lógica de negócio e o acesso a dados ficam
concentrados em uma única camada compartilhada**, e cada servidor (SOAP/REST/
GraphQL/gRPC) é apenas um **adaptador fino** sobre ela:

- **Python:** `python/common/repository.py` concentra CRUD + as 5 consultas.
  Os quatro servidores apenas traduzem o protocolo ↔ chamadas do repositório.
  Persistência única em `python/common/db.py` (SQLAlchemy + PostgreSQL).
- **TypeScript:** `typescript/src/common/repository.ts` espelha exatamente o
  repositório Python, sobre o mesmo PostgreSQL. Os quatro servidores TS
  (`src/rest`, `src/graphql`, `src/soap`, `src/grpc`) são adaptadores finos
  sobre ele — mesma estratégia do lado Python.

Todos os serviços apontam para o **mesmo banco PostgreSQL** e a **mesma massa
de dados** (seed), de modo que diferenças de desempenho refletem o protocolo,
não a regra de negócio nem o esquema.

## Escopo desta entrega

| Protocolo | Python | TypeScript |
|-----------|:------:|:----------:|
| REST      |   ✅   |     ✅     |
| GraphQL   |   ✅   |     ✅     |
| SOAP      |   ✅   |     ✅     |
| gRPC      |   ✅   |     ✅     |

**Os 8 serviços estão implementados** (4 protocolos × 2 linguagens), todos
testados de ponta a ponta contra o PostgreSQL. A paridade de contrato é
estrita: por exemplo, um cliente gRPC gerado a partir do mesmo `.proto`
conversa indistintamente com o servidor gRPC Python e com o TypeScript; e o
servidor SOAP TS reproduz o mesmo formato de envelope/WSDL do Spyne, de modo
que o mesmo `locustfile_soap.py` exercita ambos.

> Nota sobre o SOAP em TypeScript: optou-se por um endpoint SOAP 1.1 enxuto
> (tratamento de envelope próprio, servindo o **mesmo WSDL** do serviço Python)
> em vez de um framework SOAP pesado, para manter a pilha depurável e o
> contrato idêntico ao do Spyne.

## Estrutura do projeto

```
api-comparison/
├── docker-compose.yml          # Postgres + 8 serviços + job de seed
├── run_benchmarks.sh           # roda Locust (250/800 usuários) -> reports/
├── generate_latency_charts.py  # gera comparativos de média e P95
├── shared/schema.sql           # esquema de referência (DDL)
├── python/
│   ├── Dockerfile              # imagem única p/ os 4 serviços Python + seed
│   ├── requirements.txt
│   ├── common/                 # db.py, repository.py, seed.py  (compartilhado)
│   ├── rest/app.py             # FastAPI            (porta 8001)
│   ├── graphql_api/app.py      # Strawberry+FastAPI (porta 8002, /graphql)
│   ├── soap/server.py          # Spyne, SOAP 1.1    (porta 8000, /?wsdl)
│   └── grpc_api/               # gRPC + .proto      (porta 50051)
├── typescript/                 # imagem única p/ os 4 serviços TypeScript
│   ├── Dockerfile
│   ├── proto/                  # streaming.proto (gRPC) + streaming.wsdl (SOAP)
│   └── src/
│       ├── common/             # db.ts, repository.ts  (compartilhado)
│       ├── rest/server.ts      # Express                (porta 8011)
│       ├── graphql/server.ts   # graphql-yoga           (porta 8012, /graphql)
│       ├── soap/server.ts      # SOAP 1.1               (porta 8013, /?wsdl)
│       └── grpc/server.ts      # @grpc/grpc-js          (porta 50052)
└── load-tests/                 # locustfiles dos 4 protocolos + bench.sh
```

## Pré-requisitos

- **Docker** e **Docker Compose** (caminho recomendado — sobe tudo).
- Para rodar os testes de carga a partir do host: **Python 3.10+** e
  `pip install -r load-tests/requirements.txt`.

## Como executar (Docker — recomendado)

```bash
# 1) sobe Postgres + os 8 serviços
docker compose up -d --build

# 2) popula a base (400 usuários, 4000 músicas, 600 playlists)
docker compose run --rm seed

# 3) confira que está tudo no ar (Python e TypeScript)
curl http://localhost:8001/health          # REST (Python)
curl http://localhost:8011/health          # REST (TypeScript)
curl -X POST http://localhost:8002/graphql -H 'Content-Type: application/json' \
     -d '{"query":"{ users(limit:1){ id name } }"}'   # GraphQL (Python)
curl -X POST http://localhost:8012/graphql -H 'Content-Type: application/json' \
     -d '{"query":"{ users(limit:1){ id name } }"}'   # GraphQL (TypeScript)
curl "http://localhost:8000/?wsdl" | head   # SOAP (Python)
curl "http://localhost:8013/?wsdl" | head   # SOAP (TypeScript)
# gRPC: portas 50051 (Python) e 50052 (TypeScript) — teste via Locust/cliente
```

Portas:

| Serviço            | Porta | Endpoint                          |
|--------------------|:-----:|-----------------------------------|
| REST (Python)      | 8001  | `http://localhost:8001`           |
| GraphQL (Python)   | 8002  | `http://localhost:8002/graphql`   |
| SOAP (Python)      | 8000  | `http://localhost:8000/?wsdl`     |
| gRPC (Python)      | 50051 | `localhost:50051`                 |
| REST (TypeScript)  | 8011  | `http://localhost:8011`           |
| GraphQL (TypeScript)| 8012 | `http://localhost:8012/graphql`   |
| SOAP (TypeScript)  | 8013  | `http://localhost:8013/?wsdl`     |
| gRPC (TypeScript)  | 50052 | `localhost:50052`                 |

## Consultas rápidas no terminal

Todos os comandos desta seção devem ser executados no diretório
`api-comparison`. Se o seu prompt já mostra `api-comparison`, você já está no
local correto.

```bash
cd api-comparison
```

Confira se os contêineres estão ativos:

```bash
docker compose ps
```

Se ainda não estiverem ativos:

```bash
docker compose up -d --build
```

O arquivo `consultar_api.sh` executa as consultas sem exigir que você cole
JSON, XML ou envelopes SOAP grandes no terminal.

O script não acessa o PostgreSQL. O caminho é sempre
`consultar_api.sh -> porta HTTP/gRPC -> serviço -> repositório -> PostgreSQL`.
Nos casos REST e GraphQL, `python3 -m json.tool` apenas indenta o JSON que a
API já retornou. No gRPC, o `grpcurl` apenas representa a mensagem Protobuf
como JSON no terminal. Por isso, a saída formatada desse script não deve ser
usada para medir o tamanho bruto do corpo; use `audit_response_sizes.py` ou a
coluna `Average Content Size` dos relatórios Locust.

### Listar os três recursos em todas as APIs

Serviços Python:

```bash
./consultar_api.sh all users python
./consultar_api.sh all musics python
./consultar_api.sh all playlists python
```

Serviços TypeScript:

```bash
./consultar_api.sh all users typescript
./consultar_api.sh all musics typescript
./consultar_api.sh all playlists typescript
```

Cada comando consulta REST, GraphQL, SOAP e gRPC, nessa ordem.

Por padrão, o script mostra apenas cinco registros. Para solicitar até 800:

```bash
LIMIT=800 ./consultar_api.sh all users python
LIMIT=800 ./consultar_api.sh all users typescript
```

O `LIMIT` é a quantidade máxima retornada, não a quantidade criada no banco.

### Consultar uma API específica

```bash
./consultar_api.sh rest users python
./consultar_api.sh graphql musics python
./consultar_api.sh soap playlists python
./consultar_api.sh grpc users python
```

Para consultar TypeScript, troque apenas `python` por `typescript`:

```bash
./consultar_api.sh rest users typescript
./consultar_api.sh graphql musics typescript
./consultar_api.sh soap playlists typescript
./consultar_api.sh grpc users typescript
```

### Consultar um registro pelo ID

Acrescente o ID no final do comando:

```bash
./consultar_api.sh rest users python 1
./consultar_api.sh graphql musics python 1
./consultar_api.sh soap playlists python 1
./consultar_api.sh grpc users python 1
```

### Onde aparece a resposta

A resposta aparece no mesmo terminal, logo abaixo do comando:

- REST e GraphQL: JSON;
- SOAP: XML;
- gRPC: conteúdo Protobuf convertido para JSON pelo `grpcurl`.

Para salvar a resposta em um arquivo:

```bash
./consultar_api.sh rest users python > resposta.json
./consultar_api.sh soap users python > resposta.xml
```

Todos os serviços consultam o mesmo PostgreSQL. Por isso, os mesmos usuários,
músicas e playlists aparecem nas implementações Python e TypeScript e nos
quatro protocolos.

Na primeira consulta gRPC, o Docker pode baixar a imagem
`fullstorydev/grpcurl`. Isso acontece apenas se ela ainda não estiver no
computador.

## Referência detalhada de requisições

### 1. Subir e conferir os contêineres

```bash
# Sobe o PostgreSQL e as oito APIs
docker compose up -d --build

# Popula o banco, caso ainda não tenha executado o seed
docker compose run --rm seed

# Mostra o estado dos contêineres
docker compose ps
```

Todas as APIs usam o **mesmo banco PostgreSQL**. Um usuário criado pela API
REST pode ser consultado por GraphQL, SOAP ou gRPC.

Os exemplos abaixo usam os serviços Python. Para testar TypeScript, altere
somente a porta:

| Protocolo | Python | TypeScript |
|-----------|-------:|-----------:|
| REST      | 8001   | 8011       |
| GraphQL   | 8002   | 8012       |
| SOAP      | 8000   | 8013       |
| gRPC      | 50051  | 50052      |

Formatos nativos das respostas:

- REST: JSON;
- GraphQL: JSON;
- SOAP: XML;
- gRPC: Protobuf (o `grpcurl` exibe esse conteúdo como JSON no terminal).

### 2. Consultar diretamente o PostgreSQL

> Diagnóstico manual apenas. Nenhum benchmark ou gráfico usa `psql`, XML
> gerado no banco ou saída de Bash como resposta de API. Os Locustfiles
> chamam exclusivamente as portas HTTP/gRPC dos serviços.

Abrir o console SQL:

```bash
docker compose exec db psql -U app -d streaming
```

Dentro do `psql`, alguns exemplos são:

```sql
SELECT id, name, email
FROM users
ORDER BY id
LIMIT 10;

SELECT id, title, artist
FROM musics
ORDER BY id
LIMIT 10;

SELECT id, name, user_id
FROM playlists
ORDER BY id
LIMIT 10;
```

Para sair do `psql`:

```text
\q
```

Também é possível executar SQL sem abrir o console:

```bash
docker compose exec -T db psql -U app -d streaming \
  -c "SELECT id, name, email FROM users ORDER BY id LIMIT 5;"
```

Gerar XML diretamente pelo PostgreSQL:

```bash
docker compose exec -T db psql -U app -d streaming -t -A \
  -c "SELECT xmlelement(
        name users,
        xmlagg(
          xmlelement(
            name user,
            xmlelement(name id, id),
            xmlelement(name name, name),
            xmlelement(name email, email)
          )
        )
      )
      FROM (
        SELECT id, name, email
        FROM users
        ORDER BY id
        LIMIT 5
      ) AS selected_users;"
```

Essa saída XML é gerada pelo PostgreSQL. Para testar o protocolo SOAP e
receber um envelope SOAP, use os comandos da seção SOAP.

### 3. REST

Defina a URL da implementação desejada:

```bash
# Python
REST_URL="http://localhost:8001"

# Para usar TypeScript:
# REST_URL="http://localhost:8011"
```

Listar e consultar usuários:

```bash
curl -sS "$REST_URL/users?limit=5&offset=0"

USER_ID=1
curl -sS "$REST_URL/users/$USER_ID"
```

Criar, atualizar e excluir um usuário:

```bash
EMAIL="rest-$(date +%s)@example.com"

curl -sS -X POST "$REST_URL/users" \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"Usuário REST\",\"email\":\"$EMAIL\"}"

# Substitua pelo id retornado na criação
USER_ID=1

curl -sS -X PATCH "$REST_URL/users/$USER_ID" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Usuário REST atualizado"}'

curl -i -X DELETE "$REST_URL/users/$USER_ID"
```

Criar música e playlist:

```bash
curl -sS -X POST "$REST_URL/musics" \
  -H 'Content-Type: application/json' \
  -d '{
    "title":"Música de teste",
    "artist":"Artista de teste",
    "album":"Álbum de teste",
    "duration_seconds":180
  }'

curl -sS -X POST "$REST_URL/playlists" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Playlist de teste","user_id":1}'
```

Consultar e alterar relacionamentos:

```bash
USER_ID=1
PLAYLIST_ID=1
MUSIC_ID=1

# Playlists do usuário
curl -sS "$REST_URL/users/$USER_ID/playlists"

# Músicas da playlist
curl -sS "$REST_URL/playlists/$PLAYLIST_ID/musics"

# Playlists que contêm a música
curl -sS "$REST_URL/musics/$MUSIC_ID/playlists"

# Adiciona a música à playlist. Sucesso retorna HTTP 204 sem corpo.
curl -i -X PUT \
  "$REST_URL/playlists/$PLAYLIST_ID/musics/$MUSIC_ID?position=0"

# Remove a música da playlist
curl -i -X DELETE \
  "$REST_URL/playlists/$PLAYLIST_ID/musics/$MUSIC_ID"
```

### 4. GraphQL

Defina o endpoint:

```bash
# Python
GRAPHQL_URL="http://localhost:8002/graphql"

# Para usar TypeScript:
# GRAPHQL_URL="http://localhost:8012/graphql"
```

Listar usuários, músicas e playlists:

```bash
curl -sS -X POST "$GRAPHQL_URL" \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ users(limit: 5) { id name email } musics(limit: 5) { id title artist album durationSeconds } playlists(limit: 5) { id name userId } }"}'
```

Consultar um usuário:

```bash
curl -sS -X POST "$GRAPHQL_URL" \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ user(id: 1) { id name email } }"}'
```

Criar, atualizar e excluir um usuário:

```bash
EMAIL="graphql-$(date +%s)@example.com"

curl -sS -X POST "$GRAPHQL_URL" \
  -H 'Content-Type: application/json' \
  -d "{\"query\":\"mutation { createUser(name: \\\"Usuário GraphQL\\\", email: \\\"$EMAIL\\\") { id name email } }\"}"

# Substitua pelo id retornado na criação
USER_ID=1

curl -sS -X POST "$GRAPHQL_URL" \
  -H 'Content-Type: application/json' \
  -d "{\"query\":\"mutation { updateUser(id: $USER_ID, name: \\\"Usuário atualizado\\\") { id name email } }\"}"

curl -sS -X POST "$GRAPHQL_URL" \
  -H 'Content-Type: application/json' \
  -d "{\"query\":\"mutation { deleteUser(id: $USER_ID) }\"}"
```

Criar música e playlist:

```bash
curl -sS -X POST "$GRAPHQL_URL" \
  -H 'Content-Type: application/json' \
  -d '{"query":"mutation { createMusic(title: \"Música GraphQL\", artist: \"Artista de teste\", album: \"Álbum de teste\", durationSeconds: 180) { id title artist } }"}'

curl -sS -X POST "$GRAPHQL_URL" \
  -H 'Content-Type: application/json' \
  -d '{"query":"mutation { createPlaylist(name: \"Playlist GraphQL\", userId: 1) { id name userId } }"}'
```

Consultar e alterar relacionamentos:

```bash
curl -sS -X POST "$GRAPHQL_URL" \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ userPlaylists(userId: 1) { id name userId } playlistMusics(playlistId: 1) { id title artist } playlistsWithMusic(musicId: 1) { id name userId } }"}'

curl -sS -X POST "$GRAPHQL_URL" \
  -H 'Content-Type: application/json' \
  -d '{"query":"mutation { addMusicToPlaylist(playlistId: 1, musicId: 1, position: 0) }"}'

curl -sS -X POST "$GRAPHQL_URL" \
  -H 'Content-Type: application/json' \
  -d '{"query":"mutation { removeMusicFromPlaylist(playlistId: 1, musicId: 1) }"}'
```

Também é possível abrir o GraphiQL no navegador:

- Python: `http://localhost:8002/graphql`
- TypeScript: `http://localhost:8012/graphql`

### 5. SOAP

Crie esta função no terminal. Ela monta o envelope SOAP automaticamente:

```bash
soap_call() {
  local port="$1"
  local body="$2"

  curl -sS -X POST "http://localhost:${port}/" \
    -H 'Content-Type: text/xml; charset=utf-8' \
    -H 'SOAPAction: ""' \
    --data-binary "<?xml version=\"1.0\"?>
<soapenv:Envelope
 xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\"
 xmlns:tns=\"streaming.soap\">
 <soapenv:Body>${body}</soapenv:Body>
</soapenv:Envelope>"
}
```

Use a porta `8000` para Python ou `8013` para TypeScript:

```bash
SOAP_PORT=8000
# SOAP_PORT=8013
```

Listar e consultar usuários:

```bash
soap_call "$SOAP_PORT" \
  '<tns:listUsers>
    <tns:limit>5</tns:limit>
    <tns:offset>0</tns:offset>
  </tns:listUsers>'

soap_call "$SOAP_PORT" \
  '<tns:getUser><tns:id>1</tns:id></tns:getUser>'
```

Criar, atualizar e excluir um usuário:

```bash
EMAIL="soap-$(date +%s)@example.com"

soap_call "$SOAP_PORT" \
  "<tns:createUser>
    <tns:name>Usuário SOAP</tns:name>
    <tns:email>${EMAIL}</tns:email>
  </tns:createUser>"

# Substitua pelo id retornado na criação
USER_ID=1

soap_call "$SOAP_PORT" \
  "<tns:updateUser>
    <tns:id>${USER_ID}</tns:id>
    <tns:name>Usuário SOAP atualizado</tns:name>
  </tns:updateUser>"

soap_call "$SOAP_PORT" \
  "<tns:deleteUser><tns:id>${USER_ID}</tns:id></tns:deleteUser>"
```

Criar música e playlist:

```bash
soap_call "$SOAP_PORT" \
  '<tns:createMusic>
    <tns:title>Música SOAP</tns:title>
    <tns:artist>Artista de teste</tns:artist>
    <tns:album>Álbum de teste</tns:album>
    <tns:duration_seconds>180</tns:duration_seconds>
  </tns:createMusic>'

soap_call "$SOAP_PORT" \
  '<tns:createPlaylist>
    <tns:name>Playlist SOAP</tns:name>
    <tns:user_id>1</tns:user_id>
  </tns:createPlaylist>'
```

Consultar e alterar relacionamentos:

```bash
soap_call "$SOAP_PORT" \
  '<tns:listUserPlaylists>
    <tns:user_id>1</tns:user_id>
  </tns:listUserPlaylists>'

soap_call "$SOAP_PORT" \
  '<tns:listPlaylistMusics>
    <tns:playlist_id>1</tns:playlist_id>
  </tns:listPlaylistMusics>'

soap_call "$SOAP_PORT" \
  '<tns:listPlaylistsWithMusic>
    <tns:music_id>1</tns:music_id>
  </tns:listPlaylistsWithMusic>'

soap_call "$SOAP_PORT" \
  '<tns:addMusicToPlaylist>
    <tns:playlist_id>1</tns:playlist_id>
    <tns:music_id>1</tns:music_id>
    <tns:position>0</tns:position>
  </tns:addMusicToPlaylist>'

soap_call "$SOAP_PORT" \
  '<tns:removeMusicFromPlaylist>
    <tns:playlist_id>1</tns:playlist_id>
    <tns:music_id>1</tns:music_id>
  </tns:removeMusicFromPlaylist>'
```

Consultar o contrato WSDL:

```bash
curl -sS "http://localhost:${SOAP_PORT}/?wsdl"
```

### 6. gRPC

Os comandos abaixo executam o `grpcurl` em um contêiner. Na primeira
execução, o Docker baixa a imagem `fullstorydev/grpcurl`.

Crie esta função no terminal:

```bash
grpc_call() {
  local port="$1"
  local method="$2"
  local data="$3"

  docker run --rm --network host \
    -v "$PWD/python/grpc_api:/protos:ro" \
    fullstorydev/grpcurl:latest \
    -plaintext \
    -import-path /protos \
    -proto streaming.proto \
    -d "$data" \
    "localhost:${port}" \
    "streaming.StreamingService/${method}"
}
```

Use a porta `50051` para Python ou `50052` para TypeScript:

```bash
GRPC_PORT=50051
# GRPC_PORT=50052
```

Listar e consultar usuários:

```bash
grpc_call "$GRPC_PORT" ListUsers '{"limit":5,"offset":0}'
grpc_call "$GRPC_PORT" GetUser '{"id":1}'
```

Criar, atualizar e excluir um usuário:

```bash
EMAIL="grpc-$(date +%s)@example.com"

grpc_call "$GRPC_PORT" CreateUser \
  "{\"name\":\"Usuário gRPC\",\"email\":\"$EMAIL\"}"

# Substitua pelo id retornado na criação
USER_ID=1

grpc_call "$GRPC_PORT" UpdateUser \
  "{\"id\":$USER_ID,\"name\":\"Usuário gRPC atualizado\"}"

grpc_call "$GRPC_PORT" DeleteUser "{\"id\":$USER_ID}"
```

Criar música e playlist:

```bash
grpc_call "$GRPC_PORT" CreateMusic \
  '{
    "title":"Música gRPC",
    "artist":"Artista de teste",
    "album":"Álbum de teste",
    "duration_seconds":180
  }'

grpc_call "$GRPC_PORT" CreatePlaylist \
  '{"name":"Playlist gRPC","user_id":1}'
```

Consultar e alterar relacionamentos:

```bash
grpc_call "$GRPC_PORT" ListUserPlaylists '{"id":1}'
grpc_call "$GRPC_PORT" ListPlaylistMusics '{"id":1}'
grpc_call "$GRPC_PORT" ListPlaylistsWithMusic '{"id":1}'

grpc_call "$GRPC_PORT" AddMusicToPlaylist \
  '{"playlist_id":1,"music_id":1,"position":0}'

grpc_call "$GRPC_PORT" RemoveMusicFromPlaylist \
  '{"playlist_id":1,"music_id":1}'
```

### 7. Conferir dados criados por outra API

Por exemplo, depois de criar um usuário por REST, localize-o no banco:

```bash
docker compose exec -T db psql -U app -d streaming \
  -c "SELECT id, name, email
      FROM users
      WHERE email LIKE 'rest-%@example.com'
      ORDER BY id DESC
      LIMIT 5;"
```

Depois use o `id` retornado para consultar o mesmo usuário em outro
protocolo:

```bash
# GraphQL
curl -sS -X POST http://localhost:8002/graphql \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ user(id: 1) { id name email } }"}'

# SOAP
SOAP_PORT=8000
soap_call "$SOAP_PORT" \
  '<tns:getUser><tns:id>1</tns:id></tns:getUser>'

# gRPC
GRPC_PORT=50051
grpc_call "$GRPC_PORT" GetUser '{"id":1}'
```

Substitua o `1` pelo identificador encontrado no banco.

### 8. Diagnóstico

Verificar os serviços:

```bash
docker compose ps
curl -sS http://localhost:8001/health
curl -sS http://localhost:8011/health
```

Ver logs:

```bash
docker compose logs --tail=100 rest
docker compose logs --tail=100 graphql
docker compose logs --tail=100 soap
docker compose logs --tail=100 grpc
```

Para os serviços TypeScript, use `rest_ts`, `graphql_ts`, `soap_ts` ou
`grpc_ts`.

Erros comuns:

- `connection refused`: o contêiner não está ativo ou a porta está errada;
- erro de e-mail duplicado: use outro e-mail ou mantenha `$(date +%s)` no
  comando;
- `404`, `NOT_FOUND` ou SOAP Fault: o identificador informado não existe;
- respostas HTTP `204` não possuem corpo e indicam sucesso;
- REST e GraphQL não retornam XML nativamente. XML é a resposta do SOAP ou
  pode ser construído diretamente em SQL pelo PostgreSQL.

Para parar: `docker compose down` (ou `down -v` para apagar também o volume
do banco).

## Como executar (local, sem Docker)

Precisa de um PostgreSQL acessível e da variável `DATABASE_URL`
(Python) / `DATABASE_URL_TS` (TypeScript). Exemplo para Python:

```bash
cd python
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg2://app:app@localhost:5432/streaming"
export PYTHONPATH="$PWD"
python -m common.seed                                  # popula a base

cd rest        && uvicorn app:app --port 8001          # REST
cd graphql_api && uvicorn app:app --port 8002          # GraphQL
cd soap        && PORT=8000 python server.py            # SOAP
cd grpc_api    && PORT=50051 python server.py           # gRPC
```

TypeScript (um único pacote, quatro pontos de entrada):

```bash
cd typescript
npm install
npm run build
export DATABASE_URL_TS="postgresql://app:app@localhost:5432/streaming"
PORT=8011 npm run start:rest        # REST
PORT=8012 npm run start:graphql     # GraphQL
PORT=8013 npm run start:soap        # SOAP
PORT=50052 npm run start:grpc       # gRPC
```

> **Nota sobre o gRPC (Python 3.12):** os stubs `streaming_pb2*.py` são
> gerados a partir de `grpc_api/streaming.proto`. No Docker isso é feito
> automaticamente no build. Localmente, regenere com:
> ```bash
> cd python/grpc_api
> python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. streaming.proto
> ```
> Os mesmos stubs já estão copiados em `load-tests/` para o cliente Locust.
> O servidor gRPC em TypeScript carrega o `.proto` em tempo de execução
> (não precisa gerar stubs).

## Testes de carga e coleta de métricas

Os testes usam **Locust**. O `run_benchmarks.sh` executa o CRUD completo de
`users`, `musics` e `playlists`: listagem, consulta por ID, criação,
atualização e exclusão.

### Rodando a bateria completa

Com os serviços no ar e as dependências instaladas no host:

```bash
pip install -r load-tests/requirements.txt
./run_benchmarks.sh                       # 250 e 800 usuários, 60s cada
# ou personalize:
USERS="50 200 500" DURATION=120 ./run_benchmarks.sh
```

São 15 cenários por serviço, distribuídos entre os usuários virtuais. Por
isso, cada nível configurado em `USERS` deve ter pelo menos 15 usuários.

Isso gera, em `reports/`, para cada serviço e nível de carga:

- `<serviço>_<N>u_stats.csv` — **RPS, latências, P50…P100, falhas** (use a
  linha `Aggregated`) e `Average Content Size` em bytes;
- `<serviço>_<N>u_stats_history.csv` — série temporal;
- `<serviço>_<N>u.html` — dashboard visual (bom para anexar ao relatório).

Cada arquivo `_stats.csv` contém uma linha por operação CRUD e a linha
`Aggregated`. Em GraphQL e SOAP, a coluna `Type` aparece como `POST` porque
esse é o transporte HTTP dos dois protocolos; a ação efetiva (`updateUser`,
`deleteMusic`, etc.) aparece na coluna `Name`. Em gRPC, `Name` contém o método
RPC.

As criações usadas para preparar um `DELETE` e as exclusões usadas para
limpar um `CREATE` também passam pela API. Essas chamadas usam o cliente
instrumentado do Locust e são contabilizadas nas mesmas linhas `create*` e
`delete*`; portanto, não há tráfego oculto consumindo API ou banco fora das
estatísticas.

### Auditando respostas e tamanhos diretamente

Com os oito serviços ativos, execute:

```bash
.venv/bin/python audit_response_sizes.py
```

O script consulta `users`, `musics` e `playlists` nas oito APIs, normaliza
JSON, XML e Protobuf, compara todos os registros com o REST Python e grava
`reports/response_sizes.csv`. A coluna `body_bytes` mede o corpo HTTP em
REST/GraphQL/SOAP e o `ByteSize` da mensagem Protobuf em gRPC, da mesma forma
que o cliente de carga.

Respostas Python e TypeScript devem conter os mesmos dados porque usam o
mesmo PostgreSQL. Os tamanhos podem diferir por causa do envelope do
protocolo e do serializador de cada framework.

### Gerando os gráficos comparativos

Depois que todos os testes terminarem, execute na raiz do projeto:

```bash
python3 generate_latency_charts.py
```

O script detecta automaticamente os níveis de carga presentes em `reports/`
e cria gráficos de **latência média**, **P95** e **tamanho médio da resposta**
em `reports/charts/`. Além dos resultados agregados do CRUD completo, são
gerados comparativos para `get`, `post` (criação), `update` e `delete`:

- `<metrica>_same_api_<api>.svg` — compara Python e TypeScript para a mesma
  API ao longo das cargas, considerando o CRUD completo;
- `<metrica>_all_apis_<N>u.svg` — compara todas as APIs e linguagens na mesma
  carga, considerando o CRUD completo;
- `<metrica>_<operacao>_same_api_<api>.svg` — compara Python e TypeScript
  para uma operação;
- `<metrica>_<operacao>_all_apis_<N>u.svg` — compara todas as APIs e
  linguagens para uma operação e carga.

`<metrica>` será `average` para a média do tempo de resposta, `p95` para o
percentil 95 ou `response_size` para o corpo médio recebido.
`<operacao>` será `get`, `post`, `update` ou `delete`.

A latência média de cada operação é ponderada pela quantidade de requisições
das três entidades. Como o CSV do Locust não fornece o histograma combinado
por categoria, o P95 por operação é uma aproximação ponderada dos P95 de
usuários, músicas e playlists.

Todos os eixos quantitativos usam **escala linear iniciada em zero**. Assim,
por exemplo, a distância visual entre 400 ms e 700 ms representa exatamente
300 ms; não há compressão logarítmica no ranking entre APIs.

Para usar outros diretórios:

```bash
python3 generate_latency_charts.py --reports reports --output reports/charts
```

## Resumo dos resultados coletados

Resultados da linha `Aggregated` dos CSVs atuais, com **60 segundos por
execução**, ramp-up de **50 usuários/s** e **4 processos Locust**. CPU e
memória não aparecem porque precisam ser coletadas separadamente com
`docker stats`.

### 250 usuários simultâneos

| API | Linguagem | RPS | Média (ms) | P95 (ms) | P99 (ms) | Corpo médio (B) | Falhas |
|-----|-----------|----:|-----------:|---------:|---------:|----------------:|-------:|
| REST | Python | 392,1 | 512,4 | 660 | 760 | 780 | 0 |
| REST | TypeScript | 1566,2 | 59,2 | 92 | 120 | 694 | 0 |
| GraphQL | Python | 191,5 | 1148,4 | 1400 | 1600 | 871 | 0 |
| GraphQL | TypeScript | 886,9 | 173,9 | 280 | 360 | 771 | 0 |
| SOAP | Python | 195,0 | 1124,8 | 1300 | 1500 | 1828 | 0 |
| SOAP | TypeScript | 1278,2 | 92,4 | 140 | 200 | 1676 | 0 |
| gRPC | Python | 330,6 | 624,8 | 1000 | 1200 | 434 | 0 |
| gRPC | TypeScript | 1962,4 | 29,8 | 51 | 69 | 347 | 0 |

### 800 usuários simultâneos

| API | Linguagem | RPS | Média (ms) | P95 (ms) | P99 (ms) | Corpo médio (B) | Falhas |
|-----|-----------|----:|-----------:|---------:|---------:|----------------:|-------:|
| REST | Python | 340,2 | 1902,4 | 2500 | 3200 | 801 | 0 |
| REST | TypeScript | 1522,9 | 356,4 | 480 | 790 | 787 | 0 |
| GraphQL | Python | 169,4 | 3838,2 | 5100 | 13000 | 891 | 0 |
| GraphQL | TypeScript | 847,1 | 711,1 | 1100 | 1700 | 828 | 0 |
| SOAP | Python | 165,8 | 3896,1 | 5100 | 5200 | 1845 | 0 |
| SOAP | TypeScript | 1127,8 | 509,1 | 810 | 1200 | 1826 | 0 |
| gRPC | Python | 312,6 | 2086,5 | 3900 | 5000 | 432 | 0 |
| gRPC | TypeScript | 1877,1 | 270,7 | 470 | 530 | 405 | 0 |

### Leitura dos resultados

- **Maior vazão:** gRPC TypeScript, com aproximadamente `1962 RPS` em 250
  usuários e `1877 RPS` em 800 usuários.
- **Melhor latência em 250 usuários:** gRPC TypeScript, com média de
  `29,8 ms` e P95 de `51 ms`.
- **Melhor latência em 800 usuários:** gRPC TypeScript, com média de
  `270,7 ms`, P95 de `470 ms` e P99 de `530 ms`.
- **Menor corpo médio no CRUD completo:** gRPC nas duas linguagens; SOAP
  apresentou os maiores corpos por causa do envelope XML.
- **Entre os serviços Python:** REST obteve a maior vazão e as menores
  latências nas duas cargas.
- As 16 execuções terminaram sem falhas agregadas.
- Todos os serviços degradaram em latência ao passar de 250 para 800
  usuários. Isso confirma que a carga concorrente do gRPC passou a ser
  aplicada corretamente após a integração do cliente com `gevent`.
- A comparação entre protocolos dentro da mesma linguagem é mais direta.
  Comparações Python × TypeScript também incluem diferenças de runtime,
  servidor, drivers e bibliotecas, não apenas do protocolo.

![P95 com 250 usuários](reports/charts/p95_all_apis_250u.svg)

![P95 com 800 usuários](reports/charts/p95_all_apis_800u.svg)

![Média com 250 usuários](reports/charts/average_all_apis_250u.svg)

![Média com 800 usuários](reports/charts/average_all_apis_800u.svg)

![Tamanho médio com 250 usuários](reports/charts/response_size_all_apis_250u.svg)

![Tamanho médio com 800 usuários](reports/charts/response_size_all_apis_800u.svg)

### Rodando um serviço isolado (interface web do Locust)

```bash
cd load-tests
# Python
locust -f locustfile_rest.py    --host http://localhost:8001    # REST py
locust -f locustfile_graphql.py --host http://localhost:8002    # GraphQL py
locust -f locustfile_soap.py    --host http://localhost:8000    # SOAP py
locust -f locustfile_grpc.py    --host localhost:50051          # gRPC py
# TypeScript (mesmos locustfiles, outras portas)
locust -f locustfile_rest.py    --host http://localhost:8011    # REST ts
locust -f locustfile_graphql.py --host http://localhost:8012    # GraphQL ts
locust -f locustfile_soap.py    --host http://localhost:8013    # SOAP ts
locust -f locustfile_grpc.py    --host localhost:50052          # gRPC ts
# abra http://localhost:8089 e defina nº de usuários e ramp-up
```

### Testando uma operação isolada

Os locustfiles possuem tags que permitem executar apenas uma operação, sem
alterar o cenário padrão.

#### Somente `GET /users/:id` no REST

Primeiro, confirme que os serviços estão em execução:

```bash
docker compose up -d
```

Depois, entre na pasta dos testes:

```bash
cd load-tests
```

Para testar somente `GET /users/:id` no REST Python:

```bash
locust -f locustfile_rest.py --host http://localhost:8001 \
  --headless -u 100 -r 20 -t 30s --tags get_user \
  --csv ../reports/rest_py_get_user \
  --html ../reports/rest_py_get_user.html
```

Para executar o mesmo teste no REST TypeScript:

```bash
locust -f locustfile_rest.py --host http://localhost:8011 \
  --headless -u 100 -r 20 -t 30s --tags get_user \
  --csv ../reports/rest_ts_get_user \
  --html ../reports/rest_ts_get_user.html
```

Nesse comando:

- `--host`: endereço do serviço, porta `8001` para Python e `8011` para
  TypeScript;
- `-u 100`: mantém até 100 usuários virtuais;
- `-r 20`: inicia 20 usuários por segundo;
- `-t 30s`: executa o teste por 30 segundos;
- `--tags get_user`: executa somente a tarefa `GET /users/:id`;
- `--csv`: grava estatísticas em CSV;
- `--html`: gera o relatório visual do Locust.

Os principais resultados estarão na linha `Aggregated` de
`reports/rest_py_get_user_stats.csv` ou
`reports/rest_ts_get_user_stats.csv`.

Para usar a interface web em vez do modo headless:

```bash
locust -f locustfile_rest.py --host http://localhost:8001 --tags get_user
```

Abra `http://localhost:8089`, informe a quantidade de usuários e o ramp-up e
inicie o teste. Pressione `Ctrl+C` para encerrar o Locust.

#### Outras operações do cenário padrão

As tags específicas disponíveis nos quatro protocolos são:
`list_musics`, `get_user`, `user_playlists`, `playlist_musics`,
`create_user` e `create_playlist_and_add`. Também existem as tags agrupadas
`read`, `write` e `create`.

Exemplos:

```bash
# Somente criação de usuário no REST TypeScript
locust -f locustfile_rest.py --host http://localhost:8011 \
  --headless -u 100 -r 20 -t 30s --tags create_user

# Somente query de usuário no GraphQL Python
locust -f locustfile_graphql.py --host http://localhost:8002 \
  --headless -u 100 -r 20 -t 30s --tags get_user

# Somente getUser no SOAP TypeScript
locust -f locustfile_soap.py --host http://localhost:8013 \
  --headless -u 100 -r 20 -t 30s --tags get_user

# Somente RPC GetUser no gRPC TypeScript
locust -f locustfile_grpc.py --host localhost:50052 \
  --headless -u 100 -r 20 -t 30s --tags get_user
```

REST usa verbos HTTP. GraphQL usa `query`/`mutation`, SOAP usa operações no
envelope XML e gRPC usa métodos RPC; portanto, `POST`, `PATCH` e `DELETE` não
se aplicam da mesma forma aos quatro protocolos.

#### Carga isolada de CRUD REST

O arquivo `load-tests/locustfile_rest_crud.py` mede separadamente listagem,
consulta individual, criação, atualização ou exclusão de usuários, músicas e
playlists.

Classes disponíveis:

| Recurso | Listar | Consultar por ID | Criar | Atualizar | Excluir |
|---------|--------|------------------|-------|-----------|---------|
| Users | `RestListUsers` | `RestGetUser` | `RestCreateUser` | `RestUpdateUser` | `RestDeleteUser` |
| Musics | `RestListMusics` | `RestGetMusic` | `RestCreateMusic` | `RestUpdateMusic` | `RestDeleteMusic` |
| Playlists | `RestListPlaylists` | `RestGetPlaylist` | `RestCreatePlaylist` | `RestUpdatePlaylist` | `RestDeletePlaylist` |

Escolha exatamente uma classe por execução. O formato geral é:

```bash
locust -f locustfile_rest_crud.py <CLASSE> \
  --host <HOST> --headless -u 100 -r 20 -t 30s \
  --csv ../reports/<NOME> \
  --html ../reports/<NOME>.html
```

Hosts:

- REST Python: `http://localhost:8001`
- REST TypeScript: `http://localhost:8011`

##### Users

```bash
cd load-tests

# GET /users
locust -f locustfile_rest_crud.py RestListUsers \
  --host http://localhost:8001 --headless -u 100 -r 20 -t 30s

# GET /users/:id
locust -f locustfile_rest_crud.py RestGetUser \
  --host http://localhost:8001 --headless -u 100 -r 20 -t 30s

# POST /users
locust -f locustfile_rest_crud.py RestCreateUser \
  --host http://localhost:8001 --headless -u 100 -r 20 -t 30s

# PATCH /users/:id
locust -f locustfile_rest_crud.py RestUpdateUser \
  --host http://localhost:8001 --headless -u 100 -r 20 -t 30s

# DELETE /users/:id
locust -f locustfile_rest_crud.py RestDeleteUser \
  --host http://localhost:8001 --headless -u 100 -r 20 -t 30s
```

##### Musics

```bash
cd load-tests

# GET /musics
locust -f locustfile_rest_crud.py RestListMusics \
  --host http://localhost:8001 --headless -u 100 -r 20 -t 30s

# GET /musics/:id
locust -f locustfile_rest_crud.py RestGetMusic \
  --host http://localhost:8001 --headless -u 100 -r 20 -t 30s

# POST /musics
locust -f locustfile_rest_crud.py RestCreateMusic \
  --host http://localhost:8001 --headless -u 100 -r 20 -t 30s

# PATCH /musics/:id
locust -f locustfile_rest_crud.py RestUpdateMusic \
  --host http://localhost:8001 --headless -u 100 -r 20 -t 30s

# DELETE /musics/:id
locust -f locustfile_rest_crud.py RestDeleteMusic \
  --host http://localhost:8001 --headless -u 100 -r 20 -t 30s
```

##### Playlists

```bash
cd load-tests

# GET /playlists
locust -f locustfile_rest_crud.py RestListPlaylists \
  --host http://localhost:8001 --headless -u 100 -r 20 -t 30s

# GET /playlists/:id
locust -f locustfile_rest_crud.py RestGetPlaylist \
  --host http://localhost:8001 --headless -u 100 -r 20 -t 30s

# POST /playlists
locust -f locustfile_rest_crud.py RestCreatePlaylist \
  --host http://localhost:8001 --headless -u 100 -r 20 -t 30s

# PATCH /playlists/:id
locust -f locustfile_rest_crud.py RestUpdatePlaylist \
  --host http://localhost:8001 --headless -u 100 -r 20 -t 30s

# DELETE /playlists/:id
locust -f locustfile_rest_crud.py RestDeletePlaylist \
  --host http://localhost:8001 --headless -u 100 -r 20 -t 30s
```

Para testar TypeScript, mantenha a classe e troque o host para
`http://localhost:8011`.

Nos testes de atualização, cada usuário virtual cria um registro próprio
antes da medição. Nos testes de exclusão, um registro descartável é criado
antes de cada DELETE. Nos testes de criação, o registro é removido depois que
o POST foi medido. Essas requisições de preparação e limpeza passam pela API
com o cliente instrumentado do Locust e entram nas mesmas linhas de criação
ou exclusão. Para uma medição rigorosamente isolada de escrita, use uma base
exclusiva para o teste e restaure o seed ao final.

#### CRUD isolado em GraphQL, SOAP e gRPC

Os outros protocolos também possuem os mesmos 15 cenários isolados:

| Protocolo | Locustfile | Prefixo das classes | Python | TypeScript |
|-----------|------------|---------------------|--------|------------|
| GraphQL | `locustfile_graphql_crud.py` | `GraphQL` | `http://localhost:8002` | `http://localhost:8012` |
| SOAP | `locustfile_soap_crud.py` | `Soap` | `http://localhost:8000` | `http://localhost:8013` |
| gRPC | `locustfile_grpc_crud.py` | `Grpc` | `localhost:50051` | `localhost:50052` |

Combine o prefixo do protocolo com uma das operações:

| Recurso | Listar | Consultar por ID | Criar | Atualizar | Excluir |
|---------|--------|------------------|-------|-----------|---------|
| Users | `ListUsers` | `GetUser` | `CreateUser` | `UpdateUser` | `DeleteUser` |
| Musics | `ListMusics` | `GetMusic` | `CreateMusic` | `UpdateMusic` | `DeleteMusic` |
| Playlists | `ListPlaylists` | `GetPlaylist` | `CreatePlaylist` | `UpdatePlaylist` | `DeletePlaylist` |

Por exemplo, `GraphQLGetMusic`, `SoapUpdatePlaylist` e `GrpcDeleteUser`.
Escolha exatamente uma classe por execução.

##### GraphQL

```bash
cd load-tests

# Query: music por ID no GraphQL Python
locust -f locustfile_graphql_crud.py GraphQLGetMusic \
  --host http://localhost:8002 --headless -u 100 -r 20 -t 30s \
  --csv ../reports/graphql_py_get_music \
  --html ../reports/graphql_py_get_music.html

# Mutation: atualizar música no GraphQL TypeScript
locust -f locustfile_graphql_crud.py GraphQLUpdateMusic \
  --host http://localhost:8012 --headless -u 100 -r 20 -t 30s \
  --csv ../reports/graphql_ts_update_music \
  --html ../reports/graphql_ts_update_music.html
```

##### SOAP

```bash
cd load-tests

# Operação listPlaylists no SOAP Python
locust -f locustfile_soap_crud.py SoapListPlaylists \
  --host http://localhost:8000 --headless -u 100 -r 20 -t 30s \
  --csv ../reports/soap_py_list_playlists \
  --html ../reports/soap_py_list_playlists.html

# Operação deletePlaylist no SOAP TypeScript
locust -f locustfile_soap_crud.py SoapDeletePlaylist \
  --host http://localhost:8013 --headless -u 100 -r 20 -t 30s \
  --csv ../reports/soap_ts_delete_playlist \
  --html ../reports/soap_ts_delete_playlist.html
```

##### gRPC

```bash
cd load-tests

# RPC ListUsers no gRPC Python
locust -f locustfile_grpc_crud.py GrpcListUsers \
  --host localhost:50051 --headless -u 100 -r 20 -t 30s \
  --csv ../reports/grpc_py_list_users \
  --html ../reports/grpc_py_list_users.html

# RPC CreateUser no gRPC TypeScript
locust -f locustfile_grpc_crud.py GrpcCreateUser \
  --host localhost:50052 --headless -u 100 -r 20 -t 30s \
  --csv ../reports/grpc_ts_create_user \
  --html ../reports/grpc_ts_create_user.html
```

Em GraphQL, consultas são `query` e escritas são `mutation`, embora ambas
trafeguem por HTTP POST. No SOAP, cada ação é uma operação do envelope XML.
No gRPC, cada ação é um método RPC. Os cenários de escrita usam registros
temporários e seguem a mesma estratégia de preparação e limpeza descrita no
CRUD REST. Uma interrupção forçada pode impedir a limpeza final de algum
registro; para testes de escrita oficiais, use uma base dedicada e descarte
ou restaure o banco após a execução.

#### Teste funcional REST com `curl`

Use a porta `8001` para Python ou `8011` para TypeScript:

```bash
BASE=http://localhost:8001

curl "$BASE/users/1"

curl -X POST "$BASE/users" -H 'Content-Type: application/json' \
  -d '{"name":"Teste","email":"teste-unico@example.com"}'

# Substitua 401 pelo ID retornado no POST
curl -X PATCH "$BASE/users/401" -H 'Content-Type: application/json' \
  -d '{"name":"Teste atualizado"}'

curl -i -X DELETE "$BASE/users/401"
```

Para GraphQL, as quatro ações continuam sendo enviadas por HTTP POST:

```bash
curl -X POST http://localhost:8002/graphql \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ user(id:1){ id name email } }"}'

curl -X POST http://localhost:8002/graphql \
  -H 'Content-Type: application/json' \
  -d '{"query":"mutation { updateUser(id:1,name:\"Novo nome\"){ id name } }"}'
```

Para SOAP, consulte `http://localhost:8000/?wsdl` ou
`http://localhost:8013/?wsdl`. Para gRPC, os métodos equivalentes são
`GetUser`, `CreateUser`, `UpdateUser` e `DeleteUser`, definidos em
`python/grpc_api/streaming.proto`.

### CPU e memória

O Locust mede **vazão e latência**. Para **CPU e memória** por serviço,
abra outro terminal **durante** o teste e rode:

```bash
docker stats
```

Anote o `%CPU` e o `MEM USAGE` de cada container no pico da carga. Os
containers são `api-comparison-<serviço>-1`, com `<serviço>` ∈ {`rest`,
`graphql`, `soap`, `grpc`, `rest_ts`, `graphql_ts`, `soap_ts`, `grpc_ts`}.

## Montando o relatório

Preencha a tabela de `REPORT_TEMPLATE.md` com os números de `reports/` e do
`docker stats`. As colunas pedidas: **Tecnologia | Linguagem | RPS | Latência
média | P95 | P99 | CPU | Memória**, em dois cenários (**50** e **200**
usuários simultâneos, ou ajuste o template para os níveis atuais de **250** e
**800**. O template traz orientações de leitura e conclusão
(mais rápida, menor consumo, menos código, mais simples, melhor
custo-benefício).
