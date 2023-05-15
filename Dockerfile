########################################################################################################################
FROM python:3.11-slim AS compile-image

ARG BASE_DIR=/base
ARG USER=base
ARG GROUP=base

RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc curl

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    DOCKER_CONTAINER=1 \
    TZ=UTC

WORKDIR ${BASE_DIR}

RUN adduser --uid 1000 --home ${BASE_DIR} --disabled-password --gecos "" ${USER} \
    && chown -hR ${USER}: ${BASE_DIR}

RUN pip install "poetry"

COPY ./pyproject.toml ./poetry.lock  ${BASE_DIR}

RUN poetry config virtualenvs.in-project true && \
    poetry config virtualenvs.create true && \
    poetry install --no-interaction --no-ansi --without dev

########################################################################################################################
FROM python:3.11-slim as prod

RUN apt-get update
RUN apt-get install -y --no-install-recommends curl

ARG BASE_DIR=/app

WORKDIR ${BASE_DIR}

COPY --from=compile-image /base/.venv  ${BASE_DIR}/.venv

ENV PATH="${BASE_DIR}/.venv/bin:$PATH"

COPY ./app ${BASE_DIR}/app

COPY ./alembic.ini ./start.sh ${BASE_DIR}

RUN chmod +x ${BASE_DIR}/start.sh

CMD ["./start.sh"]
