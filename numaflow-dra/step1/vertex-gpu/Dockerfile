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

ENV EXAMPLE_PATH="$PYSETUP_PATH/step1/vertex-gpu"
ENV VENV_PATH="$EXAMPLE_PATH/.venv"
ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

COPY user-config.env ./
RUN export $(grep -v '^#' user-config.env | xargs) && \
    ln -fs /usr/share/zoneinfo/Asia/Tokyo /etc/localtime && \
    echo "$TIME_AREA/$TIME_ZONE" > /etc/timezone && \
    apt-get update && \
    echo "tzdata tzdata/Areas select $TIME_AREA" | debconf-set-selections && \
    echo "tzdata tzdata/Zones/$TIME_AREA select $TIME_ZONE" | debconf-set-selections && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
        curl \
        wget \
        # deps for building python deps
        build-essential \
        libopencv-dev \
        python3-opencv \
        libyaml-dev \
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
COPY ./ ./

RUN git clone https://github.com/Tianxiaomo/pytorch-YOLOv4.git
RUN curl "https://drive.usercontent.google.com/download?id=1fcbR0bWzYfIEdLJPzOsn4R5mlvR6IQyA&confirm=xxx" \
  -o ./pytorch-YOLOv4/yolov4.conv137.pth
RUN curl "https://drive.usercontent.google.com/download?id=1wv_LiFeCRYwtpkqREPeI13-gPELBDwuJ&confirm=xxx" \
  -o ./pytorch-YOLOv4/yolov4.pth

WORKDIR $EXAMPLE_PATH
RUN poetry install --no-cache --no-root && \
    rm -rf ~/.cache/pypoetry/

RUN chmod +x entry.sh

ENTRYPOINT ["/dumb-init", "--"]
CMD ["sh", "-c", "$EXAMPLE_PATH/entry.sh"]

EXPOSE 5000