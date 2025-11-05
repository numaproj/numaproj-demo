The purpose of this repository is verifying the integration of Numaflow and DRA.
In our plan, we commit this repo to numaproj-demo

# Architecture of DCI PoC Pipeline
![Architecture of DCI PoC Pipeline](/docs/assets/DCI_PoC_architecture.svg)

| Component | Role |
| :- | :- |
| NAS | Hosts video files encoded in H.264. (Note that as long as the files can be placed, it doesn't have to be a NAS.) |
| Video Streaming Server | Reads an input video file on the NAS, then serves it to the Source via RTSP. |
| Source | Provides input video frames for the pipeline in one of the following way: (1) Receives the input video from the Video Streaming Server via RTSP; or (2) Reads the input video file on the NAS directly. |
| Filter Resize (F/R) | Resizes the input frames from the Source as preprocessing, then sends them to the Inference. |
| Inference | Performs object detection on the frames using YOLOv4 or YOLOv7 with GPU, then sends both the original (received) frames and the detected bounding-box information to the Sink. |
| Sink | Draws bounding boxes on the frames, then sends them to the Video Display Server via HTTP. |
| Video Display Server | Serves the output video frames from the Sink to the client via HTTP. |

## Note: About the inference model being used in Inference Vertex
- In this PoC, the inference vertex uses [Tianxiaomo/pytorch-YOLOv4](https://github.com/Tianxiaomo/pytorch-YOLOv4?tab=readme-ov-file#02-pytorch) and [WongKinYiu/yolov7](https://github.com/WongKinYiu/yolov7) to detect objects appearing in the frames.
- The code is obtained through the following steps and is not redistributed in this repository.

# 1. Prerequisites
- (Requirements) You need to set up a following environment
   - A Kubernetes cluster with a GPU on a worker node
   - GPU support enabled in the Kubernetes cluster
   - Dyanamic Resource Allocation(DRA) enabled in the Kubernetes cluster
   - Numaflow installed in k8s cluster

- You can refer to [Note: Environment used for verifying](#note-environment-used-for-verifying) for imformation about the environment we used.

## 1-1. Set up Kubernetes Cluster
- Refer to [Bootstrapping clusters with kubeadm](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/) and set up a k8s cluster with GPU on worker nodes

## 1-2. Enable GPU support
### Install nvidia driver
```
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt update && sudo ubuntu-drivers autoinstall
sudo apt list --installed | grep nvidia-driver
sudo reboot
```

```
nvidia-smi
```

### Enable MPS daemon(Optional)
```
echo -e "\nexport CUDA_DEVICE_ORDER=\"PCI_BUS_ID\"\nexport CUDA_VISIBLE_DEVICES=0,1\nexport CUDA_MPS_PIPE_DIRECTORY=/tmp/nvidia-mps\nexport CUDA_MPS_LOG_DIRECTORY=/tmp/nvidia-mps"
 | sudo tee -a /root/.bashrc > /dev/null
```

```
sudo -s
nvidia-cuda-mps-control -d
exit
```

### Install NVIDIA Container Toolkit

- Install NVIDIA Container Toolkit to refer to [this page](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
  - Don't need to configure

## 1-3. Enable Dynamic Resource Allocation
- You refer to [k8s-dra-driver-gpu](https://github.com/NVIDIA/k8s-dra-driver-gpu) and [Enabling dynamic resource allocation](https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/#enabling-dynamic-resource-allocation), and then enable DRA in your Kubernetes cluster.

## 1-4. Set up Numaflow

- The following procedure is prepared based on [official quick-start](https://numaflow.numaproj.io/quick-start/#installing-numaflow) and use `local-storage` as `StorageClass`

```
git clone git@github.com:numaproj/numaflow.git
kubectl create ns numaflow-system
kubectl apply -n numaflow-system -f https://raw.githubusercontent.com/numaproj/numaflow/main/config/install.yaml
```

```
kubectl apply -f ./config_yaml/local-storage.yaml
chmod +x ./config_yaml/PVs.sh
./config/PVs.sh
kubectl apply -f ./config_yaml/inter-step-buffer-service.yaml
```

# 2. QuickStart
## 2-1. Install tools to operate the repository
### 2-1-1. pipx, Poetry
- This project uses Poetry for dependency management, building a container that will be used in a pod forming the pipeline.
- Follow [the pipx official installtion instructions](https://pipx.pypa.io/stable/installation/).
- Follow ["With pipx" section in the Poetry official installation instructions](https://python-poetry.org/docs/#installing-with-pipx).
- `source ~/.bashrc`

### 2-1-2. Install docker
- Since use docker to build container, install docker by referring to [this page](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository)
- `sudo usermod -aG docker $(whoami)`
- `newgrp docker`
- `docker ps`

## 2-2. Configure .env files from template files

```
cd /path/to/numaflow-dra
cp app.env.template app.env
cp repo.env.template repo.env
```
- Set your timezone for `TIME_AREA` and `TIME_ZONE` in repo.env
- Other keys will be supported in a later process

## 2-3. Set up input data
An input data is an .mp4 file (4K (3840*2160), 15fps). You download a video from a free website and convert it using tools such as ffmpeg.

Please make use of the following websites:
- https://www.pexels.com/ja-jp/videos/
- https://pixabay.com/ja/videos/

Note that the videos on these sites are not for distribution. Please check the licenses before using them.

- we recommend these movies, [movie1](https://www.pexels.com/video/a-busy-downtown-intersection-6896028/) or [movie2](https://pixabay.com/ja/videos/%E3%83%AA%E3%83%90%E3%83%97%E3%83%BC%E3%83%AB-%E6%A9%8B%E8%84%9A-%E9%A0%AD-46098/)
- Check the data format of the video, e.g., resolution, frame rate, and that it is encoded in H.264.
- Convert the movie to 4K, 15fps, h264 encoded data format
```
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate -of json movie.mp4
ffmpeg -i movie.mp4 -vf "scale=3840:2160" -r 15 -c:v libx264 -preset slow -crf 23 -pix_fmt yuv420p poc_movie.mp4
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate -of json poc_movie.mp4
```

## 2-4. Set up your container registry

- Set up container registry that you can access personally, such as Docker Hub

```
cd /path/to/numaflow-dra
```

- Set `REGISTRY_URL` appropriately in the `repo.env` file.

## 2-5. Make a log directory

- make log dir on worker node to record Vertex execution logs
```
$ sudo mkdir -m 777 -p /var/tmp/logs/numaflow-dra/dci_poc
```

## 2-6. Generate pipeline.yml

```
cd /path/to/numaflow-dra
./generate_pipeline_yaml.sh
```

- When `generate_pipeline_yaml.sh` is executed, `pipelineXXX.yaml` with `REGISTRY_URL` configured is created in each `pipelineXXX.yaml.template` in various locations

## 2-7. Configure pipelines to read input file directly
- Set the path where the video is located for `VIDEO_FILE_SRC` in `/path/to/numaflow-dra/app.env`.
  Also, set `SOURCE_INPUT_TYPE` in `/path/to/numaflow-dra/app.env` to `file`.

## 2-8. Build Container & Push it to your Registry

```
cd numaflow-dra/dci_poc/XXX/
make image
```

## 2-9. Start a Video Display Server
- Set `RECEIVER_URL` appropriately in the `app.env` file.

```
cd /path/to/numaflow-dra/video-receive-server
make start-receiver
```

## 2-10. Deploy pipelines
- Select a pattern you want to deploy

- pattern1:
  - `kubectl apply -f config_yaml/dra-t4.yml`
  - `kubectl apply -f dci_poc/pipeline1.yml`

- pattern2:
  - `kubectl apply -f config_yaml/dra-a100.yml`
  - `kubectl apply -f dci_poc/pipeline2.yml`

- pattern3:
  - `kubectl apply -f config_yaml/dra-a100.yml`
  - `kubectl apply -f dci_poc/pipeline3.yml`

- FYI: For details, see [demo/README.md](./demo/README.md).
  - demo1: switch between pattern1 and pattern2
    - By switching the deployment pipeline, you can easily change an accelerator used in the pipeline.
  - demo2: switch between pattern2 and pattern3
    - When you update an ML inference model using Kubeflow, you can easily update the ML model used in the pipeline.
  

That's all.

# Note: Environment used for verifying
- k8s cluster: 1 control plane, 2 data Plane
  - Control: T4
  - Data 1: GPU A100
  - Data 2: L4, T4
- We used baremetal servers to build k8s cluster
- You needn't to prepare 2 Worker. It is sufficient if one worker has a GPU.
- Both video-display-server and video-streaming-server will be started on the control plane

- QuickStart
  - One GPU is required on the data plane.
  - The GPU type does not matter as long as it is compatible with DynamicResourceAllocation
    - However, we currently provide configurations only for T4 and A100, so you need to prepare a manifest file that matches the GPU type you are using.

- Demo
  - Two types of GPUs are used on the data plane, but since each pipeline uses only one GPU, this does not cause any operational issues.
  - Having a GPU on the C-plane allows for clearer video display.

| | Control Plane | Data Plane |
| - | - | - |
| Ubuntu  | 24.04.3 LTS | Same as left |
| kubeadm | 1.33.2 | Same as left |
| kubelet | 1.33.2 | Same as left |
| kubectl | 1.33.2 | Same as left |
| CRI-O   | 1.33.2 | Same as left |
| Calico  | 3.30.1 | Same as left |
| NVIDIA GPU Driver | - | 575.64.03-0ubuntu0.24.04.1 |
| Numaflow | 1.6.0 | - |
| MediaMTX | 1.14.0 | - |

# LICENCE

This project is licensed under the Apache License 2.0，but but includes portions of code that are licensed under the MIT License as listed below.
- video-streaming-server/mediamtx/
