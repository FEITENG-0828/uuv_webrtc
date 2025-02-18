"""
网络工具模块
包含IP获取、WebRTC编解码控制等实用功能
"""

import socket
from typing import Optional

from aiortc import RTCPeerConnection, RTCRtpTransceiver
from aiortc.rtcrtpsender import RTCRtpSender

def get_host_ip() -> str:
    """
    获取本机有效IPv4地址
    优先返回局域网地址，失败时返回回环地址
    
    Returns:
        str: IPv4地址字符串 (如 "192.168.0.101")
    """
    try:
        # 使用UDP连接获取IP地址
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(1.0)  # 设置1秒超时
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except (socket.error, OSError):
        return "127.0.0.1"

def force_codec(pc: RTCPeerConnection, sender: RTCRtpSender, forced_codec: str) -> None:
    """
    强制使用指定编解码器
    
    Args:
        pc (RTCPeerConnection): WebRTC对等连接对象
        sender (RTCRtpSender): RTP发送器
        forced_codec (str): 强制使用的编解码器名称 (如 "video/H264")
    
    Raises:
        ValueError: 找不到匹配的Transceiver或编解码器时抛出
    """
    try:
        # 解析编解码器类型
        kind = forced_codec.split("/")[0].lower()

        # 获取对应类型的编解码能力
        codecs = RTCRtpSender.getCapabilities(kind).codecs

        # 过滤出目标编解码器
        matched_codecs = [c for c in codecs if c.mimeType.lower() == forced_codec.lower()]
        if not matched_codecs:
            raise ValueError(f"不支持的编解码器: {forced_codec}")

        # 查找匹配的Transceiver
        transceiver: Optional[RTCRtpTransceiver] = next(
            (t for t in pc.getTransceivers() if t.sender == sender), None
        )
        if not transceiver:
            raise ValueError("找不到匹配的Transceiver")

        transceiver.setCodecPreferences(matched_codecs)

    except StopIteration as e:
        raise ValueError("找不到可用的Transceiver") from e
