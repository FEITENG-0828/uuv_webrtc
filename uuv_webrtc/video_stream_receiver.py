"""
视频流接收器模块
实现基于WebRTC的视频流接收功能，处理媒体传输和编解码
"""

import numpy as np
import threading
import asyncio
from typing import Optional, Tuple
import logging

from aiortc import VideoStreamTrack
from aiortc.contrib.media import MediaStreamError

class VideoStreamReceiver:
    """
    WebRTC视频流接收器类
    负责建立连接并接收媒体流
    """
    
    def __init__(self, frame_size: Tuple[int, int] = (1280, 720), logger: logging.Logger = None):
        """
        初始化视频流接收器

        Args:
            frame_size (Tuple[int, int], optional): 视频帧的分辨率, 默认(1280, 720)
            logger (logging.Logger, optional): 日志记录器, 默认None
        """
        self.logger = logger or logging.getLogger(__name__)

        self.__track: Optional[VideoStreamTrack] = None
        self.__task: Optional[asyncio.Task] = None
        self.__frame_lock = threading.Lock()
        self.__latest_frame: np.ndarray = np.zeros((frame_size[1], frame_size[0], 3), dtype=np.uint8)

    def __cancelCurrentTask(self) -> None:
        """
        取消当前任务
        """
        if self.__task and not self.__task.done():
            self.__task.cancel()

    def addTrack(self, track: VideoStreamTrack) -> None:
        """
        注册视频轨道
        
        Args:
            track (VideoStreamTrack): 视频轨道对象
        """
        if track.kind == "video":
            self.__cancelCurrentTask()
            self.__track = track
            self.__task = None

    async def start(self) -> None:
        """
        开始接收
        """
        if self.__track is not None and self.__task is None:
            self.__task = asyncio.create_task(self.__processFrames())

    async def stop(self) -> None:
        """
        停止接收
        """
        self.__cancelCurrentTask()
        self.__track = None

    async def __processFrames(self) -> None:
        """
        持续处理视频帧
        """
        while self.__track:
            try:
                frame = await self.__track.recv()
                with self.__frame_lock:
                    self.__latest_frame = frame.to_ndarray(format="bgr24")

            except MediaStreamError as e:
                self.logger.error(f"视频流中断: {e}")
                break

    def getLatestFrame(self) -> Tuple[bool, np.ndarray]:
        """
        获取最新帧

        Returns:
            Tuple[bool, np.ndarray]: 最新帧状态和帧数据
                - bool: 是否获取成功
                - np.ndarray: 视频帧（BGR格式）
        """
        with self.__frame_lock:
            return self.__latest_frame is not None, self.__latest_frame.copy()
