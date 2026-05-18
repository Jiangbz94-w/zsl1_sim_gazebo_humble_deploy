#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File    : test.py
@Author  : kunpeng fan
@Brief   : To test the path_lib and path_follow func.
@License : Copyright (c) 2026. Licensed under the MIT License.

3 个组件可以按需组合，但 enable_cmd_pub 和 enable_close_loop 不能同时开启（两者都向
同一 cmd_vel topic 发布，指令会叠加冲突）：

  enable_path_pub  : 轨迹发布  —— 生成 PathLib 路径并发布到 path_topic（供 RViz 可视化
                                   或外部闭环节点订阅）
  enable_cmd_pub   : 开环规控  —— PCtl 根据内部路径计算 (v,w) 序列，逐帧定时发布到
                                   cmd_topic；不依赖 odom，不订阅任何 topic
  enable_close_loop: 闭环规控  —— PathFollowerClose 订阅 odom + path_topic，
                                   100 Hz 纯追踪控制输出 cmd_topic

有效组合：
  ┌──────────────────────────────────────────────────────────────────────┐
  │ 组合                          │ 适用场景                              │
  ├──────────────────────────────────────────────────────────────────────┤
  │ path_pub + close_loop         │ 最常用：内部发路径 + 闭环跟踪         │
  │ path_pub + open_loop          │ 内部发路径（可视化）+ 开环执行         │
  │ open_loop only                │ 纯开环，无需 odom，调试用             │
  │ close_loop only               │ 纯闭环，path 由外部节点发布           │
  │ path_pub only                 │ 只发路径，控制由其他节点负责           │
  └──────────────────────────────────────────────────────────────────────┘

Usage examples:
  cd /workspace/src/zsl1/zsl1_path_follow
  source /opt/ros/humble/setup.bash && source /workspace/install/setup.bash

  # 先发路径，再闭环跟踪（最常用）
  python3 zsl1_path_follow/scripts/test.py _enable_path_pub:=true _enable_close_loop:=true

  # 先发路径（RViz 可视化），再开环执行（不依赖 odom）
  python3 zsl1_path_follow/scripts/test.py _enable_path_pub:=true _enable_open_loop:=true

  # 纯开环（不发路径，不依赖 odom，直接执行）
  python3 zsl1_path_follow/scripts/test.py _enable_open_loop:=true

  # 纯闭环（path 由外部节点发布到 /local_planner/path）
  # 等价于直接运行 path_follow_close.py，但后者更精简
  python3 zsl1_path_follow/scripts/test.py _enable_path_pub:=false _enable_close_loop:=true

  # 最精简的纯闭环（推荐，无多余节点）
  python3 zsl1_path_follow/scripts/path_follow_close.py

  # 通过 ros2 run 启动（ROS2 风格参数，已自动 source）：
  ros2 run zsl1_path_follow test_path_follow --ros-args -p enable_path_pub:=true -p enable_open_loop:=true -p enable_close_loop:=false
