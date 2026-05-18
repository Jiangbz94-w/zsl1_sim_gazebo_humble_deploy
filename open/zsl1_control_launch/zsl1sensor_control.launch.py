"""
zsl1sensor_control.launch.py — ROS 2 Humble

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
扩展方式
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
在文件顶部的 SENSOBOTS 列表里追加一行，即可支持 zsl1sensor3、zsl1sensor4 等，
其余代码无需修改。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
键盘控制（默认模式，enable_joy:=false）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  # 只控制 zsl1sensor1
  ros2 launch zsl1_control zsl1sensor_control.launch.py

  # 同时控制两台（一个键盘同步操控两台）
  ros2 launch zsl1_control zsl1sensor_control.launch.py enable_zsl1sensor2:=true

  # 只控制 zsl1sensor2
  ros2 launch zsl1_control zsl1sensor_control.launch.py \
      enable_zsl1sensor1:=false enable_zsl1sensor2:=true

    # sensor1 使用 robot_lab 策略，sensor2 使用 himloco 策略
  ros2 launch zsl1_control zsl1sensor_control.launch.py \
      enable_zsl1sensor2:=true \
      policy_zsl1sensor1:=robot_lab \
      policy_zsl1sensor2:=himloco

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
手柄控制（enable_joy:=true）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
每台机器人在各自命名空间下启动独立 joy_node，设备路径由 SENSOBOTS 里的
joy_dev 字段指定（默认 js0 / js1），也可通过命令行覆盖。

  # 单手柄控制 zsl1sensor1（手柄插在 /dev/input/js0）
  ros2 launch zsl1_control zsl1sensor_control.launch.py enable_joy:=true

  # 两台各用一个手柄独立控制
  ros2 launch zsl1_control zsl1sensor_control.launch.py \
      enable_zsl1sensor2:=true enable_joy:=true

  # 两台共用同一个手柄（都指向 js0）
  ros2 launch zsl1_control zsl1sensor_control.launch.py \
      enable_zsl1sensor2:=true enable_joy:=true \
      joy_dev_zsl1sensor2:=/dev/input/js0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
键盘多机同步机制
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  - keyboard_master=True  的节点读取 stdin，将键码发布到全局 /zsl1_keyboard
  - keyboard_master=False 的节点订阅 /zsl1_keyboard，不读 stdin
  - SENSOBOTS 列表中只能有一台 keyboard_master=True
  - 多台同时启动时，master 的键盘/手柄命令自动同步到所有 slave
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace

# =====================================================================
# 在此处添加/删除机器人实例，其余代码无需修改
# keyboard_master: 只能有一台为 True（负责读 stdin 并广播键码）
# =====================================================================
SENSOBOTS = [
    {"name": "zsl1sensor1", "keyboard_master": True,  "joy_dev": "/dev/input/js0", "enable_default": "true", "policy_default": "wya_lab", "startup_delay": 0.0},
    {"name": "zsl1sensor2", "keyboard_master": False, "joy_dev": "/dev/input/js1", "enable_default": "false", "policy_default": "wya_lab", "startup_delay": 3.0},
]


def generate_launch_description():

    args = [
        DeclareLaunchArgument(
            "robot_name", default_value="zsl1",
            description="机器人型号，对应 policy/ 目录下的子目录名"),
        DeclareLaunchArgument(
            "enable_joy", default_value="false",
            description="是否为各实例启动独立 joy_node"),
    ]

    groups = []

    for sensobot in SENSOBOTS:
        name   = sensobot["name"]
        master = sensobot["keyboard_master"]
        dev    = sensobot["joy_dev"]
        default_enable = sensobot["enable_default"]
        default_policy = sensobot["policy_default"]
        startup_delay = sensobot.get("startup_delay", 0.0)

        enable_arg = f"enable_{name}"
        policy_arg = f"policy_{name}"

        args.append(DeclareLaunchArgument(
            enable_arg, default_value=default_enable,
            description=f"是否启动 {name} 控制节点"))
        args.append(DeclareLaunchArgument(
            policy_arg, default_value=default_policy,
            description=f"{name} 使用的 RL 策略子目录名（留空则默认 himloco，如 robot_lab / himloco）"))

        enable  = LaunchConfiguration(enable_arg)
        policy  = LaunchConfiguration(policy_arg)
        joy_dev = LaunchConfiguration(f"joy_dev_{name}", default=dev)

        group = GroupAction(
            condition=IfCondition(enable),
            actions=[
                PushRosNamespace(name),
                Node(
                    package="joy",
                    executable="joy_node",
                    name="joy_node",
                    output="screen",
                    condition=IfCondition(LaunchConfiguration("enable_joy")),
                    parameters=[{"dev": joy_dev}],
                ),
                Node(
                    package="zsl1_control",
                    executable="locomotion_sim",
                    name="zsl1_control",
                    output="screen",
                    parameters=[{
                        "robot_name":        LaunchConfiguration("robot_name"),
                        "gazebo_model_name": name,
                        "policy_name":       policy,
                        "keyboard_master":   master,
                    }],
                ),
            ],
        )

        if startup_delay > 0.0:
            groups.append(TimerAction(period=startup_delay, actions=[group]))
        else:
            groups.append(group)

    return LaunchDescription(args + groups)

