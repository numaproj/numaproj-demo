####################################################################################################
# builder: install needed dependencies
####################################################################################################

FROM python:3.12-slim-bookworm AS builder

ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=on \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_VERSION=1.8.2 \
  POETRY_HOME="/opt/poetry" \
  POETRY_VIRTUALENVS_IN_PROJECT=true \
  POETRY_NO_INTERACTION=1 \
  PYSETUP_PATH="/opt/pysetup"

ENV VERTEX_PATH="dci_poc/vertex"
ENV EXAMPLE_PATH="$PYSETUP_PATH/$VERTEX_PATH"
ENV VENV_PATH="$EXAMPLE_PATH/.venv"
ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

COPY ./$VERTEX_PATH/apt-packages.txt ./
RUN apt-get update \
    && apt-get install --no-install-recommends -y $(grep -vE '^\s*#|^\s*$' apt-packages.txt | sed 's/\s*#.*$//') \
    && apt-get install -y git \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    \
    # install dumb-init
    && wget -O /dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.5/dumb-init_1.2.5_x86_64 \
    && chmod +x /dumb-init \
    && curl -sSL https://install.python-poetry.org | python3 - 

####################################################################################################
# udf: used for running the udf vertices
####################################################################################################
FROM builder AS udf

WORKDIR $PYSETUP_PATH

ENV  PYTHONPATH="$PYSETUP_PATH"
COPY ./lib/ ./lib/
COPY app.env ./
COPY $VERTEX_PATH $VERTEX_PATH

WORKDIR $EXAMPLE_PATH
RUN poetry install --no-cache --no-root && \
    rm -rf ~/.cache/pypoetry/

RUN chmod +x entry.sh

ENTRYPOINT ["/dumb-init", "--"]
CMD ["sh", "-c", "$EXAMPLE_PATH/entry.sh"]

EXPOSE 5000