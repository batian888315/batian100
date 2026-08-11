#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import base64
import requests
import json
import cv2

class VisionToText(Node):
    def __init__(self):
        super().__init__('vision_to_text')
        self.bridge = CvBridge()
        self.sub = self.create_subscription(Image, '/camera/image_raw', self.image_callback, 10)
        self.pub = self.create_publisher(String, '/marker_text', 10)

        # ---------- 请替换以下配置 ----------
        self.api_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"  # 例如火山引擎
        self.api_key = "YOUR_API_KEY"  # 替换为真实API Key
        self.model = "doubao-vision-pro-32k"  # 替换为模型ID
        # ------------------------------------

        self.get_logger().info("Vision-to-Text (Cloud AI) started")

    def image_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            _, buffer = cv2.imencode('.jpg', cv_image)
            base64_image = base64.b64encode(buffer).decode('utf-8')

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "请用中文简短描述这张图片中的文字和标志内容，只输出识别到的文字信息。"},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ]
            }
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                result = response.json()
                text = result['choices'][0]['message']['content']
                self.get_logger().info(f"AI识别结果: {text}")
                pub_msg = String()
                pub_msg.data = text
                self.pub.publish(pub_msg)
        except Exception as e:
            self.get_logger().error(f"AI识别失败: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = VisionToText()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()