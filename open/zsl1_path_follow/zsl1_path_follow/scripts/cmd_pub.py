#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File    : cmd_pub.py
@Author  : kunpeng fan
@Brief   : Receive the actions, then publish.
@License : Copyright (c) 2026. Licensed under the MIT License.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

from typing import List, Tuple


class CmdVelPublisher(Node):
    def __init__(self,
                 freq: int,
                 cmd_topic: str = '/zsl1sensor1/cmd_vel'):
        super().__init__('cmd_vel_publisher_node')

        self.time_period = 1.0 / freq
        self.cmd_topic = cmd_topic
        self.actions_buffer: List[Tuple[float, float]] = []

        self.publisher_ = self.create_publisher(Twist, self.cmd_topic, 10)
        self.timer = self.create_timer(self.time_period, self.timer_callback)

    def timer_callback(self):
        if len(self.actions_buffer) == 0:
            self.get_logger().debug('No action, pass.')
        else:
            v, w = self.actions_buffer[0]
            self.actions_buffer.pop(0)

            msg = Twist()
            msg.linear.x = float(v)
            msg.linear.y = 0.0
            msg.linear.z = 0.0
            msg.angular.x = 0.0
            msg.angular.y = 0.0
            msg.angular.z = float(w)

            self.publisher_.publish(msg)
            self.get_logger().info(
                f'Publishing: linear_x={msg.linear.x:.3f}, angular_z={msg.angular.z:.3f}'
            )

    def set_actions(self, actions: List[Tuple[float, float]]) -> None:
        self.actions_buffer = list(actions)


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelPublisher(freq=10)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
