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

## Integrantes

| Nome | Matrícula |
|------|:---------:|
| Leonardo Silva | 2319973 |
| Ravi Freitas | 2316154 |
| Luca Solon | 1910486 |
| Luiz Henrique | 2520528 |

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
├── run_benchmarks.sh           # roda Locust (50/200 usuários) -> reports/
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
# 1) sobe Postgres + os 5 serviços
docker compose up -d --build

# 2) popula a base (500 usuários, 1000 músicas, 100 playlists)
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

Os testes usam **Locust**. O cenário (em todos os protocolos) mistura as
operações com pesos realistas: listar músicas (5), consultar usuário (4),
listar playlists do usuário (3), listar músicas da playlist (3), criar usuário
(2) e criar playlist + adicionar música (1).

### Rodando a bateria completa

Com os serviços no ar e as dependências instaladas no host:

```bash
pip install -r load-tests/requirements.txt
./run_benchmarks.sh                       # 50 e 200 usuários, 60s cada
# ou personalize:
USERS="50 200 500" DURATION=120 ./run_benchmarks.sh
```

Isso gera, em `reports/`, para cada serviço e nível de carga:

- `<serviço>_<N>u_stats.csv` — **RPS, latências, P50…P100, falhas** (use a
  linha `Aggregated`);
- `<serviço>_<N>u_stats_history.csv` — série temporal;
- `<serviço>_<N>u.html` — dashboard visual (bom para anexar ao relatório).

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
usuários simultâneos). O template traz orientações de leitura e conclusão
(mais rápida, menor consumo, menos código, mais simples, melhor
custo-benefício).
