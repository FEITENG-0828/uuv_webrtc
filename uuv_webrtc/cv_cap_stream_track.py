"""
视频流轨道模块
实现媒体流与计算机视觉采集的集成
"""

import asyncio
from typing import Optional
from av import VideoFrame
from aiortc import VideoStreamTrack
from aiortc.contrib.media import MediaStreamError
import logging

from .cv_capture import CvCapture

class CvCapStreamTrack(VideoStreamTrack):
    """自定义视频流轨道
    将计算机视觉采集结果转换为媒体流
    """
    
    kind = "video"
    
    def __init__(self, capture: CvCapture, logger: logging.Logger = None):
        """
        初始化视频流轨道
        
        Args:
            capture (CvCapture): 视频捕获对象
            logger (logging.Logger, optional): 日志记录器, 默认None
        """
        super().__init__()
        self.logger = logger or logging.getLogger(__name__)

        self.__capture = capture

    async def recv(self) -> Optional[VideoFrame]:
        """
        获取并转换视频帧
        
        Returns:
            VideoFrame: 转换后的视频帧对象
        """
        try:
            # 获取时间戳和时基
            timestamp, time_base = await self.next_timestamp()
            
            # 获取视频帧
            success, frame = self.__capture.getLatestFrame()
            if not success or frame is None:
                await asyncio.sleep(0.01)
                return None
            
            # 转换帧格式
            video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
            video_frame.pts = timestamp
            video_frame.time_base = time_base
            
            return video_frame
            
        except MediaStreamError as e:
            self.logger.error(f"视频流中断: {e}")
            await asyncio.sleep(0.1)
            return None
