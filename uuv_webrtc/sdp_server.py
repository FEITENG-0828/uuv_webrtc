"""
SDP信令服务器模块
处理SDP协议交换和信令传输
"""

import socket
import threading
import asyncio
import json
import time
from typing import Optional
import logging

from .utils import get_host_ip

class SdpServer:
    """SDP信令服务器类
    负责处理offer/answer交换和ICE候选信息传输
    """
    
    def __init__(self, udp_port: int, logger: logging.Logger = None):
        """初始化SDP信令服务器

        Args:
            udp_port (int): 本地UDP端口
            logger (logging.Logger): 日志记录器
        """
        self.logger = logger or logging.getLogger(__name__)

        # 网络通信配置
        self.__udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__udp_socket.bind(("0.0.0.0", udp_port))
        
        # 连接状态信息（使用锁保证线程安全）
        self.__lock = threading.Lock()
        self.__local_description: Optional[str] = None
        self.__remote_description: Optional[str] = None
        self.__remote_heart_beat: Optional[float] = None
        
        # 启动消息接收线程
        self.__recv_thread = threading.Thread(
            target=self.__recv_handle, 
            daemon=True,
            name="SDP_Server_Receiver"
        )
        self.__recv_thread.start()
        
        self.logger.info(f"SDP服务已启动 | 地址：{get_host_ip()} | 端口：{udp_port}")

    def set_local_description(self, sdp: str) -> None:
        """设置本地SDP描述（Offer）

        Args:
            sdp (str): 本地SDP描述
        """
        with self.__lock:
            self.__local_description = sdp

    def get_remote_description(self) -> Optional[str]:
        """获取远端SDP描述（Answer）

        Returns:
            Optional[str]: 远端SDP描述
        """
        with self.__lock:
            return self.__remote_description

    def get_remote_heart_beat(self) -> Optional[float]:
        """获取最后一次心跳时间戳

        Returns:
            Optional[float]: 最后一次心跳时间戳
        """
        with self.__lock:
            return self.__remote_heart_beat

    async def wait_remote_description(self) -> None:
        """
        异步等待远端SDP描述就绪
        """
        while self.__remote_description is None:
            await asyncio.sleep(0.1)

    def __recv_handle(self) -> None:
        """
        UDP消息处理循环
        """
        while True:
            try:
                # 接收并解析消息
                remote_msg, remote_addr = self.__udp_socket.recvfrom(4096)
                decoded_msg = remote_msg.decode()
                
                # 处理不同类型的消息
                if self.__local_description is not None:
                    if decoded_msg == "ask_offer":
                        if self.__remote_description is None:
                            # 发送Offer给请求方
                            offer = json.dumps({"type": "offer", "sdp": self.__local_description})
                            self.__udp_socket.sendto(offer.encode(), remote_addr)
                        else:
                            self.clear_connection_info()

                    elif decoded_msg == "heart_beat":
                        # 更新心跳时间
                        with self.__lock:
                            self.__remote_heart_beat = time.time()
                    
                    else:
                        # 处理Answer响应
                        try:
                            answer = json.loads(decoded_msg)
                            if answer.get("type") == "answer" and "sdp" in answer:
                                with self.__lock:
                                    self.__remote_description = answer["sdp"]
                        except json.JSONDecodeError as e:
                            self.logger.error(f"无效的JSON格式: {decoded_msg} | 错误: {e}")
                else:
                    self.logger.debug("本地SDP描述为空")

            except Exception as e:
                self.logger.error(f"接收消息异常: {str(e)}")
                time.sleep(1)  # 防止错误循环

    def clear_connection_info(self) -> None:
        """
        重置所有连接信息
        """
        with self.__lock:
            self.__local_description = None
            self.__remote_description = None
            self.__remote_heart_beat = None

    def close(self) -> None:
        """
        安全关闭服务
        """
        if self.__recv_thread.is_alive():
            self.__recv_thread.join(timeout=2)
        if self.__udp_socket:
            self.__udp_socket.close()

    def __del__(self):
        """
        确保资源释放
        """
        self.close()
