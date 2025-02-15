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
    
    def __init__(self, logger: logging.Logger = None):
        """
        初始化视频流接收器
        """
        self.logger = logger or logging.getLogger(__name__)

        self._track: Optional[VideoStreamTrack] = None
        self._task: Optional[asyncio.Task] = None
        self._frame_lock = threading.Lock()
        self._latest_frame: np.ndarray = np.zeros((720, 1280, 3), dtype=np.uint8) # FIXME: 需要根据实际分辨率修改

    def _cancel_current_task(self) -> None:
        """
        取消当前任务
        """
        if self._task and not self._task.done():
            self._task.cancel()

    def add_track(self, track: VideoStreamTrack) -> None:
        """
        注册视频轨道
        
        Args:
            track: 视频轨道对象
        """
        if track.kind == "video":
            self._cancel_current_task()
            self._track = track
            self._task = None

    async def start(self) -> None:
        """
        开始接收
        """
        if self._track is not None and self._task is None:
            self._task = asyncio.create_task(self._process_frames())

    async def stop(self) -> None:
        """
        停止接收
        """
        self._cancel_current_task()
        self._track = None

    async def _process_frames(self) -> None:
        """
        持续处理视频帧
        """
        while self._track:
            try:
                frame = await self._track.recv()
                with self._frame_lock:
                    self._latest_frame = frame.to_ndarray(format="bgr24")

            except MediaStreamError as e:
                self.logger.error(f"视频流中断: {e}")
                break

    def get_latest_frame(self) -> Tuple[bool, np.ndarray]:
        """
        获取最新帧

        Returns:
            Tuple[bool, np.ndarray]: 最新帧状态和帧数据
        """
        with self._frame_lock:
            return self._latest_frame is not None, self._latest_frame.copy()
