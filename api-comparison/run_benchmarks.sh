#!/usr/bin/env bash
# ============================================================================
# run_benchmarks.sh — orquestra a bateria de testes de carga (Locust) contra
# os serviços JÁ EM EXECUÇÃO (via `docker compose up -d` + seed).
#
# Para cada serviço e cada nível de carga, executa as 15 operações CRUD
# (listar, consultar, criar, atualizar e excluir users, musics e playlists)
# e gera relatórios NATIVOS do Locust:
#   reports/<serviço>_<usuários>u_stats.csv          (RPS, latências, falhas)
#   reports/<serviço>_<usuários>u_stats_history.csv  (série temporal)
#   reports/<serviço>_<usuários>u.html               (dashboard visual)
#
# Métricas de CPU/memória: rode `docker stats` em outro terminal durante o
# teste (ver README). O Locust mede RPS/latência/P95/P99/falhas; o Docker
# mede CPU/memória por container.
#
# Pré-requisitos no host:
#   pip install -r load-tests/requirements.txt
#   docker compose up -d && docker compose run --rm seed
#
# Uso:
#   ./run_benchmarks.sh               # níveis padrão: 250 e 800 usuários, 60s
#   USERS="50 200 500" DURATION=120 ./run_benchmarks.sh
# ============================================================================
set -euo pipefail

cd "$(dirname "$0")"
LT=load-tests
OUT=reports
mkdir -p "$OUT"

# Níveis de carga e duração (segundos). Ajuste via variáveis de ambiente.
USERS="${USERS:-250 800}"
DURATION="${DURATION:-60}"
SPAWN="${SPAWN:-50}"   # usuários gerados por segundo (ramp-up)
PROCESSES="${PROCESSES:-4}"
STOP_TIMEOUT="${STOP_TIMEOUT:-60}"
COOLDOWN="${COOLDOWN:-5}"

# Os locustfiles CRUD possuem uma classe por operação.
CRUD_OPERATIONS=(
  ListUsers GetUser CreateUser UpdateUser DeleteUser
  ListMusics GetMusic CreateMusic UpdateMusic DeleteMusic
  ListPlaylists GetPlaylist CreatePlaylist UpdatePlaylist DeletePlaylist
)

# serviço -> "locustfile|host|prefixo das classes"
declare -A SERVICES=(
  ["rest_py"]="$LT/locustfile_rest_crud.py|http://localhost:8001|Rest"
  ["graphql_py"]="$LT/locustfile_graphql_crud.py|http://localhost:8002|GraphQL"
  ["soap_py"]="$LT/locustfile_soap_crud.py|http://localhost:8000|Soap"
  ["grpc_py"]="$LT/locustfile_grpc_crud.py|localhost:50051|Grpc"
  ["rest_ts"]="$LT/locustfile_rest_crud.py|http://localhost:8011|Rest"
  ["graphql_ts"]="$LT/locustfile_graphql_crud.py|http://localhost:8012|GraphQL"
  ["soap_ts"]="$LT/locustfile_soap_crud.py|http://localhost:8013|Soap"
  ["grpc_ts"]="$LT/locustfile_grpc_crud.py|localhost:50052|Grpc"
)

# Ordem amigável de execução (Python e depois TypeScript, por protocolo).
DEFAULT_ORDER=(rest_py rest_ts graphql_py graphql_ts soap_py soap_ts grpc_py grpc_ts)
read -r -a ORDER <<< "${BENCHMARK_SERVICES:-${DEFAULT_ORDER[*]}}"

echo ">> Níveis de carga: ${USERS} | duração: ${DURATION}s cada"
echo ">> Cenário: CRUD completo (15 operações por serviço)"
echo ">> Preparo/limpeza: chamadas reais pela API, contabilizadas nas operações"
echo ">> DICA: em outro terminal rode  'docker stats'  para CPU/memória."
echo ""

for svc in "${ORDER[@]}"; do
  if [[ -z "${SERVICES[$svc]+x}" ]]; then
    echo "ERRO: serviço desconhecido em BENCHMARK_SERVICES: $svc" >&2
    exit 1
  fi

  IFS='|' read -r lf host class_prefix <<< "${SERVICES[$svc]}"
  lfdir=$(dirname "$lf")
  lfname=$(basename "$lf")
  user_classes=()
  for operation in "${CRUD_OPERATIONS[@]}"; do
    user_classes+=("${class_prefix}${operation}")
  done

  for u in $USERS; do
    if (( u < ${#CRUD_OPERATIONS[@]} )); then
      echo "ERRO: USERS deve ser >= ${#CRUD_OPERATIONS[@]} para incluir todas as operações CRUD." >&2
      exit 1
    fi

    report_prefix="$OUT/${svc}_${u}u"
    prefix="../$report_prefix"
    echo "==== $svc @ ${u} usuários (${DURATION}s) -> $host ===="
    rm -f "${report_prefix}.html" "${report_prefix}"_*.csv
    ( cd "$lfdir" && locust -f "$lfname" "${user_classes[@]}" \
        --host "$host" --headless \
        -u "$u" -r "$SPAWN" -t "${DURATION}s" --processes "$PROCESSES" \
        --stop-timeout "$STOP_TIMEOUT" \
        --csv "$prefix" --html "${prefix}.html" --only-summary )
    python3 validate_benchmark_report.py "$report_prefix" \
      --expected-operations "${#CRUD_OPERATIONS[@]}"
    echo ""
    sleep "$COOLDOWN"
  done
done

echo ">> Concluído. Relatórios em ./$OUT/"
echo ">> Cada *_stats.csv contém as 15 operações CRUD e a linha 'Aggregated'."
echo ">> Average Content Size registra o corpo médio recebido pelo cliente."
echo ">> Em GraphQL e SOAP o tipo HTTP continuará POST; a operação está em 'Name'."
