#!/bin/bash
export LC_ALL=C
set -xueo pipefail

deactivate_venv() {
    local venv
    venv="$(dirname "$(which python3)")"
    if [ -x "${venv}/deactivate" ] ; then
        "${venv}/deactivate"
    fi
}

main() {
    # Get the path to the directory that contains this script
    local bin
    bin="$(realpath "$(dirname "${BASH_SOURCE[0]}")")"

    # Inside /opencv-cuda/build -----------------------------------------------
    mkdir -p "${bin}/build"
    cd "${bin}/build"

    # Activate virtualenv of /dci_poc/vertex that will use OpenCV with CUDA
    deactivate_venv
    eval $(poetry -P ../../dci_poc/vertex env activate)

    # Configure, build, and install OpenCV with CUDA
    cmake \
        -D CMAKE_BUILD_TYPE=RELEASE \
        -D OPENCV_EXTRA_MODULES_PATH=../opencv_contrib/modules \
        -D CMAKE_INSTALL_PREFIX=../.local \
        -D BUILD_opencv_apps=OFF \
        -D BUILD_opencv_python2=OFF \
        -D BUILD_opencv_python3=ON \
        -D BUILD_TESTS=OFF \
        -D BUILD_PERF_TESTS=OFF \
        -D BUILD_EXAMPLES=OFF \
        -D WITH_CUDA=ON \
        -D CUDA_FAST_MATH=ON \
        -D WITH_CUDNN=OFF \
        -D WITH_NVCUVID=OFF \
        -D WITH_NVCUVENC=OFF \
        ../opencv
    make -j install
}

main "$@"
