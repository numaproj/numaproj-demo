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

    # Required modules (at least):
    # - opencv_contrib (OPENCV_EXTRA_MODULES_PATH)
    # - BUILD_opencv_python3
    # - BUILD_opencv_core
    # - BUILD_opencv_cudev
    # Configure, build, and install OpenCV with CUDA
    cmake \
        -D CMAKE_BUILD_TYPE=RELEASE \
        -D OPENCV_EXTRA_MODULES_PATH=../opencv_contrib/modules \
        -D CMAKE_INSTALL_PREFIX=../.local \
        -D BUILD_opencv_apps=OFF \
        -D BUILD_opencv_python2=OFF \
        -D BUILD_opencv_python3=ON \
        -D BUILD_opencv_aruco=OFF \
        -D BUILD_opencv_bgsegm=OFF \
        -D BUILD_opencv_bioinspired=OFF \
        -D BUILD_opencv_calib3d=OFF \
        -D BUILD_opencv_ccalib=OFF \
        -D BUILD_opencv_cudabgsegm=OFF \
        -D BUILD_opencv_cudafeatures2d=OFF \
        -D BUILD_opencv_cudaobjdetect=OFF \
        -D BUILD_opencv_cudaoptflow=OFF \
        -D BUILD_opencv_cudastereo=OFF \
        -D BUILD_opencv_datasets=OFF \
        -D BUILD_opencv_dnn=OFF \
        -D BUILD_opencv_dnn_objdetect=OFF \
        -D BUILD_opencv_dnn_superres=OFF \
        -D BUILD_opencv_dpm=OFF \
        -D BUILD_opencv_face=OFF \
        -D BUILD_opencv_features2d=OFF \
        -D BUILD_opencv_flann=OFF \
        -D BUILD_opencv_fuzzy=OFF \
        -D BUILD_opencv_gapi=OFF \
        -D BUILD_opencv_hfs=OFF \
        -D BUILD_opencv_highgui=OFF \
        -D BUILD_opencv_img_hash=OFF \
        -D BUILD_opencv_intensity_transform=OFF \
        -D BUILD_opencv_line_descriptor=OFF \
        -D BUILD_opencv_mcc=OFF \
        -D BUILD_opencv_ml=OFF \
        -D BUILD_opencv_objdetect=OFF \
        -D BUILD_opencv_optflow=OFF \
        -D BUILD_opencv_phase_unwrapping=OFF \
        -D BUILD_opencv_plot=OFF \
        -D BUILD_opencv_quality=OFF \
        -D BUILD_opencv_rapid=OFF \
        -D BUILD_opencv_reg=OFF \
        -D BUILD_opencv_rgbd=OFF \
        -D BUILD_opencv_saliency=OFF \
        -D BUILD_opencv_shape=OFF \
        -D BUILD_opencv_signal=OFF \
        -D BUILD_opencv_stereo=OFF \
        -D BUILD_opencv_stitching=OFF \
        -D BUILD_opencv_structured_light=OFF \
        -D BUILD_opencv_superres=OFF \
        -D BUILD_opencv_surface_matching=OFF \
        -D BUILD_opencv_text=OFF \
        -D BUILD_opencv_tracking=OFF \
        -D BUILD_opencv_videostab=OFF \
        -D BUILD_opencv_wechat_qrcode=OFF \
        -D BUILD_opencv_xfeatures2d=OFF \
        -D BUILD_opencv_ximgproc=OFF \
        -D BUILD_opencv_xobjdetect=OFF \
        -D BUILD_opencv_xphoto=OFF \
        -D BUILD_TESTS=OFF \
        -D BUILD_PERF_TESTS=OFF \
        -D BUILD_EXAMPLES=OFF \
        -D WITH_CUDA=ON \
        -D CUDA_FAST_MATH=ON \
        -D WITH_CUDNN=OFF \
        -D WITH_NVCUVID=OFF \
        -D WITH_NVCUVENC=OFF \
        -D WITH_FFMPEG=OFF \
        -D WITH_OPENCL=OFF \
        -S ../opencv \
        -B .
    make -j install
}

main "$@"
