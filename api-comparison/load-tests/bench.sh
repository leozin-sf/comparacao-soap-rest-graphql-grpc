#!/usr/bin/env bash
# Uso: bench.sh <nome> <locustfile> <host> <users> <secs> <server_pid> <outfile>
# Roda Locust headless e, em paralelo, amostra CPU%/RSS do processo do servidor
# (incluindo filhos) via ps. Anexa uma linha CSV ao outfile.
set -u
NAME="$1"; LF="$2"; HOST="$3"; USERS="$4"; SECS="$5"; SPID="$6"; OUT="$7"

# --- amostrador de recursos em background ---
SAMPLES=/tmp/samples_$$.txt
: > "$SAMPLES"
(
  for _ in $(seq 1 "$SECS"); do
    # soma %CPU e RSS(KB) do servidor + filhos
    PIDS=$(pgrep -P "$SPID" 2>/dev/null; echo "$SPID")
    PIDS=$(echo "$PIDS" | tr '\n' ',' | sed 's/,$//')
    ps -o %cpu=,rss= -p "$PIDS" 2>/dev/null \
      | awk '{c+=$1; r+=$2} END{printf "%.1f %d\n", c, r}' >> "$SAMPLES"
    sleep 1
  done
) &
SAMPLER=$!

# --- carga ---
SUMMARY=$(cd "$(dirname "$LF")" && locust -f "$(basename "$LF")" --host "$HOST" \
  --headless -u "$USERS" -r "$USERS" -t "${SECS}s" --only-summary 2>&1 \
  | grep -E "Aggregated" )

kill "$SAMPLER" 2>/dev/null; wait "$SAMPLER" 2>/dev/null

# linha 1 = stats (reqs, fails, avg, min, max, med, rps, fps)
LINE1=$(echo "$SUMMARY" | head -1)
REQS=$(echo "$LINE1" | awk '{print $2}')
FAILS=$(echo "$LINE1" | awk '{print $3}' | grep -oE '^[0-9]+')
AVG=$(echo "$LINE1" | awk '{print $5}')
RPS=$(echo "$LINE1" | awk '{print $(NF-1)}')
# linha 2 = percentis: ... 50 66 75 80 90 95 98 99 ...
LINE2=$(echo "$SUMMARY" | tail -1)
P95=$(echo "$LINE2" | awk '{print $7}')
P99=$(echo "$LINE2" | awk '{print $9}')

# recursos: CPU% médio e RSS máx (MB)
CPU=$(awk '{c+=$1; n++} END{if(n)printf "%.0f", c/n; else print 0}' "$SAMPLES")
MEM=$(awk 'BEGIN{m=0} {if($2>m)m=$2} END{printf "%.0f", m/1024}' "$SAMPLES")
rm -f "$SAMPLES"

echo "${NAME},${USERS},${REQS},${FAILS},${RPS},${AVG},${P95},${P99},${CPU},${MEM}" >> "$OUT"
echo "[${NAME} @ ${USERS}u] reqs=${REQS} fails=${FAILS} rps=${RPS} avg=${AVG}ms p95=${P95} p99=${P99} cpu=${CPU}% mem=${MEM}MB"
