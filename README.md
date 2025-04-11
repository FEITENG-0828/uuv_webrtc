# UUV WebRTC 视频传输系统

用于UUV的实时视频传输系统，基于WebRTC协议实现较低延迟视频流传输

## 主要功能

- 实时摄像头采集与编码
- WebRTC点对点视频传输
- 可配置的视频参数调整

## 快速开始

### 安装
```bash
pip install -r requirements.txt
```

> **注意：**
> - 本项目仅在`Python 3.10.8`,`Python 3.11.0`,`Python 3.12.3`进行测试可以正常运行，但不保证其他Python版本有效
> - 打包上传后使用`pip install uuv_webrtc`安装时采用了严格版本依赖

### 测试
1. 启动服务器：
```bash
python test/server.py
```

2. 启动客户端（新终端）：
```bash
python test/client.py
```

## 核心模块

### 1. 视频采集模块
- `cv_capture.py`：摄像头驱动与帧捕获
- `cv_cap_stream_track.py`：视频流封装

### 2. 传输模块
- `rtc_client.py`：客户端连接管理
- `rtc_server.py`：服务端连接管理
- `sdp_server.py`：SDP信令交换

### 3. 接收模块
- `video_stream_receiver.py`：视频流解码与显示

## 许可证
MIT License

## 版权
Copyright © 2025 [FEITENG](https://github.com/FEITENG-0828), All rights reserved
