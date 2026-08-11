#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
from pyzbar import pyzbar

class QRDetector(Node):
    def __init__(self):
        super().__init__('qr_detector')
        self.bridge = CvBridge()
        self.pub = self.create_publisher(String, '/qr_code_info', 10)
        self.sub = self.create_subscription(Image, '/camera/image_raw', self.image_callback, 10)
        self.get_logger().info("QR Detector started")

    def image_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            return
        barcodes = pyzbar.decode(cv_image)
        for barcode in barcodes:
            data = barcode.data.decode("utf-8")
            self.get_logger().info(f"QR detected: {data}")
            pub_msg = String()
            pub_msg.data = data
            self.pub.publish(pub_msg)
            break

def main(args=None):
    rclpy.init(args=args)
    node = QRDetector()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()