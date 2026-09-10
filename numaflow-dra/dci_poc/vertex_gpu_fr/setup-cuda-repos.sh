#!/bin/bash
export LANG=C LC_ALL=C
set -Cxueo pipefail

main() {
  # Assume that we are on Ubuntu 24.04
  if ! . /etc/os-release ; then
    exit 1
  fi
  if [ "${VERSION_ID:-}" != 24.04 ] ; then
    exit 1
  fi

  # Required for downloading cuda-keyring
  sudo apt update
  sudo apt install -y curl

  # See https://developer.nvidia.com/cuda-downloads?target_os=Linux&target_arch=x86_64&Distribution=Ubuntu&target_version=24.04&target_type=deb_network
  curl -sSL -o cuda-keyring_1.1-1_all.deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
  sudo dpkg -i cuda-keyring_1.1-1_all.deb
  rm -f cuda-keyring_1.1-1_all.deb
}

main "$@"
exit 0
