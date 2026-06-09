# Comparação de Tecnologias de API — SOAP × REST × GraphQL × gRPC

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
  linha `Aggregated`);
- `<serviço>_<N>u_stats_history.csv` — série temporal;
- `<serviço>_<N>u.html` — dashboard visual (bom para anexar ao relatório).

Cada arquivo `_stats.csv` contém uma linha por operação CRUD e a linha
`Aggregated`. Em GraphQL e SOAP, a coluna `Type` aparece como `POST` porque
esse é o transporte HTTP dos dois protocolos; a ação efetiva (`updateUser`,
`deleteMusic`, etc.) aparece na coluna `Name`. Em gRPC, `Name` contém o método
RPC.

### Gerando os gráficos comparativos de latência

Depois que todos os testes terminarem, execute na raiz do projeto:

```bash
python3 generate_latency_charts.py
```

O script detecta automaticamente os níveis de carga presentes em `reports/`
e cria gráficos de **latência média** e **P95** em `reports/charts/`. Além dos
resultados agregados do CRUD completo, são gerados comparativos para `get`,
`post` (criação), `update` e `delete`:

- `<metrica>_same_api_<api>.svg` — compara Python e TypeScript para a mesma
  API ao longo das cargas, considerando o CRUD completo;
- `<metrica>_all_apis_<N>u.svg` — compara todas as APIs e linguagens na mesma
  carga, considerando o CRUD completo;
- `<metrica>_<operacao>_same_api_<api>.svg` — compara Python e TypeScript
  para uma operação;
- `<metrica>_<operacao>_all_apis_<N>u.svg` — compara todas as APIs e
  linguagens para uma operação e carga.

`<metrica>` será `average` para a média do tempo de resposta ou `p95` para o
percentil 95. `<operacao>` será `get`, `post`, `update` ou `delete`.

A latência média de cada operação é ponderada pela quantidade de requisições
das três entidades. Como o CSV do Locust não fornece o histograma combinado
por categoria, o P95 por operação é uma aproximação ponderada dos P95 de
usuários, músicas e playlists.

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

| API | Linguagem | RPS | Média (ms) | P95 (ms) | P99 (ms) | Falhas |
|-----|-----------|----:|-----------:|---------:|---------:|-------:|
| REST | Python | 503,5 | 359,0 | 400 | 430 | 0 |
| REST | TypeScript | 1975,5 | 4,0 | 8 | 14 | 0 |
| GraphQL | Python | 269,7 | 771,3 | 850 | 1700 | 0 |
| GraphQL | TypeScript | 1845,2 | 12,0 | 27 | 41 | 0 |
| SOAP | Python | 207,5 | 867,6 | 3500 | 7600 | 0 |
| SOAP | TypeScript | 1751,6 | 19,0 | 48 | 100 | 0 |
| gRPC | Python | 430,9 | 438,1 | 680 | 800 | 0 |
| gRPC | TypeScript | 1484,2 | 5,5 | 13 | 26 | 0 |

### 800 usuários simultâneos

| API | Linguagem | RPS | Média (ms) | P95 (ms) | P99 (ms) | Falhas |
|-----|-----------|----:|-----------:|---------:|---------:|-------:|
| REST | Python | 491,8 | 1284,2 | 1600 | 2900 | 0 |
| REST | TypeScript | 2340,0 | 178,9 | 370 | 530 | 0 |
| GraphQL | Python | 269,7 | 2405,2 | 2900 | 19000 | 0 |
| GraphQL | TypeScript | 1758,1 | 277,6 | 580 | 840 | 0 |
| SOAP | Python | 204,8 | 1406,8 | 5600 | 16000 | 1 |
| SOAP | TypeScript | 1701,1 | 155,0 | 340 | 450 | 0 |
| gRPC | Python | 439,9 | 1437,8 | 2500 | 3100 | 0 |
| gRPC | TypeScript | 1851,1 | 180,9 | 290 | 320 | 0 |

### Leitura dos resultados

- **Maior vazão:** REST TypeScript, com aproximadamente `1975 RPS` em 250
  usuários e `2340 RPS` em 800 usuários.
- **Melhor latência em 250 usuários:** REST TypeScript, com média de `4 ms`
  e P95 de `8 ms`.
- **Melhor cauda em 800 usuários:** gRPC TypeScript, com P95 de `290 ms` e
  P99 de `320 ms`.
- **Menor média em 800 usuários:** SOAP TypeScript, com `155 ms`, embora seu
  P95 de `340 ms` seja maior que o do gRPC TypeScript.
- **Entre os serviços Python:** REST obteve a maior vazão e as menores
  latências nas duas cargas. SOAP Python apresentou as maiores caudas e a
  única falha agregada.
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
o POST foi medido. Essas requisições de preparação e limpeza não entram nas
estatísticas do Locust, mas geram carga auxiliar no servidor e no banco. Para
uma medição rigorosamente isolada de escrita, use uma base exclusiva para o
teste e restaure o seed ao final.

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
