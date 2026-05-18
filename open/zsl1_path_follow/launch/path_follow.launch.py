#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
path_follow.launch.py  –  Launch the closed-loop path follower node (ROS 2 Humble).

Usage:
  ros2 launch zsl1_path_follow path_follow.launch.py
  ros2 launch zsl1_path_follow path_follow.launch.py maxSpeed:=0.8 odomTopic:=/my_odom
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # ── Declare launch arguments (all map 1-to-1 to node parameters) ─────────
    args = [
        DeclareLaunchArgument('sensorOffsetX',    default_value='0.0'),
        DeclareLaunchArgument('sensorOffsetY',    default_value='0.0'),
        DeclareLaunchArgument('lookAheadDis',     default_value='0.5'),
        DeclareLaunchArgument('yawRateGain',      default_value='7.5'),
        DeclareLaunchArgument('stopYawRateGain',  default_value='7.5'),
        DeclareLaunchArgument('maxYawRate',       default_value='45.0'),
        DeclareLaunchArgument('maxSpeed',         default_value='1.2'),
        DeclareLaunchArgument('maxAccel',         default_value='1.0'),
        DeclareLaunchArgument('twoWayDrive',      default_value='true'),
        DeclareLaunchArgument('stopDisThre',      default_value='0.2'),
        DeclareLaunchArgument('slowDwnDisThre',   default_value='1.0'),
        DeclareLaunchArgument('dirDiffThre',      default_value='0.1'),
        DeclareLaunchArgument('alignYaw',         default_value='false'),
        DeclareLaunchArgument('autoStopWhenDone', default_value='true'),
        DeclareLaunchArgument('odomTopic',
            default_value='/zsl1sensor1/mid360_mid/gazebo_gt/odometry'),
        DeclareLaunchArgument('pathTopic',  default_value='/local_planner/path'),
        DeclareLaunchArgument('cmdTopic',   default_value='/zsl1sensor1/cmd_vel'),
        DeclareLaunchArgument('stopTopic',  default_value='/path_follow_stop'),
    ]

    path_follow_node = Node(
        package='zsl1_path_follow',
        executable='path_follow_close',
        name='path_follow',
        output='screen',
        parameters=[{
            'sensorOffsetX':    LaunchConfiguration('sensorOffsetX'),
            'sensorOffsetY':    LaunchConfiguration('sensorOffsetY'),
            'lookAheadDis':     LaunchConfiguration('lookAheadDis'),
            'yawRateGain':      LaunchConfiguration('yawRateGain'),
            'stopYawRateGain':  LaunchConfiguration('stopYawRateGain'),
            'maxYawRate':       LaunchConfiguration('maxYawRate'),
            'maxSpeed':         LaunchConfiguration('maxSpeed'),
            'maxAccel':         LaunchConfiguration('maxAccel'),
            'twoWayDrive':      LaunchConfiguration('twoWayDrive'),
            'stopDisThre':      LaunchConfiguration('stopDisThre'),
            'slowDwnDisThre':   LaunchConfiguration('slowDwnDisThre'),
            'dirDiffThre':      LaunchConfiguration('dirDiffThre'),
            'alignYaw':         LaunchConfiguration('alignYaw'),
            'autoStopWhenDone': LaunchConfiguration('autoStopWhenDone'),
            'odomTopic':        LaunchConfiguration('odomTopic'),
            'pathTopic':        LaunchConfiguration('pathTopic'),
            'cmdTopic':         LaunchConfiguration('cmdTopic'),
            'stopTopic':        LaunchConfiguration('stopTopic'),
        }],
    )

    return LaunchDescription(args + [path_follow_node])
