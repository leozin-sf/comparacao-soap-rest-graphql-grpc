# Imagem ÚNICA para os 4 serviços TypeScript (REST, GraphQL, SOAP, gRPC).
# Espelha a estratégia do lado Python: build uma vez, o docker-compose varia
# apenas o `command`. Mantém a comparação justa (mesma base, mesmo repositório).
FROM node:22-slim AS build
WORKDIR /app
COPY package.json tsconfig.json ./
RUN npm install
COPY src ./src
COPY proto ./proto
RUN npm run build

FROM node:22-slim
WORKDIR /app
ENV NODE_ENV=production
COPY package.json ./
RUN npm install --omit=dev
COPY --from=build /app/dist ./dist
# proto/ é lido em runtime pelos servidores gRPC (.proto) e SOAP (.wsdl).
COPY proto ./proto
# CMD padrão sobrescrito por cada serviço no docker-compose.yml.
CMD ["node", "dist/rest/server.js"]
