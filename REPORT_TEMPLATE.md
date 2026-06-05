# Relatório Comparativo — SOAP × REST × GraphQL × gRPC

> Disciplina: Computação Distribuída — Prof. Nabor C. Mendonça
> Domínio: serviço de streaming de músicas (usuários, músicas, playlists)
>
> Preencha as tabelas abaixo com os números gerados em `reports/` (Locust) e
> no `docker stats` (CPU/memória). Cada linha vem da linha **Aggregated** do
> arquivo `reports/<serviço>_<N>u_stats.csv`.

## 1. Metodologia

- **Massa de dados:** 500 usuários, 1000 músicas, 100 playlists, vínculos
  playlist↔música aleatórios (gerados por `python -m common.seed`).
- **Persistência única:** todos os serviços usam o **mesmo PostgreSQL** e a
  **mesma camada de repositório** por linguagem — a única variável é o
  protocolo.
- **Cenário de carga (Locust):** mix ponderado de listagens, consultas
  relacionais e escritas (pesos 5/4/3/3/2/1).
- **Níveis de carga:** 50 e 200 usuários simultâneos, ramp-up de 50 u/s.
- **Duração:** ___ s por execução (preencher; sugestão: 60 s).
- **Ambiente:** ___ (CPU, RAM, SO, versão do Docker — preencher).

## 2. Resultados — 50 usuários simultâneos

| Tecnologia | Linguagem  | RPS | Latência média (ms) | P95 (ms) | P99 (ms) | CPU (%) | Memória (MB) | Falhas |
|------------|------------|----:|--------------------:|---------:|---------:|--------:|-------------:|-------:|
| REST       | Python     |     |                     |          |          |         |              |        |
| REST       | TypeScript |     |                     |          |          |         |              |        |
| GraphQL    | Python     |     |                     |          |          |         |              |        |
| GraphQL    | TypeScript |     |                     |          |          |         |              |        |
| SOAP       | Python     |     |                     |          |          |         |              |        |
| SOAP       | TypeScript |     |                     |          |          |         |              |        |
| gRPC       | Python     |     |                     |          |          |         |              |        |
| gRPC       | TypeScript |     |                     |          |          |         |              |        |

## 3. Resultados — 200 usuários simultâneos

| Tecnologia | Linguagem  | RPS | Latência média (ms) | P95 (ms) | P99 (ms) | CPU (%) | Memória (MB) | Falhas |
|------------|------------|----:|--------------------:|---------:|---------:|--------:|-------------:|-------:|
| REST       | Python     |     |                     |          |          |         |              |        |
| REST       | TypeScript |     |                     |          |          |         |              |        |
| GraphQL    | Python     |     |                     |          |          |         |              |        |
| GraphQL    | TypeScript |     |                     |          |          |         |              |        |
| SOAP       | Python     |     |                     |          |          |         |              |        |
| SOAP       | TypeScript |     |                     |          |          |         |              |        |
| gRPC       | Python     |     |                     |          |          |         |              |        |
| gRPC       | TypeScript |     |                     |          |          |         |              |        |

## 4. Complexidade de implementação (qualitativo)

| Critério                         | SOAP | REST | GraphQL | gRPC |
|----------------------------------|------|------|---------|------|
| Linhas de código do adaptador¹   |      |      |         |      |
| Curva de configuração inicial    |      |      |         |      |
| Contrato/tipagem forte           | WSDL | (informal/OpenAPI) | SDL | .proto |
| Ferramentas de cliente prontas   |      |      |         |      |
| Facilidade de depuração (texto?) | sim (XML) | sim (JSON) | sim (JSON) | não (binário) |

> ¹ Conte as linhas dos adaptadores (todos finos, sobre o mesmo repositório):
> Python — `soap/server.py`, `rest/app.py`, `graphql_api/app.py`,
> `grpc_api/server.py`; TypeScript — `src/soap/server.ts`, `src/rest/server.ts`,
> `src/graphql/server.ts`, `src/grpc/server.ts`. A lógica de negócio fica em
> `common/repository.py` e `src/common/repository.ts`.

## 5. Conclusão (preencher com base nos seus números)

- **Maior vazão (RPS) / menor latência:** ___
- **Menor consumo de recursos (CPU/memória):** ___
- **Menos código / mais simples de implementar:** ___
- **Melhor para APIs públicas / navegador:** ___
- **Melhor custo-benefício no cenário do trabalho:** ___

---

## Apêndice — Números de referência (ambiente de desenvolvimento)

> ⚠️ **Estes números NÃO devem ir no relatório final.** Foram coletados em um
> ambiente de testes (container Linux, PostgreSQL local, execuções curtas de
> ~12 s) apenas para validar o ferramental e ilustrar o padrão esperado.
> Gere os seus próprios números na sua máquina com `run_benchmarks.sh`.

**50 usuários (~12 s):**

| Tecnologia | Linguagem | RPS | Média (ms) | P95 (ms) | P99 (ms) | CPU (%) | Mem (MB) | Falhas |
|------------|-----------|----:|-----------:|---------:|---------:|--------:|---------:|-------:|
| REST       | Python    | 170 | 9          | 17       | 150      | 19      | 75       | 0      |
| GraphQL    | Python    | 167 | 17         | 43       | 170      | 32      | 82       | 0      |
| SOAP       | Python    | 147 | 53         | 97       | 1100     | 25      | 72       | 25     |
| gRPC       | Python    | 175 | 2          | 4        | 6        | 14      | 63       | 0      |

**200 usuários (~12 s):**

| Tecnologia | Linguagem | RPS | Média (ms) | P95 (ms) | P99 (ms) | CPU (%) | Mem (MB) | Falhas |
|------------|-----------|----:|-----------:|---------:|---------:|--------:|---------:|-------:|
| REST       | Python    | 332 | 264        | 470      | 610      | 28      | 81       | 0      |
| GraphQL    | Python    | 228 | 578        | 690      | 4500     | 46      | 85       | 0      |
| SOAP       | Python    | 221 | 577        | 2300     | 3300     | 41      | 73       | 339    |
| gRPC       | Python    | 543 | 1          | 3        | 4        | 26      | 63       | 0      |

**Padrão observado (para interpretar os seus resultados):**

- **gRPC** teve a maior vazão e a menor latência, e foi o único cuja latência
  **não degradou** ao subir de 50 → 200 usuários (multiplexação HTTP/2 +
  serialização binária Protobuf), além do menor consumo de memória.
- **REST** ficou em segundo lugar e escalou de forma estável (sem falhas).
- **GraphQL** pagou o overhead de parse/resolução da query: vazão menor e
  caudas de latência (P99) maiores sob carga.
- **SOAP** foi o mais pesado: parsing/validação de XML mais caro e o servidor
  WSGI começou a **falhar requisições** sob 200 usuários — o ponto mais frágil
  em concorrência alta.
