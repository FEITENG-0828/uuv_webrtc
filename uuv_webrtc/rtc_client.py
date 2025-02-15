"""
WebRTC客户端模块
实现客户端连接和媒体处理逻辑
"""

import asyncio
import socket
import json
import threading
import numpy as np
import logging

from aiortc import RTCPeerConnection, RTCSessionDescription

from .video_stream_receiver import VideoStreamReceiver
from .utils import get_host_ip

class RtcClient:
    """
    WebRTC客户端类
    实现客户端连接和媒体处理逻辑
    """

    def __init__(
        self,
        local_port: int = 20001,
        server_address: tuple[str, int] = ("127.0.0.1", 20000),
        logger: logging.Logger = None,
    ) -> None:
        """
        初始化WebRTC客户端
        
        Args:
            local_port (int, optional): 本地端口, 默认20001
            server_address (tuple[str, int], optional): 服务器地址和端口, 默认("127.0.0.1", 20000)
            logger (logging.Logger, optional): 日志记录器, 默认None
        """
        self.logger = logger or logging.getLogger(__name__)

        # 网络配置
        self.__local_address = (get_host_ip(), local_port)
        self.__server_address = server_address
        self.__udp_socket = self.__init_udp_socket()

        self.__video_stream_receiver = VideoStreamReceiver(self.logger)
        self.__pc = self.__init_peer_connection()
        
        # 异步事件循环管理
        self.__loop = asyncio.new_event_loop()
        self.__client_task = self.__loop.create_task(self.__run_client())
        self.__event_loop_thread = threading.Thread(
            target=self.__start_event_loop, 
            daemon=True
        )
        self.__event_loop_thread.start()
        self.logger.info("客户端初始化完成")

    def __start_event_loop(self):
        """
        启动事件循环
        """
        asyncio.set_event_loop(self.__loop)
        try:
            self.__loop.run_forever()
        finally:
            self.__loop.close()

    def __init_udp_socket(self) -> socket.socket:
        """
        初始化UDP socket

        Returns:
            socket.socket: 初始化后的UDP socket对象
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(self.__local_address)
        self.logger.info(f"UDP socket已启动 | 地址: {self.__local_address[0]}:{self.__local_address[1]}")
        return sock

    def __init_peer_connection(self) -> RTCPeerConnection:
        """
        初始化WebRTC对等连接

        Returns:
            RTCPeerConnection: 初始化后的对等连接对象
        """
        pc = RTCPeerConnection()
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            """
            连接状态变更处理
            """
            state = pc.connectionState
            self.logger.info(f"连接状态变更: {state}")
            if state in ["failed", "closed"]:
                await self.__video_stream_receiver.stop()
                
        @pc.on("track")
        def on_track(track):
            """
            收到视频流处理
            """
            self.logger.info(f"收到视频流: {track.kind}")
            self.__video_stream_receiver.add_track(track)
            
        return pc

    async def __exchange_sdp(self) -> RTCSessionDescription:
        """
        处理SDP交换流程

        Returns:
            RTCSessionDescription: 交换后的SDP描述
        """
        while True:
            try:
                self.__udp_socket.sendto(b"ask_offer", self.__server_address)
                self.__udp_socket.settimeout(1)
                offer_data, _ = self.__udp_socket.recvfrom(4096)
                
                offer = json.loads(offer_data.decode())
                if offer.get("type") == "offer":
                    return RTCSessionDescription(sdp=offer["sdp"], type="offer")
                    
                self.logger.warning("收到无效的Offer类型")
                await asyncio.sleep(1)
                
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.error(f"SDP解析失败: {e}")
            except OSError as e:
                self.logger.error(f"网络错误: {e}")
                await asyncio.sleep(1)

    async def __start_heartbeat(self):
        """
        维持心跳连接
        """
        while True:
            try:
                self.__udp_socket.sendto(b"heart_beat", self.__server_address)
                await asyncio.sleep(1)
            except OSError as e:
                self.logger.error(f"心跳发送失败: {e}")
                break

    async def __run_client(self):
        """
        主客户端逻辑
        """
        try:
            # SDP协商
            offer = await self.__exchange_sdp()
            await self.__pc.setRemoteDescription(offer)
            
            # 创建应答
            answer = await self.__pc.createAnswer()
            await self.__pc.setLocalDescription(answer)
            self.__udp_socket.sendto(
                json.dumps({"type": "answer", "sdp": answer.sdp}).encode(),
                self.__server_address
            )
            
            # 启动视频流和心跳
            await self.__video_stream_receiver.start()
            await self.__start_heartbeat()
            
        except Exception as e:
            self.logger.error(f"客户端运行异常: {e}")

    def get_latest_frame(self) -> tuple[bool, np.ndarray]:
        """
        获取最新视频帧

        Returns:
            tuple[bool, np.ndarray]: 视频帧状态和帧数据
        """
        return self.__video_stream_receiver.get_latest_frame()

    async def close(self):
        """
        安全关闭客户端
        """
        # 关闭客户端任务
        if self.__client_task and not self.__client_task.done():
            self.__client_task.cancel()
        # 关闭UDP socket
        if self.__udp_socket:
            self.__udp_socket.close()
        # 关闭视频流接收器
        await self.__video_stream_receiver.stop()
        # 关闭对等连接
        self.__loop.create_task(self.__pc.close())
        # 停止事件循环
        if self.__loop.is_running():
            self.__loop.stop()
        self.logger.info("客户端已关闭")

    def __enter__(self):
        """
        进入上下文管理器
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        退出上下文管理器
        """
        asyncio.run(self.close())

    def __del__(self):
        """
        确保资源释放
        """
        asyncio.run(self.close())
