"""
WebRTC服务器模块
实现WebRTC服务端逻辑和连接管理
"""

import asyncio
import threading
import time
import logging

from aiortc import RTCPeerConnection, RTCSessionDescription

from .cv_capture import CvCapture
from .sdp_server import SdpServer
from .cv_cap_stream_track import CvCapStreamTrack
from .utils import force_codec

class RtcServer:
    """
    WebRTC服务器类
    实现WebRTC服务端逻辑和连接管理
    """

    def __init__(
        self,
        cap : CvCapture,
        port: int = 20000,
        codec: str = "video/VP8",
        logger: logging.Logger = None,
    ) -> None:
        """
        初始化WebRTC服务器

        Args:
            cap: 视频捕获对象
            port: 本地sdp信令服务的开放端口
            codec: 视频编解码器
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger(__name__)

        self.__codec = codec.lower()
        self.__pcs = set()

        self.__cap = cap
        self.__sdp_server = SdpServer(port, self.logger)

        # 异步事件循环管理
        self.__loop = asyncio.new_event_loop()
        self.__server_task = self.__loop.create_task(self.__run_server())
        self.__event_loop_thread = threading.Thread(
            target=self.__start_event_loop, 
            daemon=True
        )
        self.__event_loop_thread.start()
        self.logger.info("服务器初始化完成")

    def __start_event_loop(self):
        """
        启动事件循环
        """
        asyncio.set_event_loop(self.__loop)
        try:
            self.__loop.run_forever()
        finally:
            self.__loop.close()

    async def __on_connection_state_change(self, pc: RTCPeerConnection):
        """
        连接状态变更处理

        Args:
            pc: 对等连接对象
        """
        state = pc.connectionState
        self.logger.info(f"连接状态变更: {state}")
        if state in ["failed", "closed"]:
            await pc.close()
            self.__cleanup_connection(pc)

    async def __negotiate_connection(self, pc: RTCPeerConnection):
        """
        SDP协商流程

        Args:
            pc: 对等连接对象
        """
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        self.__sdp_server.set_local_description(pc.localDescription.sdp)

        self.logger.info(f"等待客户端应答...")
        await self.__sdp_server.wait_remote_description()
        
        answer = RTCSessionDescription(
            sdp=self.__sdp_server.get_remote_description(),
            type="answer"
        )
        await pc.setRemoteDescription(answer)

    async def __monitor_connection(self, pc: RTCPeerConnection):
        """
        连接状态监控

        Args:
            pc: 对等连接对象
        """
        try:
            while pc.connectionState not in ["closed", "failed"]:
                if self.__sdp_server.get_remote_heart_beat():
                    if time.time() - self.__sdp_server.get_remote_heart_beat() > 5:
                        self.logger.warning("连接超时")
                        await pc.close()
                else:
                    self.logger.warning("需要重新连接")
                    await pc.close()
                await asyncio.sleep(1)
        finally:
            self.__cleanup_connection(pc)

    async def __run_server(self):
        """
        主服务器逻辑
        """
        try:
            while True:
                self.logger.info("创建新连接")
                pc = RTCPeerConnection()
                self.__pcs.add(pc)
                
                # 添加视频轨道并设置编解码器
                sender = pc.addTrack(CvCapStreamTrack(self.__cap, self.logger))
                force_codec(pc, sender, self.__codec)
                pc.on("connectionstatechange", lambda: self.__on_connection_state_change(pc))

                await self.__negotiate_connection(pc)
                await self.__monitor_connection(pc)
                self.logger.info("连接结束")

        except asyncio.CancelledError:
            self.logger.info("服务器将正常关闭")
        except Exception as e:
            self.logger.error(f"服务器异常: {e}")

    def __cleanup_connection(self, pc: RTCPeerConnection):
        """
        清理连接资源

        Args:
            pc: 对等连接对象
        """
        if pc in self.__pcs:
            self.__pcs.remove(pc)
        self.__sdp_server.clear_connection_info()

    async def close(self):
        """
        安全关闭服务器
        """
        # 关闭服务器任务
        if self.__server_task and not self.__server_task.done():
            self.__server_task.cancel()
        # 确保所有连接关闭
        await asyncio.gather(
            *(pc.close() for pc in self.__pcs),
            return_exceptions=True
        )
        # 关闭sdp信令服务
        if self.__sdp_server:
            self.__sdp_server.close()
        # 停止事件循环
        if self.__loop.is_running():
            self.__loop.stop()
        self.logger.info("服务器已关闭")

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
