"""
计算机视觉采集模块
实现视频采集和帧处理功能
"""

import cv2
import threading
import time
import numpy as np
from typing import Tuple
import logging

class CvCapture:
    """视频采集器类
    封装OpenCV视频采集功能
    """
    
    def __init__(
        self,
        cam: int = 0,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        logger: logging.Logger = None
    ) -> None:
        """
        初始化视频捕获设备
        
        Args:
            cam: 摄像头设备ID
            width: 捕获宽度
            height: 捕获高度
            fps: 目标帧率
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger(__name__)

        self.__cam_id = cam
        self.__target_size = (width, height)
        self.__target_fps = fps
        
        # 视频流参数
        self.__ret = False
        self.__latest_frame: np.ndarray = np.zeros((height, width, 3), dtype=np.uint8)
        self.__frame_lock = threading.Lock()
        self.__running = threading.Event()
        self.__running.set()
        
        # 启动捕获线程
        self.__capture_thread = threading.Thread(
            target=self.__capture_loop,
            name="CV_Capture_Thread",
            daemon=True
        )
        self.__capture_thread.start()
        
        # 等待初始化完成
        if not self.__wait_for_camera():
            self.logger.error("摄像头初始化失败")
            raise RuntimeError("摄像头初始化失败")

    def __init_camera(self) -> cv2.VideoCapture:
        """
        初始化摄像头设备
        
        Returns:
            cv2.VideoCapture: 初始化后的摄像头对象
        """
        cap = cv2.VideoCapture(self.__cam_id)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            cap.set(cv2.CAP_PROP_FPS, self.__target_fps)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.__target_size[0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.__target_size[1])
        return cap

    def __capture_loop(self) -> None:
        """
        视频采集主循环
        """
        while self.__running.is_set():
            cap = self.__init_camera()
            if not cap.isOpened():
                self.logger.warning(f"无法打开摄像头 {self.__cam_id}，5秒后重试...")
                time.sleep(5)
                continue

            while self.__running.is_set():
                success, frame = cap.read()
                if not success:
                    self.logger.warning("视频帧获取失败，尝试重新初始化...")
                    break
                
                with self.__frame_lock:
                    self.__ret = True
                    self.__latest_frame = frame

            cap.release()
            time.sleep(1)  # 防止频繁重试

    def __wait_for_camera(self, timeout: float = 5.0) -> bool:
        """
        等待摄像头准备就绪
        
        Args:
            timeout (float, optional): 等待超时时间，默认5秒
            
        Returns:
            bool: 摄像头是否就绪
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self.__frame_lock:
                if self.__latest_frame is not None:
                    self.logger.info(f"摄像头 {self.__cam_id} 已就绪 | 分辨率：{self.__target_size}")
                    return True
            time.sleep(0.1)
        self.logger.warning("摄像头初始化超时")
        return False

    def get_frame_size(self) -> Tuple[int, int]:
        """
        获取当前分辨率
        
        Returns:
            Tuple[int, int]: 分辨率 (width, height)
        """
        return self.__target_size

    def get_latest_frame(self) -> Tuple[bool, np.ndarray]:
        """
        获取最新的视频帧
        
        Returns:
            Tuple[bool, np.ndarray]: 
                - bool: 是否获取成功
                - np.ndarray: 视频帧（BGR格式）
        """
        with self.__frame_lock:
            return (self.__ret, self.__latest_frame.copy())

    def close(self) -> None:
        """
        安全关闭摄像头
        """
        self.__running.clear()
        if self.__capture_thread.is_alive():
            self.__capture_thread.join(timeout=2)

    def __del__(self):
        """
        确保资源释放
        """
        self.close()
