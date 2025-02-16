"""
客户端测试程序
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
from uuv_webrtc import RtcClient

if __name__ == "__main__":
    with RtcClient(
        local_port=20001,
        server_address=("192.168.0.101", 20000)
    ) as client:
        try:
            while True:
                success, frame = client.getLatestFrame()
                if success:
                    cv2.imshow("client", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

        except KeyboardInterrupt:
            pass
        finally:
            print(client.getFrameSize())
            print("客户端退出")
            cv2.destroyAllWindows()
