"""多机器人 spawn launch（机器人清单由同目录 robots_config.py 统一管理）。

新增/删除机器人只需修改 robots_config.py，本文件无需改动。

注：之前 gazebo_ros 同进程多 model 会互相污染 plugin 节点 ns（导致 sensor2 的
camera/laser/imu topic 落到 sensor1 ns 下）。现已通过在 sensor_gazebo.xacro /
zsl1_gazebo.xacro 中改用 *绝对路径 <remapping>* 修复，topic 名不再依赖 plugin
节点 ns，因此可以安全并行 spawn。
"""

import os as _os
import sys as _sys

# 从同目录读取统一机器人配置（容器内路径：/workspace/src/zsl1/zsl1_gazebo/launch/）
_sys.path.insert(0, _os.path.dirname(__file__))
from robots_config import ROBOTS  # noqa: E402

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.conditions import IfCondition
from launch.substitutions import (
    LaunchConfiguration,
    Command,
    FindExecutable,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue


def _make_robot_description(name: str) -> ParameterValue:
    """xacro -> URDF (string)。"""
    return ParameterValue(
        Command([
            FindExecutable(name="bash"), ' -c "',
            FindExecutable(name="xacro"), " ",
            PathJoinSubstitution([
                FindPackageShare("zsl1_description"), "xacro", f"{name}.xacro"
            ]),
            f" robot_namespace:={name}",
            " parameters_file:=",
            PathJoinSubstitution([
                FindPackageShare("zsl1_description"), "config", f"{name}_control.yaml"
            ]),
            r" | perl -0pe 's/<\?xml[^>]*>\s*//; s/<!--.*?-->\s*//gs'",
            '"',
        ]),
        value_type=str,
    )


def _make_robot_group(cfg: dict) -> GroupAction:
    name = cfg["name"]
    return GroupAction(
        condition=IfCondition(LaunchConfiguration(f"enable_{name}")),
        actions=[
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="robot_state_publisher",
                namespace=name,
                output="screen",
                remappings=[("joint_states", "/joint_states_all")],
                parameters=[{
                    "robot_description": _make_robot_description(name),
                    "use_sim_time": True,
                }],
            ),
            Node(
                package="gazebo_ros",
                executable="spawn_entity.py",
                name=f"spawn_{name}",
                output="screen",
                arguments=[
                    "-topic",  f"/{name}/robot_description",
                    "-entity", name,
                    "-x", LaunchConfiguration(f"{name}_x"),
                    "-y", LaunchConfiguration(f"{name}_y"),
                    "-z", LaunchConfiguration(f"{name}_z"),
                ],
            ),
        ],
    )


def generate_launch_description():
    declare_args = []
    groups = []
    for cfg in ROBOTS:
        name = cfg["name"]
        declare_args += [
            DeclareLaunchArgument(
                f"enable_{name}", default_value="true",
                description=f"是否 spawn {name}"),
            DeclareLaunchArgument(
                f"{name}_x", default_value=cfg["default_x"],
                description=f"{name} spawn x"),
            DeclareLaunchArgument(
                f"{name}_y", default_value=cfg["default_y"],
                description=f"{name} spawn y"),
            DeclareLaunchArgument(
                f"{name}_z", default_value=cfg["default_z"],
                description=f"{name} spawn z"),
        ]
        groups.append(_make_robot_group(cfg))

    return LaunchDescription([*declare_args, *groups])
