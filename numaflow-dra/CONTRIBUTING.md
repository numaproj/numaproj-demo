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

numaflow-dra has two kinds of tests in the `tests` directory: (1) unit tests for `dci_poc/vertex` and (2) integration tests. Note that there is no unit test for `dci_poc/vertex_gpu` yet. Also note that the integration test requires test data.

How to prepare and run the tests is as follows.

## All tests

### Prepare repo.env

See [README.md](README.md).

## Unit tests for dci_poc/vertex

### Prepare video file

- when you test that source vertex receive data from video-streaming-server, you should locate video file in /tmp/poc_movie_test.mp4
- launch_ffmpeg_and_wait_ready() stream video from it

### Install dependencies

```
$ cd dci_poc/vertex
$ make test-setup
```

### Run unit tests all at once

```
$ cd dci_poc/vertex
$ make test-ut
```

### Run each unit test individually

Give APP as follows, where APP is in `tests/dci_poc/APP`.

```
$ cd dci_poc/vertex
$ APP=filter_resize_stream make test-exe
```


## integration tests

### Extract a 4K video frame for test data

Browse [this page](https://www.pexels.com/video/a-busy-downtown-intersection-6896028/), select &quot;4K UHD 3840x2160&quot;, and download the video as `6896028-uhd_3840_2160_30fps.mp4` onto the root directory.

Then extract the first frame of the video with ffmpeg as follows:

```
$ sudo apt-get -y install ffmpeg
$ ffmpeg -i 6896028-uhd_3840_2160_30fps.mp4 -frames 1 %04d.png
```

Now you will have `0001.png` on the root directory.

### Clone pytorch-YOLOv4 and download weights

On the root directory, run:

```
$ . ./repo.env
$ git clone -b $YOLOV4_GIT_VERSION $YOLOV4_GIT_URL ml-models/pytorch-YOLOv4
$ curl -sSLo ./ml-models/pytorch-YOLOv4/yolov4.conv137.pth $YOLOV4_DL_MODEL_WEIGHTS_URL
$ curl -sSLo ./ml-models/pytorch-YOLOv4/yolov4.pth $YOLOV4_DL_MODEL_URL
```

### Make the log directory

```
$ sudo mkdir -m 777 -p /var/tmp/logs/numaflow-dra/tests/dci_poc
```

### Install dependencies

```
$ cd dci_poc
$ make test-setup
```

### Run integration tests
Set SOURCE_INPUT to file in app.env and then run

Set `SOURCE_INPUT` to `file` in app.env and then run

```
$ cd dci_poc
$ make test-it
```
