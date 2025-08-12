The purpose of this repository is verifying the integration of Numaflow and DRA.
In our plan, we commit this repo to numaproj-demo

# Architecture of DCI PoC Pipeline
![Architecture of DCI PoC Pipeline](./docs/assets/DCI_PoC_STEP1_Archi.drawio.svg)

| Component | Role |
| :- | :- |
| NAS | - Place video files already encoded in H.264 format |
| Source | - ※Assume that a video files sent to Source Vertex is already encoded.<br>- Retrieve encoded a video file from the NAS storage location.<br>- Transmit the encoded data per one frame to the next Vertex via gRPC.<br>&emsp;- The video file must be decoded to process data on a per-frame basis(numpy.ndarray) |
| FilterResize | - Resize the frame as preprocessing for inference.<br>- Serialize the data into Python binary format and transmit it the next vertex. |
| Inference | - Deserialize the received Python binary data into frames (numpy.ndarray).<br> - Perform object detection on the frames using YOLOv4 on a GPU.<br> - Transmit the detected BoundingBox information as output via gRPC. |
| Sink | - Receive the output results from the Inference Vertex.<br> - Output the log information to the host machine via mountVolume. |
| Host Machine | - ※Sink Vertex is running in this machine.<br> - Utilize the host machine as an aggregation point for processed data. |

## Note: About the inference model being used in Inference Vertex
- In this PoC, the inference vertex uses [Tianxiaomo/pytorch-YOLOv4](https://github.com/Tianxiaomo/pytorch-YOLOv4?tab=readme-ov-file#02-pytorch) to detect objects appearing in the frames.
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

## 1-4. Setup Numaflow

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

# 2. How to Use numaflow-dra
## 2-1. Prepare .env file

```
cd /path/to/numaflow-dra
cp user-config.env.template user-config.env
```
- Set your timezone for `TIME_AREA` and `TIME_ZONE` in user-config.env

## 2-2. Prepare input_data

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

After prepare the video, set the path where the video is located for `VIDEO_SRC` in `/path/to/numaflow-dra/user-config.env`.

## 2-3. Install poetry to build container

- To deploy a pipeline, build a container that will be used in a pod forming the pipeline.
- Since poetry is used to build a container in numaflow-dra, install poetry by referring to [this page](https://python-poetry.org/docs/#installing-with-pipx)
- `source ~/.bashrc`

## 2-4. Set up your container registry

- Set up container registry that you can access personally, such as Docker Hub

```
cd /path/to/numaflow-dra
```

- Set `REGISTRY_URL` appropriately in the `user-config.env` file.

```
cd /path/to/numaflow-dra
./generate_pipeline_yaml.sh
```

- For each `pipelineXXX.yaml.template` in various locations, `pipelineXXX.yaml` with `REGISTRY_URL` configured will be created

## 2-5. Build Container & Push it to your Registry

You can choose one pipeline from following options

- step1-debug
  - `source -> filter/resize -> sink-debug`
  - This directory is for verifying that the source and filter-resize are working correctly
  - It is used when developing numaflow-dra
- step1
  - `source -> filter/resize -> inference -> sink`
  - This directory is the latest, and its use is recommended


```
cd numaflow-dra/step1/XXX/
make image
```

## 2-6. Deploy pipeline

you execute `sudo mkdir /var/log/numaflow` on worker nodes to prepare log path.

```
cd numaflow-dra/config_yaml
kubectl apply -f dra-single-gpu.yaml
```

```
cd numaflow-dra/step1
kubectl apply -f pipeline.yaml
```

That's all.

# Option

you can switch F/R with `numaflow-dra/step1/pipeline.yaml and entry.sh`

```pipeline.yaml
    - name: filter-resize
      scale:
        max: 1
      udf:
        container:
          image: [registry ip]:[port]/numaflow/step1-debug:stable
          imagePullPolicy: Always
          env:
            - name: SCRIPT
              value: "fr-stream" <- changenable
```

```entry.sh
elif [ "$SCRIPT" = "filter-resize" ]; then
    python filter-resize.py
elif [ "$SCRIPT" = "fr-stream" ]; then
    python filter-resize-stream.py
```

- `filter-resize.py` use Sync Servicer and Server.
- `filter-resize-async.py` use Async Servicer and Server.
- `filter-resize-stream.py` use Streamer Servicer and Server.

# Note: Environment used for verifying
- k8s cluster: 1 Master 2 Worker
  - Worker1: GPU A100
  - Worker2: L4, T4
- We used baremetal servers to build k8s cluster
- You needn't to prepare 2 Worker. It is sufficient if one worker has a GPU.

| | Master | Worker |
| - | - | - |
| Ubuntu | 22.04 LTS(stable) | as above |
| kubeadm | 1.31.3(stable) | as above |
| kubelet | 1.31.3(stable) | as above |
| kubectl | 1.31.3(stable) | as above |
| CRI-O | 1.31.2(stable) | as above |
| Calico | 3.28.1(stable) | as above |
| NVIDIA GPU Driver | - | 560.35.03-0ubuntu0~gpu22.04.4 |
