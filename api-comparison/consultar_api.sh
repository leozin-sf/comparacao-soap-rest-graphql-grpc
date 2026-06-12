#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./consultar_api.sh <api> <recurso> <linguagem> [id]

APIs:
  rest | graphql | soap | grpc | all

Recursos:
  users | musics | playlists

Linguagens:
  python | typescript

Exemplos:
  ./consultar_api.sh rest users python
  ./consultar_api.sh graphql musics typescript
  ./consultar_api.sh soap playlists python
  ./consultar_api.sh grpc users typescript 1
  ./consultar_api.sh all users python
  LIMIT=800 ./consultar_api.sh all users python
EOF
}

if (( $# < 3 || $# > 4 )); then
  usage
  exit 1
fi

api="$1"
resource="$2"
language="$3"
resource_id="${4:-}"
limit="${LIMIT:-5}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! "$limit" =~ ^[1-9][0-9]*$ ]]; then
  echo "LIMIT deve ser um número inteiro maior que zero." >&2
  exit 1
fi

case "$resource" in
  users)
    singular="User"
    fields="id name email"
    ;;
  musics)
    singular="Music"
    fields="id title artist album durationSeconds"
    ;;
  playlists)
    singular="Playlist"
    fields="id name userId"
    ;;
  *)
    echo "Recurso inválido: $resource" >&2
    usage
    exit 1
    ;;
esac

case "$language" in
  python)
    rest_port=8001
    graphql_port=8002
    soap_port=8000
    grpc_port=50051
    ;;
  typescript)
    rest_port=8011
    graphql_port=8012
    soap_port=8013
    grpc_port=50052
    ;;
  *)
    echo "Linguagem inválida: $language" >&2
    usage
    exit 1
    ;;
esac

if [[ -n "$resource_id" && ! "$resource_id" =~ ^[0-9]+$ ]]; then
  echo "O id deve ser um número inteiro." >&2
  exit 1
fi

pretty_json() {
  python3 -m json.tool
}

query_rest() {
  local url

  if [[ -n "$resource_id" ]]; then
    url="http://localhost:${rest_port}/${resource}/${resource_id}"
  else
    url="http://localhost:${rest_port}/${resource}?limit=${limit}&offset=0"
  fi

  curl -fsS "$url" | pretty_json
}

query_graphql() {
  local field query payload

  if [[ -n "$resource_id" ]]; then
    field="${singular,}"
    query="{ ${field}(id: ${resource_id}) { ${fields} } }"
  else
    query="{ ${resource}(limit: ${limit}, offset: 0) { ${fields} } }"
  fi

  payload="$(printf '{"query":"%s"}' "$query")"
  curl -fsS -X POST "http://localhost:${graphql_port}/graphql" \
    -H 'Content-Type: application/json' \
    --data-binary "$payload" |
    pretty_json
}

query_soap() {
  local operation body response

  if [[ -n "$resource_id" ]]; then
    operation="get${singular}"
    body="<tns:${operation}><tns:id>${resource_id}</tns:id></tns:${operation}>"
  else
    operation="list${singular}s"
    body="<tns:${operation}><tns:limit>${limit}</tns:limit><tns:offset>0</tns:offset></tns:${operation}>"
  fi

  response="$(
    curl -fsS -X POST "http://localhost:${soap_port}/" \
      -H 'Content-Type: text/xml; charset=utf-8' \
      -H 'SOAPAction: ""' \
      --data-binary "<?xml version=\"1.0\"?><soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:tns=\"streaming.soap\"><soapenv:Body>${body}</soapenv:Body></soapenv:Envelope>"
  )"
  printf '%s\n' "$response"
}

query_grpc() {
  local operation data

  if [[ -n "$resource_id" ]]; then
    operation="Get${singular}"
    data="{\"id\":${resource_id}}"
  else
    operation="List${singular}s"
    data="{\"limit\":${limit},\"offset\":0}"
  fi

  docker run --rm --network host \
    -v "${script_dir}/python/grpc_api:/protos:ro" \
    fullstorydev/grpcurl:latest \
    -plaintext \
    -import-path /protos \
    -proto streaming.proto \
    -d "$data" \
    "localhost:${grpc_port}" \
    "streaming.StreamingService/${operation}"
}

query_one() {
  case "$1" in
    rest) query_rest ;;
    graphql) query_graphql ;;
    soap) query_soap ;;
    grpc) query_grpc ;;
    *)
      echo "API inválida: $1" >&2
      usage
      exit 1
      ;;
  esac
}

if [[ "$api" == "all" ]]; then
  for current_api in rest graphql soap grpc; do
    printf '\n===== %s / %s / %s =====\n' \
      "$current_api" "$resource" "$language"
    query_one "$current_api"
  done
else
  query_one "$api"
fi
