#!/usr/bin/env python3
"""joint_states_merge_relay.py

为什么需要这个节点（请勿删除注释，记录关键 upstream 缺陷）：

ros2_control humble 在「同一 gzserver 进程内加载多个 controller_manager」时，
后加载的 cm 内部创建的 controller LifecycleNode 会复用第一个 cm 创建时被
rclcpp 缓存的 default node arguments / namespace，使所有 robot 的
joint_state_broadcaster 都把 sensor_msgs/JointState 发到「最先加载的 cm 的
namespace」下，而不是各自的 /<robot_ns>/joint_states。具体表现：
    pub:  /<first_ns>/joint_states  ← 含两台机器人各自 12 个关节的两条独立消息
    pub:  /<other_ns>/joint_states  ← 0
而且「first_ns」是哪一个取决于 spawn_entity 的并发顺序，不可靠。

这是 ros2_control / gazebo_ros2_control 在 humble 下的已知缺陷
（cm 内部 LifecycleNode 的 NodeOptions 处理）。在不 fork 上游、也不
拆成多 gzserver 进程的前提下，无法在源码层面彻底修复。

本节点的职责：
  * 同时订阅所有候选 /<robot_ns>/joint_states 输入 topic（哪一个有数据
    取决于本次 run 的 cm spawn 顺序），用 RELIABLE QoS（与 broadcaster
    端一致），把消息原样转发到统一的 /joint_states_all。
  * RSP 通过 launch 中的 remap 订阅 /joint_states_all，按各自 URDF 的
    joint name 自动过滤本机器人的 joint。

为什么不用 topic_tools::relay：humble 版的 relay 用 SensorDataQoS
(BEST_EFFORT) 订阅 + 发布，而 robot_state_publisher 默认用 RELIABLE
订阅，导致 QoS 不匹配，订阅端收到 "A message was lost" 但拿不到数据。

参数:
  input_topics  (string[])  待合并的 joint_states 输入 topic 列表
  output_topic  (string)    汇总输出 topic，默认 /joint_states_all
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from sensor_msgs.msg import JointState


class JointStatesMergeRelay(Node):
    def __init__(self):
        super().__init__("joint_states_merge_relay")

        self.declare_parameter("input_topics", [""])
        self.declare_parameter("output_topic", "/joint_states_all")

        input_topics = [
            t for t in self.get_parameter("input_topics")
                          .get_parameter_value().string_array_value
            if t
        ]
        output_topic = self.get_parameter("output_topic").value

        if not input_topics:
            self.get_logger().error("input_topics is empty; nothing to relay")
            return

        # 必须 RELIABLE，对齐 joint_state_broadcaster (SystemDefaultsQoS)
        # 和 robot_state_publisher (默认 RELIABLE) 两端
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=20,
            durability=DurabilityPolicy.VOLATILE,
        )

        self.pub = self.create_publisher(JointState, output_topic, qos)

        self.subs = []
        for t in input_topics:
            sub = self.create_subscription(
                JointState, t,
                lambda msg, src=t: self._on_msg(msg, src),
                qos,
            )
            self.subs.append(sub)
            self.get_logger().info(f"relay {t} -> {output_topic}")

    def _on_msg(self, msg: JointState, src: str):
        # 直接转发；joint name 已被 ros2_control 自动加上各自机器人的前缀，
        # 不会冲突，下游 RSP 自行按 URDF 过滤
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = JointStatesMergeRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
