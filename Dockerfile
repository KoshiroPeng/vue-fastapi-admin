FROM node:18-alpine AS web

WORKDIR /opt/vue-fastapi-admin/web
COPY ./web/package.json ./web/pnpm-lock.yaml* ./
RUN npm install -g pnpm@9 && pnpm install
COPY ./web ./
RUN pnpm build


FROM python:3.11-slim

ARG PIP_INDEX_URL=https://pypi.org/simple
WORKDIR /opt/vue-fastapi-admin

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc python3-dev bash nginx vim curl procps net-tools \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i ${PIP_INDEX_URL}

COPY . .
COPY --from=web /opt/vue-fastapi-admin/web/dist /opt/vue-fastapi-admin/web/dist
ADD /deploy/web.conf /etc/nginx/sites-available/web.conf
RUN rm -f /etc/nginx/sites-enabled/default \
    && ln -s /etc/nginx/sites-available/web.conf /etc/nginx/sites-enabled/

ENV LANG=C.UTF-8
EXPOSE 80

ENTRYPOINT [ "sh", "deploy/entrypoint.sh" ]