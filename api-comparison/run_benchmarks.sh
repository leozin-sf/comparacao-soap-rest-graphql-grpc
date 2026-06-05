#!/usr/bin/env bash
# ============================================================================
# run_benchmarks.sh — orquestra a bateria de testes de carga (Locust) contra
# os serviços JÁ EM EXECUÇÃO (via `docker compose up -d` + seed).
#
# Para cada serviço e cada nível de carga, gera relatórios NATIVOS do Locust:
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
#   ./run_benchmarks.sh                # níveis padrão: 50 e 200 usuários, 60s
#   USERS="50 200 500" DURATION=120 ./run_benchmarks.sh
# ============================================================================
set -euo pipefail

cd "$(dirname "$0")"
LT=load-tests
OUT=reports
mkdir -p "$OUT"

# Níveis de carga e duração (segundos). Ajuste via variáveis de ambiente.
USERS="${USERS:-50 200}"
DURATION="${DURATION:-60}"
SPAWN="${SPAWN:-50}"   # usuários gerados por segundo (ramp-up)

# serviço -> "locustfile|host"
declare -A SERVICES=(
  ["rest_py"]="$LT/locustfile_rest.py|http://localhost:8001"
  ["graphql_py"]="$LT/locustfile_graphql.py|http://localhost:8002"
  ["soap_py"]="$LT/locustfile_soap.py|http://localhost:8000"
  ["grpc_py"]="$LT/locustfile_grpc.py|localhost:50051"
  ["rest_ts"]="$LT/locustfile_rest.py|http://localhost:8011"
  ["graphql_ts"]="$LT/locustfile_graphql.py|http://localhost:8012"
  ["soap_ts"]="$LT/locustfile_soap.py|http://localhost:8013"
  ["grpc_ts"]="$LT/locustfile_grpc.py|localhost:50052"
)

# Ordem amigável de execução (Python e depois TypeScript, por protocolo).
ORDER=(rest_py rest_ts graphql_py graphql_ts soap_py soap_ts grpc_py grpc_ts)

echo ">> Níveis de carga: ${USERS} | duração: ${DURATION}s cada"
echo ">> DICA: em outro terminal rode  'docker stats'  para CPU/memória."
echo ""

for svc in "${ORDER[@]}"; do
  IFS='|' read -r lf host <<< "${SERVICES[$svc]}"
  lfdir=$(dirname "$lf")
  lfname=$(basename "$lf")
  for u in $USERS; do
    prefix="../$OUT/${svc}_${u}u"
    echo "==== $svc @ ${u} usuários (${DURATION}s) -> $host ===="
    ( cd "$lfdir" && locust -f "$lfname" --host "$host" --headless \
        -u "$u" -r "$SPAWN" -t "${DURATION}s" \
        --csv "$prefix" --html "${prefix}.html" --only-summary ) \
      || echo "   (aviso: locust retornou erro para $svc @ ${u}u)"
    echo ""
  done
done

echo ">> Concluído. Relatórios em ./$OUT/"
echo ">> Use os arquivos *_stats.csv (coluna 'Aggregated') para montar a tabela"
echo "   comparativa do relatório, e os .html para anexar gráficos."
