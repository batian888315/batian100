#!/usr/bin/env python3
import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # 1. 底盘（OriginCar Pro）
    origincar_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('origincar_base'),
                'launch',
                'origincar_bringup.launch.py'
            )
        )
    )

    # 2. N10雷达
    radar_node = Node(
        package='ydlidar_ros2_driver',
        executable='ydlidar_ros2_driver_node',
        name='ydlidar_ros2_driver_node',
        output='screen',
        parameters=[{
            'port': '/dev/ttyUSB0',
            'frame_id': 'laser_frame',
            'baudrate': 230400,
            'lidar_type': 1,
        }]
    )

    # 3. 二维码识别
    qr_node = Node(
        package='competition_control',
        executable='qr_detector.py',
        name='qr_detector',
        output='screen'
    )

    # 4. 图文AI识别
    ai_node = Node(
        package='competition_control',
        executable='vision_to_text.py',
        name='vision_to_text',
        output='screen'
    )

    # 5. 主状态机
    state_machine_node = Node(
        package='competition_control',
        executable='competition_state_machine.py',
        name='competition_state_machine',
        output='screen'
    )

    return LaunchDescription([
        origincar_bringup,
        radar_node,
        qr_node,
        ai_node,
        state_machine_node,
    ])