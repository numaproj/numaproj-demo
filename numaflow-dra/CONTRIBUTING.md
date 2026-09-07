# Code formatter and linter

We use [Ruff](https://docs.astral.sh/ruff/) to both format and lint codes. You first need to install dependencies on the project root as follows:

```
poetry install --with dev
```

Then run:

```
make lint
```

If you don't need auto-fix, run instead:

```
make check-lint
```

Note that `lint`/`check-lint` targets includes both formatting and linting. If you only need formating, use `format`/`check-format` targets instead.

# Testing

numaflow-dra has unit tests under `tests/dci_poc`, there are separate directories corresponding to each vertex directory in `dci_poc/`.

How to prepare and run the tests is as follows.

## Prepare repo.env

See [README.md](README.md).

## Install dependencies and download test data

(The commands described below are for testing of `dci_poc/vertex`. You have to replace the path with `dci_poc/vertex_gpu_fr`, `dci_poc/vertex_gpu_yolov4`, or `dci_poc/vertex_gpu_yolov7` when you want to do testing for each of them.)

```
$ cd dci_poc/vertex
$ make setup
```

This command also downloads test data. The unit tests use the following files as test data:

|test target|input file|
|-|-|
|`dci_poc/vertex`|`video-streaming-server/mediamtx/poc_movie_test.mp4`<br>・In CI, This mp4file  is not downloaded. Instead, it's copied from a pre-downloaded file located at `vars.PATH_PRE_DOWNLOADED_VIDEO`|
|`dci_poc/vertex_gpu_yolov4`|`ml-models/pytorch-YOLOv4/data/dog.jpg`<br>This JPEG file is located in the downloaded model directory.|
|`dci_poc/vertex_gpu_yolov7`|`ml-models/official-yolov7/deploy/triton-inference-server/data/dog.jpg`<br>This JPEG file is located in the downloaded model directory.|

## Run unit tests

```
$ cd dci_poc/vertex
$ make test
```

# Development

## Color conversion in pipeline

Being compliant to OpenCV, each video frame should be read in BGR (not RGB) order in every vertex. Color should be reordered if necessary. Especially note that both of YOLOv4 and YOLOv7 take an image in RGB (not BGR) order.
