"""
服务器测试程序
"""
import sys
import os
sys.path.append(os.path.dirname(__file__) + "/../src/")

import time
import logging
from uuv_webrtc import CvCapture
from uuv_webrtc import RtcServer

# 创建自定义logger
server_logger = logging.getLogger("MyServer")
server_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(
    filename=os.path.join(os.path.dirname(__file__), 'server.log'),
    mode='w',
    encoding='utf-8'
)
file_handler.setFormatter(logging.Formatter(
    '[%(levelname)s] %(asctime)s - %(message)s'
))
server_logger.addHandler(file_handler)

if __name__ == "__main__":
    cap = CvCapture(cam=0, frame_size=(1280, 720), fps=30, logger=server_logger)
    with RtcServer(cap=cap, port=20000, codec="video/VP8", logger=server_logger) as server:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            server_logger.info("服务器通过Ctrl+C退出")
