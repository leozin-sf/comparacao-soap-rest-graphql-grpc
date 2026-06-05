# Imagem ÚNICA compartilhada por todos os serviços Python (REST, GraphQL,
# gRPC, SOAP) e pelo job de seed. Usar a mesma imagem/base reforça a
# comparação justa: a única variável entre os serviços é o `command`.
FROM python:3.12-slim

WORKDIR /app

# Dependências de sistema mínimas. psycopg2-binary e lxml trazem wheels
# para cp312, mas mantemos libpq/build essentials por robustez em slim.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia toda a árvore python/ (common + os 4 adaptadores + proto/stubs).
COPY . /app

# (Re)gera os stubs gRPC a partir do .proto para casar com a versão de
# grpcio-tools instalada. Idempotente.
RUN cd /app/grpc_api \
    && python -m grpc_tools.protoc -I. \
       --python_out=. --grpc_python_out=. streaming.proto

# Permite `from common import ...` a partir de qualquer WORKDIR de serviço.
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# CMD padrão sobrescrito por cada serviço no docker-compose.yml.
CMD ["python", "-c", "print('Defina o command no docker-compose.yml')"]
