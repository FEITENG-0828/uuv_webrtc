"""
实时视频通信系统
包含WebRTC核心功能、信令服务和计算机视觉集成

版本: 1.0.0
模块组成：
- video_stream_receiver: 视频流接收
- rtc_server/rtc_client: WebRTC连接管理
- sdp_server: 信令服务
- cv_capture: 视频采集处理
"""

__version__ = "1.0.0"
__all__ = [
    "get_host_ip",
    "CvCapture",
    "RtcServer",
    "RtcClient",
    "logger"
]

from .utils import get_host_ip
from .cv_capture import CvCapture
from .rtc_server import RtcServer
from .rtc_client import RtcClient

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
logger.handlers[0].setFormatter(logging.Formatter("[%(asctime)s][%(name)s][%(levelname)s] %(message)s"))
