ARG PYTHON_IMAGE=python:3.11-slim

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

ENTRYPOINT ["sh", "deploy/entrypoint.sh"]
