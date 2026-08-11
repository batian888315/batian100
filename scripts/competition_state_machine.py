#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from nav_msgs.msg import Odometry
import math
import time
import pyttsx3

class CompetitionStateMachine(Node):
    def __init__(self):
        super().__init__('competition_state_machine')
        self.get_logger().info("State Machine Initialized")

        # ---- 语音引擎 ----
        self.tts = pyttsx3.init()
        self.tts.setProperty('rate', 150)

        # ---- 状态 ----
        self.state = "INIT"
        self.task1_done = False
        self.task2_done = False
        self.task3_done = False
        self.task4_done = False

        # ---- 定位（订阅里程计） ----
        self.current_x = 0.0
        self.current_y = 0.0
        self.create_subscription(Odometry, '/odom', self.odom_callback, 10)

        # ---- 识别结果 ----
        self.qr_data = ""
        self.marker_text = ""

        # ---- 雷达数据 ----
        self.laser_ranges = []
        self.laser_angle_min = -3.1415926
        self.laser_angle_max = 3.1415926
        self.create_subscription(LaserScan, '/scan', self.laser_callback, 10)

        # ---- 订阅识别话题 ----
        self.create_subscription(String, '/qr_code_info', self.qr_callback, 10)
        self.create_subscription(String, '/marker_text', self.marker_callback, 10)

        # ---- 发布速度 ----
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # ---- 地图固定点 ----
        self.start_pose = (0.5, 0.5)
        self.task_pub_pose = (4.5, 1.8)
        self.channel_entrance = (5.0, 1.25)
        self.parking_pose = (0.5, 0.5)

        # ---- 罚时 ----
        self.penalty = 0

        # ---- 主循环定时器 ----
        self.timer = self.create_timer(0.1, self.run)

    # ----- 回调函数 -----
    def odom_callback(self, msg):
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y

    def laser_callback(self, msg):
        self.laser_ranges = msg.ranges
        self.laser_angle_min = msg.angle_min
        self.laser_angle_max = msg.angle_max

    def qr_callback(self, msg):
        self.qr_data = msg.data
        self.get_logger().info(f"QR received: {self.qr_data}")

    def marker_callback(self, msg):
        self.marker_text = msg.data
        self.get_logger().info(f"Marker AI text: {self.marker_text}")

    # ----- 语音播报 -----
    def speak(self, text):
        self.tts.say(text)
        self.tts.runAndWait()

    # ----- 雷达避障检测 -----
    def check_obstacle(self, front_angle=30, distance_threshold=0.5):
        if not self.laser_ranges:
            return False
        angle_range = math.radians(front_angle)
        mid = len(self.laser_ranges)//2
        half = int(angle_range / (self.laser_angle_max - self.laser_angle_min) * len(self.laser_ranges))
        start = max(0, mid - half)
        end = min(len(self.laser_ranges), mid + half)
        for i in range(start, end):
            if 0.05 < self.laser_ranges[i] < distance_threshold:
                return True
        return False

    def get_obstacle_direction(self):
        # 返回 -1: 左转, 1: 右转 (基于左右障碍物距离)
        if not self.laser_ranges:
            return 0
        mid = len(self.laser_ranges)//2
        left_avg = sum(self.laser_ranges[max(0, mid-20):mid]) / 20 if mid>20 else 1.0
        right_avg = sum(self.laser_ranges[mid:min(len(self.laser_ranges), mid+20)]) / 20 if mid+20 <= len(self.laser_ranges) else 1.0
        if left_avg < right_avg:
            return 1   # 左侧更近 → 右转
        else:
            return -1  # 右侧更近 → 左转

    # ----- 运动控制 -----
    def move_to_target(self, target_x, target_y, tolerance=0.2):
        cmd = Twist()
        rate = self.create_rate(20)
        while rclpy.ok():
            dx = target_x - self.current_x
            dy = target_y - self.current_y
            dist = math.hypot(dx, dy)
            if dist < tolerance:
                break
            # 避障
            if self.check_obstacle(front_angle=40, distance_threshold=0.6):
                dir_ = self.get_obstacle_direction()
                cmd.linear.x = 0.1
                cmd.angular.z = dir_ * 0.6
            else:
                angle = math.atan2(dy, dx)
                cmd.linear.x = min(0.3, dist * 0.4)
                cmd.angular.z = max(-0.8, min(0.8, angle * 1.2))
            self.cmd_pub.publish(cmd)
            rate.sleep()
        # 停止
        self.stop()

    def stop(self):
        self.cmd_pub.publish(Twist())

    # ----- 子任务1 -----
    def do_task1(self):
        self.speak("开始执行任务一，前往任务发布点")
        self.move_to_target(self.task_pub_pose[0], self.task_pub_pose[1])
        self.task1_done = True
        self.state = "TASK2"

    # ----- 子任务2：识别 -----
    def do_task2(self):
        self.speak("开始识别二维码和图文标记")
        timeout = 20
        start = time.time()
        while time.time() - start < timeout:
            if self.qr_data and self.marker_text:
                break
            rclpy.spin_once(self, timeout_sec=0.1)
        # 罚时
        if not self.qr_data:
            self.penalty += 30
            self.speak("二维码识别失败，罚时30秒")
        else:
            self.speak(f"二维码内容：{self.qr_data}")
        if not self.marker_text:
            self.penalty += 20
            self.speak("图文标记识别失败，罚时20秒")
        else:
            self.speak(f"图文标记内容：{self.marker_text}")
        self.task2_done = True
        self.state = "TASK3"

    # ----- 子任务3：通道行驶（奇偶决定方向）-----
    def do_task3(self):
        # 判断奇偶
        direction = "cw"  # 默认
        try:
            num = int(self.qr_data.strip())
            if num % 2 == 0:
                direction = "ccw"
                self.speak("偶数，逆时针行驶")
            else:
                direction = "cw"
                self.speak("奇数，顺时针行驶")
        except:
            self.speak("二维码非数字，默认顺时针")
        # 获取航点
        waypoints = self.get_channel_waypoints(direction)
        self.speak("开始进入黄色通道")
        for idx, wp in enumerate(waypoints):
            self.move_to_target(wp[0], wp[1], tolerance=0.15)
            if idx % 3 == 0:
                self.speak(f"已通过第{idx+1}个航点")
        # 回到通道入口
        self.move_to_target(self.channel_entrance[0], self.channel_entrance[1])
        self.speak("已回到通道入口")
        self.task3_done = True
        self.state = "TASK4"

    def get_channel_waypoints(self, direction):
        if direction == "cw":
            return [
                (5.0, 1.25), (5.5, 1.5), (6.0, 2.0), (6.5, 2.2),
                (7.0, 2.0), (7.5, 1.5), (8.0, 1.25), (7.5, 1.0),
                (7.0, 0.5), (6.5, 0.3), (6.0, 0.5), (5.5, 1.0),
                (5.0, 1.25)
            ]
        else:
            return [
                (5.0, 1.25), (5.5, 1.0), (6.0, 0.5), (6.5, 0.3),
                (7.0, 0.5), (7.5, 1.0), (8.0, 1.25), (7.5, 1.5),
                (7.0, 2.0), (6.5, 2.2), (6.0, 2.0), (5.5, 1.5),
                (5.0, 1.25)
            ]

    # ----- 子任务4：返回停车点 -----
    def do_task4(self):
        self.speak("返回停车点")
        self.move_to_target(self.parking_pose[0], self.parking_pose[1])
        self.task4_done = True
        self.state = "FINISH"

    # ----- 主循环 -----
    def run(self):
        if self.state == "INIT":
            self.speak("比赛开始")
            self.state = "TASK1"
        elif self.state == "TASK1" and not self.task1_done:
            self.do_task1()
        elif self.state == "TASK2" and self.task1_done and not self.task2_done:
            self.do_task2()
        elif self.state == "TASK3" and self.task2_done and not self.task3_done:
            self.do_task3()
        elif self.state == "TASK4" and self.task3_done and not self.task4_done:
            self.do_task4()
        elif self.state == "FINISH":
            self.stop()
            self.speak("全部任务完成")
            self.get_logger().info(f"Total penalty: {self.penalty}s")
            self.timer.cancel()

def main(args=None):
    rclpy.init(args=args)
    node = CompetitionStateMachine()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()