"""

import sys
import os

# ── 将 ROS1 风格 _key:=value 参数转换为 ROS2 --ros-args -p key:=value ──────────
def _convert_ros1_args():
    ros1_params = []
    remaining = [sys.argv[0]]
    for arg in sys.argv[1:]:
        if arg.startswith('_') and ':=' in arg:
            key, val = arg[1:].split(':=', 1)
            ros1_params += ['-p', f'{key}:={val}']
        else:
            remaining.append(arg)
    if ros1_params:
        remaining += ['--ros-args'] + ros1_params
    sys.argv = remaining

_convert_ros1_args()

import rclpy
from rclpy.node import Node

import numpy as np

from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped
from builtin_interfaces.msg import Time as RosTime

# 支持 ros2 run（相对 import）和 python3 直接运行（绝对 import）两种方式
try:
    from .path_lib import PathLib
    from .path_follow_open import PathFollowerOpen
    from .cmd_pub import CmdVelPublisher
    from .path_follow_close import PathFollowerClose
except ImportError:
    _scripts_dir = os.path.dirname(os.path.abspath(__file__))
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)
    from path_lib import PathLib
    from path_follow_open import PathFollowerOpen
    from cmd_pub import CmdVelPublisher
    from path_follow_close import PathFollowerClose


# ── Helpers ────────────────────────────────────────────────────────────────────

def numpy_to_ros_path(node: Node, traj: np.ndarray, frame_id: str = 'map') -> Path:
    """Convert [T, 3] numpy array (x, y, yaw) to nav_msgs/Path."""
    ros_path = Path()
    ros_path.header.stamp    = node.get_clock().now().to_msg()
    ros_path.header.frame_id = frame_id

    for i in range(traj.shape[0]):
        x, y, yaw = traj[i]

        pose = PoseStamped()
        pose.header.stamp    = ros_path.header.stamp
        pose.header.frame_id = frame_id
        pose.pose.position.x = float(x)
        pose.pose.position.y = float(y)
        pose.pose.position.z = 0.0
        pose.pose.orientation.x = 0.0
        pose.pose.orientation.y = 0.0
        pose.pose.orientation.z = float(np.sin(yaw / 2.0))
        pose.pose.orientation.w = float(np.cos(yaw / 2.0))

        ros_path.poses.append(pose)

    return ros_path


def refresh_path_stamp(node: Node, path_msg: Path) -> None:
    """Refresh header stamps so downstream tools see a current message."""
    stamp = node.get_clock().now().to_msg()
    path_msg.header.stamp = stamp
    for pose in path_msg.poses:
        pose.header.stamp = stamp


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ('1', 'true', 'yes', 'on')
    return bool(value)


# ── Main Node ──────────────────────────────────────────────────────────────────

class TestPathFollowNode(Node):
    def __init__(self):
        super().__init__('test_path_follow_demo')

        # ── Mode switches ────────────────────────────────────────────────────
        self.declare_parameter('enable_path_pub',          True)
        self.declare_parameter('enable_open_loop',         False)
        self.declare_parameter('enable_close_loop',        False)
        self.declare_parameter('auto_exit_when_cmd_done',  '')

        self.declare_parameter('path_topic',   '/local_planner/path')
        self.declare_parameter('cmd_topic',    '/zsl1sensor1/cmd_vel')
        self.declare_parameter('odom_topic',   '/zsl1sensor1/mid360_mid/gazebo_gt/odometry')
        self.declare_parameter('frame_id',     'map')
        self.declare_parameter('path_pub_hz',  5.0)
        self.declare_parameter('cmd_pub_hz',   4)

        self.declare_parameter('total_paths',       3)
        self.declare_parameter('max_angle_deg',     60.0)
        self.declare_parameter('distance',          4.0)
        self.declare_parameter('num_future_points', 40)
        self.declare_parameter('path_idx',          2)
        self.declare_parameter('cmd_max_w',         3.0)
        self.declare_parameter('append_stop_cmd',   True)
        self.declare_parameter('stop_cmd_count',    3)

        def _g(name):
            return self.get_parameter(name).value

        enable_path_pub   = _as_bool(_g('enable_path_pub'))
        enable_open_loop  = _as_bool(_g('enable_open_loop'))
        enable_close_loop = _as_bool(_g('enable_close_loop'))
        auto_exit_raw     = _g('auto_exit_when_cmd_done')

        path_topic   = str(_g('path_topic'))
        cmd_topic    = str(_g('cmd_topic'))
        odom_topic   = str(_g('odom_topic'))
        frame_id     = str(_g('frame_id'))
        path_pub_hz  = float(_g('path_pub_hz'))
        cmd_pub_hz   = max(int(_g('cmd_pub_hz')), 1)

        total_paths       = max(int(_g('total_paths')), 1)
        max_angle         = float(_g('max_angle_deg'))
        distance          = float(_g('distance'))
        num_future_points = int(_g('num_future_points'))
        path_idx          = int(_g('path_idx'))
        cmd_max_w         = float(_g('cmd_max_w'))
        append_stop_cmd   = _as_bool(_g('append_stop_cmd'))
        stop_cmd_count    = int(_g('stop_cmd_count'))

        if auto_exit_raw == '':
            auto_exit_when_cmd_done = not enable_path_pub
        else:
            auto_exit_when_cmd_done = _as_bool(auto_exit_raw)

        if not enable_path_pub and not enable_open_loop and not enable_close_loop:
            self.get_logger().warn('All mode switches are disabled, nothing to do.')
            return

        if enable_open_loop and enable_close_loop:
            self.get_logger().error(
                'enable_open_loop 和 enable_close_loop 不能同时启用！'
                '两者都向同一 cmd_vel topic 发布，指令会叠加冲突。'
                '请只选其中一种控制模式。'
            )
            raise RuntimeError('enable_open_loop and enable_close_loop are mutually exclusive.')

        # ── Build path ────────────────────────────────────────────────────────
        paths = PathLib(
            total_paths=total_paths,
            max_angle=max_angle,
            distance=distance,
            num_future_points=num_future_points,
        )

        if path_idx < 0 or path_idx >= total_paths:
            new_idx = path_idx % total_paths
            self.get_logger().warn(
                f'path_idx={path_idx} out of range, use {new_idx} instead.')
            path_idx = new_idx

        path     = paths.get_path(idx=path_idx)
        path_msg = numpy_to_ros_path(self, traj=path, frame_id=frame_id)

        # ── Path publisher ────────────────────────────────────────────────────
        self._path_pub = None
        if enable_path_pub:
            from rclpy.qos import QoSProfile, DurabilityPolicy
            qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
            self._path_pub = self.create_publisher(Path, path_topic, qos)
            refresh_path_stamp(self, path_msg)
            self._path_pub.publish(path_msg)
            self.get_logger().info(
                f'Path published once on {path_topic} ({len(path_msg.poses)} poses)')

        # ── Open-loop cmd ─────────────────────────────────────────────────────
        self._cmd_vel_pub = None
        if enable_open_loop:
            controller = PathFollowerOpen(dt=1.0 / float(cmd_pub_hz), max_w=cmd_max_w)
            actions = list(controller.path_follow(traj=path))
            if append_stop_cmd and stop_cmd_count > 0:
                actions.extend([(0.0, 0.0)] * stop_cmd_count)

            self._cmd_vel_pub = CmdVelPublisher(freq=cmd_pub_hz, cmd_topic=cmd_topic)
            self._cmd_vel_pub.set_actions(actions)
            self.get_logger().info(
                f'Open-loop mode ON, topic={cmd_topic}, rate={cmd_pub_hz} Hz, queued actions={len(actions)}'
            )

        # ── Close-loop control ────────────────────────────────────────────────
        self._follower = None
        if enable_close_loop:
            self.get_logger().info('Close-loop mode ON: starting PathFollowerClose ...')
            # 直接把 test.py 的 topic 配置透传给 PathFollowerClose，无需重复配参
            self._follower = PathFollowerClose(
                odom_topic=odom_topic,
                path_topic=path_topic,
                cmd_topic=cmd_topic,
            )

        self.get_logger().info('TestPathFollowNode ready.')


def main(args=None):
    rclpy.init(args=args)

    test_node   = TestPathFollowNode()
    follower    = getattr(test_node, '_follower',    None)  # 闭环节点
    cmd_vel_pub = getattr(test_node, '_cmd_vel_pub', None)  # 开环节点

    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(test_node)
    if follower is not None:
        executor.add_node(follower)
    if cmd_vel_pub is not None:
        executor.add_node(cmd_vel_pub)  # 开环节点也需要 spin 才能触发定时器

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        if follower is not None:
            follower.stop()
        if cmd_vel_pub is not None:
            cmd_vel_pub.destroy_node()
        test_node.destroy_node()
        if follower is not None:
            follower.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
