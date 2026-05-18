#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File    : path_follow_close.py
@Author  : kunpeng fan
@Brief   : Closed-loop path follower (ROS 2 Humble).
           Subscribes to odom + path, outputs cmd_vel at 100 Hz via a ROS timer.
           Can be run standalone or imported and instantiated by test.py.
@License : Copyright (c) 2026. Licensed under the MIT License.
"""

import math
from typing import Optional

from scipy.spatial.transform import Rotation

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry, Path
from geometry_msgs.msg import Twist
from std_msgs.msg import Int8


class PathFollowerClose(Node):
    """
    Closed-loop path follower (pure pursuit + speed ramp).

    订阅 odom + nav_msgs/Path，100 Hz 定时输出 cmd_vel。
    与 PathFollowerOpen 的区别：
      - PathFollowerOpen : 离线预计算 (v,w) 序列，不依赖 odom
      - PathFollowerClose: 实时闭环，依赖 odom 反馈，跟踪精度更高

    Usage examples
    --------------
    # Standalone（最精简）：
        rclpy.init()
        node = PathFollowerClose()
        rclpy.spin(node)

    # 嵌入到 test.py 中（直接传 topic，无需重复配参）：
        node = PathFollowerClose(
            odom_topic='/zsl1sensor1/odom',
            path_topic='/local_planner/path',
            cmd_topic='/zsl1sensor1/cmd_vel',
        )
    """

    def __init__(self, *,
                 odom_topic: Optional[str] = None,
                 path_topic: Optional[str] = None,
                 cmd_topic:  Optional[str] = None,
                 stop_topic: Optional[str] = None):
        super().__init__('path_follower_close')

        # ── Declare ROS 2 parameters (same names as path_follow.launch.py) ────
        self.declare_parameter('sensorOffsetX',   0.0)
        self.declare_parameter('sensorOffsetY',   0.0)
        self.declare_parameter('lookAheadDis',    0.5)
        self.declare_parameter('yawRateGain',     7.5)
        self.declare_parameter('stopYawRateGain', 7.5)
        self.declare_parameter('maxYawRate',      45.0)
        self.declare_parameter('maxSpeed',        1.0)
        self.declare_parameter('maxAccel',        1.0)
        self.declare_parameter('twoWayDrive',     True)
        self.declare_parameter('stopDisThre',     0.2)
        self.declare_parameter('slowDwnDisThre',  1.0)
        self.declare_parameter('dirDiffThre',     0.1)
        self.declare_parameter('alignYaw',        False)
        self.declare_parameter('autoStopWhenDone', True)
        self.declare_parameter('odomTopic',       '/zsl1sensor1/mid360_mid/gazebo_gt/odometry')
        self.declare_parameter('pathTopic',       '/local_planner/path')
        self.declare_parameter('cmdTopic',        '/zsl1sensor1/cmd_vel')
        self.declare_parameter('stopTopic',       '/path_follow_stop')

        def _p(name):
            return self.get_parameter(name).value

        # ── Control parameters ────────────────────────────────────────────────
        self.sensor_offset_x     = float(_p('sensorOffsetX'))
        self.sensor_offset_y     = float(_p('sensorOffsetY'))
        self.look_ahead_dis      = float(_p('lookAheadDis'))
        self.yaw_rate_gain       = float(_p('yawRateGain'))
        self.stop_yaw_rate_gain  = float(_p('stopYawRateGain'))
        self.max_yaw_rate_deg    = float(_p('maxYawRate'))
        self.max_speed           = float(_p('maxSpeed'))
        self.max_accel           = float(_p('maxAccel'))
        self.two_way_drive       = bool(_p('twoWayDrive'))
        self.stop_dis_thre       = float(_p('stopDisThre'))
        self.slow_down_dis_thre  = float(_p('slowDwnDisThre'))
        self.dir_diff_thre       = float(_p('dirDiffThre'))
        self.align_yaw           = bool(_p('alignYaw'))
        self.auto_stop_when_done = bool(_p('autoStopWhenDone'))

        # 构造参数优先；未传则使用 ROS 2 参数服务器的值（可通过 --ros-args 或 launch 覆盖）
        self.odom_topic  = odom_topic  if odom_topic  is not None else str(_p('odomTopic'))
        self.path_topic  = path_topic  if path_topic  is not None else str(_p('pathTopic'))
        self.cmd_topic   = cmd_topic   if cmd_topic   is not None else str(_p('cmdTopic'))
        self.stop_topic  = stop_topic  if stop_topic  is not None else str(_p('stopTopic'))

        # ── Internal state ────────────────────────────────────────────────────
        self._vehicle_x   = 0.0
        self._vehicle_y   = 0.0
        self._vehicle_yaw = 0.0

        self._vehicle_x_rec   = 0.0
        self._vehicle_y_rec   = 0.0
        self._vehicle_yaw_rec = 0.0

        self._path: Path | None = None
        self._path_init     = False
        self._path_point_id = 0
        self._current_v     = 0.0
        self._current_w     = 0.0
        self._safety_stop   = 0
        self._done          = False

        # ── Publishers / Subscribers ──────────────────────────────────────────
        # path 订阅使用 TRANSIENT_LOCAL，以便接收发布者发出的锁存消息
        # （当 test.py 先发路径、后启动闭环控制器时，必须匹配 QoS 才能收到）
        from rclpy.qos import QoSProfile, DurabilityPolicy
        path_qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)

        self._pub_cmd = self.create_publisher(Twist, self.cmd_topic, 10)
        self.create_subscription(Odometry, self.odom_topic, self._odom_cb, 10)
        self.create_subscription(Path, self.path_topic, self._path_cb, path_qos)
        self.create_subscription(Int8, self.stop_topic, self._stop_cb, 5)

        # ── 100 Hz control timer ──────────────────────────────────────────────
        self._timer = self.create_timer(0.01, self._control_loop)

        self.get_logger().info('[PathFollowerClose] Started.')
        self.get_logger().info(f'  odom : {self.odom_topic}')
        self.get_logger().info(f'  path : {self.path_topic}')
        self.get_logger().info(f'  cmd  : {self.cmd_topic}')
        self.get_logger().info(
            f'  lookAheadDis={self.look_ahead_dis:.2f}'
            f'  maxSpeed={self.max_speed:.2f}'
            f'  maxAccel={self.max_accel:.2f}'
        )

    # ── Callbacks ──────────────────────────────────────────────────────────────

    def _odom_cb(self, msg: Odometry):
        q = msg.pose.pose.orientation
        yaw = Rotation.from_quat([q.x, q.y, q.z, q.w]).as_euler('xyz')[2]
        self._vehicle_yaw = yaw
        self._vehicle_x = (msg.pose.pose.position.x
                           - math.cos(yaw) * self.sensor_offset_x
                           + math.sin(yaw) * self.sensor_offset_y)
        self._vehicle_y = (msg.pose.pose.position.y
                           - math.sin(yaw) * self.sensor_offset_x
                           - math.cos(yaw) * self.sensor_offset_y)

    def _path_cb(self, msg: Path):
        if not msg.poses:
            self.get_logger().warn(
                '[PathFollowerClose] Received empty path, ignored.', throttle_duration_sec=1.0)
            return
        self._path            = msg
        self._vehicle_x_rec   = self._vehicle_x
        self._vehicle_y_rec   = self._vehicle_y
        self._vehicle_yaw_rec = self._vehicle_yaw
        self._path_point_id   = 0
        self._path_init       = True
        self.get_logger().info(
            f'[PathFollowerClose] Path received: {len(msg.poses)} poses.')

    def _stop_cb(self, msg: Int8):
        self._safety_stop = msg.data

    # ── 100 Hz control loop ────────────────────────────────────────────────────

    def _control_loop(self):
        if not self._path_init:
            self.get_logger().warn(
                '[PathFollowerClose] No path set.', throttle_duration_sec=1.0)
            return
        if not self._path or not self._path.poses:
            self.get_logger().warn(
                '[PathFollowerClose] Path is empty.', throttle_duration_sec=1.0)
            return

        # ── Step 1: current position in path-origin frame ──────────────────────
        dx = self._vehicle_x - self._vehicle_x_rec
        dy = self._vehicle_y - self._vehicle_y_rec
        c  = math.cos(self._vehicle_yaw_rec)
        s  = math.sin(self._vehicle_yaw_rec)
        veh_x_rel =  c * dx + s * dy
        veh_y_rel = -s * dx + c * dy

        poses     = self._path.poses
        path_size = len(poses)

        # ── Step 2: distance to end ────────────────────────────────────────────
        end_dis = math.hypot(
            poses[-1].pose.position.x - veh_x_rel,
            poses[-1].pose.position.y - veh_y_rel,
        )

        # ── Step 3: advance look-ahead index ──────────────────────────────────
        while self._path_point_id < path_size - 1:
            p_x = poses[self._path_point_id].pose.position.x - veh_x_rel
            p_y = poses[self._path_point_id].pose.position.y - veh_y_rel
            if math.hypot(p_x, p_y) < self.look_ahead_dis:
                self._path_point_id += 1
            else:
                break

        p_x = poses[self._path_point_id].pose.position.x - veh_x_rel
        p_y = poses[self._path_point_id].pose.position.y - veh_y_rel
        dis = math.hypot(p_x, p_y)

        # ── Step 4: desired heading in path-origin frame ───────────────────────
        if self.align_yaw and end_dis < self.stop_dis_thre:
            qo = poses[-1].pose.orientation
            target_yaw_global = Rotation.from_quat(
                [qo.x, qo.y, qo.z, qo.w]).as_euler('xyz')[2]
            path_dir = target_yaw_global - self._vehicle_yaw_rec
        else:
            path_dir = math.atan2(p_y, p_x)

        dir_diff = self._vehicle_yaw - self._vehicle_yaw_rec - path_dir
        while dir_diff >  math.pi: dir_diff -= 2.0 * math.pi
        while dir_diff < -math.pi: dir_diff += 2.0 * math.pi

        # ── Step 5: two-way drive ──────────────────────────────────────────────
        nav_fwd = True
        if self.two_way_drive and abs(dir_diff) > math.pi / 2.0:
            if (self.align_yaw and end_dis >= self.stop_dis_thre) or (not self.align_yaw):
                nav_fwd = False
                dir_diff += (-math.pi if dir_diff > 0 else math.pi)

        # ── Step 6: target speed ───────────────────────────────────────────────
        if path_size <= 1:
            target_speed = 0.0
        elif end_dis < self.slow_down_dis_thre:
            target_speed = self.max_speed * (end_dis / self.slow_down_dis_thre)
        else:
            target_speed = self.max_speed
        if not nav_fwd:
            target_speed = -target_speed

        # ── Step 7: speed ramp ─────────────────────────────────────────────────
        accel_step = self.max_accel / 100.0
        if abs(dir_diff) < self.dir_diff_thre and dis > self.stop_dis_thre:
            if self._current_v < target_speed:
                self._current_v = min(self._current_v + accel_step, target_speed)
            elif self._current_v > target_speed:
                self._current_v = max(self._current_v - accel_step, target_speed)
        else:
            if self._current_v > 0.0:
                self._current_v = max(0.0, self._current_v - accel_step)
            elif self._current_v < 0.0:
                self._current_v = min(0.0, self._current_v + accel_step)

        # ── Step 8: yaw rate ───────────────────────────────────────────────────
        stop_speed_thresh = 2.0 * accel_step
        if abs(self._current_v) < stop_speed_thresh:
            self._current_w = -self.stop_yaw_rate_gain * dir_diff
        else:
            self._current_w = -self.yaw_rate_gain * dir_diff

        max_w_rad = self.max_yaw_rate_deg * math.pi / 180.0
        self._current_w = max(-max_w_rad, min(self._current_w, max_w_rad))

        # ── Step 9: safety stop ────────────────────────────────────────────────
        if self._safety_stop >= 1:
            self._current_v = 0.0
        if self._safety_stop >= 2:
            self._current_w = 0.0

        # ── Step 10: end-of-path detection ────────────────────────────────────
        accel_step_check = self.max_accel / 100.0
        stop_speed_thresh_check = 2.0 * accel_step_check
        if (self.auto_stop_when_done
                and end_dis < self.stop_dis_thre
                and abs(self._current_v) < stop_speed_thresh_check
                and not self._done):
            self._done = True
            self._current_v = 0.0
            self._current_w = 0.0
            self.get_logger().info('[PathFollowerClose] Path completed. Publishing zero cmd_vel.')
            self._pub_cmd.publish(Twist())
            self._timer.cancel()
            return

        # ── Step 11: publish ───────────────────────────────────────────────────
        cmd = Twist()
        cmd.linear.x  = self._current_v
        cmd.angular.z = self._current_w
        self._pub_cmd.publish(cmd)

    # ── Public helpers ─────────────────────────────────────────────────────────

    def stop(self):
        """Publish a zero-velocity command and cancel the timer cleanly."""
        self._timer.cancel()
        self._pub_cmd.publish(Twist())
        self.get_logger().info('[PathFollowerClose] Stopped.')


def main(args=None):
    rclpy.init(args=args)
    node = PathFollowerClose()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.stop()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
