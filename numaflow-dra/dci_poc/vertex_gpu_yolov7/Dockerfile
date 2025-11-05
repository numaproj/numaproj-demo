####################################################################################################
# builder: install needed dependencies
####################################################################################################

FROM pytorch/pytorch:2.5.0-cuda12.4-cudnn9-devel AS builder

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

ENV VERTEX_PATH="dci_poc/vertex_gpu_yolov7"
ENV EXAMPLE_PATH="$PYSETUP_PATH/$VERTEX_PATH"
ENV VENV_PATH="$EXAMPLE_PATH/.venv"
ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

COPY ./$VERTEX_PATH/apt-packages.txt ./
RUN export $(grep -vE '^\s*#|^\s*$' repo.env | sed 's/\s*#.*$//') && \
    ln -fs /usr/share/zoneinfo/Asia/Tokyo /etc/localtime && \
    echo "$TIME_AREA/$TIME_ZONE" > /etc/timezone && \
    apt-get update && \
    echo "tzdata tzdata/Areas select $TIME_AREA" | debconf-set-selections && \
    echo "tzdata tzdata/Zones/$TIME_AREA select $TIME_ZONE" | debconf-set-selections && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y $(grep -vE '^\s*#|^\s*$' apt-packages.txt)  \
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

ARG YOLOV7_GIT_VERSION
ARG YOLOV7_GIT_URL
ARG YOLOV7_DL_MODEL_WEIGHTS_URL

WORKDIR $PYSETUP_PATH

ENV  PYTHONPATH="$PYSETUP_PATH"
COPY ./lib/ ./lib/
COPY app.env ./
COPY $VERTEX_PATH $VERTEX_PATH

# path must be lower caharacter due to https://github.com/WongKinYiu/yolov7/blob/a207844b1ce82d204ab36d87d496728d3d2348e7/utils/google_utils.py#L19
RUN git clone -b "${YOLOV7_GIT_VERSION}" "${YOLOV7_GIT_URL}" ./ml-models/official-yolov7
RUN curl -Lf "${YOLOV7_DL_MODEL_WEIGHTS_URL}" -o ./ml-models/official-yolov7/yolov7.pt

WORKDIR $EXAMPLE_PATH
RUN poetry install --no-cache --no-root && \
    rm -rf ~/.cache/pypoetry/

RUN chmod +x entry.sh

ENTRYPOINT ["/dumb-init", "--"]
CMD ["sh", "-c", "$EXAMPLE_PATH/entry.sh"]

EXPOSE 5000