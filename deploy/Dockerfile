ARG NODE_IMAGE=node:18-alpine
ARG PYTHON_IMAGE=python:3.11-slim
ARG NGINX_IMAGE=nginx:1.27-alpine

FROM ${NODE_IMAGE} AS web

WORKDIR /opt/vue-fastapi-admin/web
COPY ./web/package.json ./web/pnpm-lock.yaml* ./
RUN npm install -g pnpm@9 && pnpm install
COPY ./web ./
RUN pnpm build


FROM ${PYTHON_IMAGE} AS backend

ARG PIP_INDEX_URL=https://pypi.org/simple
WORKDIR /opt/vue-fastapi-admin

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc python3-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i ${PIP_INDEX_URL}

COPY . .

ENV LANG=C.UTF-8
EXPOSE 9999

ENTRYPOINT [ "sh", "deploy/entrypoint.sh" ]


FROM ${NGINX_IMAGE} AS gateway

COPY deploy/web.conf /etc/nginx/conf.d/default.conf
COPY deploy/proxy_params.conf /etc/nginx/proxy_params.conf
COPY --from=web /opt/vue-fastapi-admin/web/dist /usr/share/nginx/html

EXPOSE 80
