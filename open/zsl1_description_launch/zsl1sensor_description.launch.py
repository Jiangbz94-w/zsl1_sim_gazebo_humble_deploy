"""多机器人 spawn launch（可扩展到任意数量的 zsl1sensorN）。

新增机器人只需在 SENSORS 列表追加一项，无需改其它代码。

注：之前 gazebo_ros 同进程多 model 会互相污染 plugin 节点 ns（导致 sensor2 的
camera/laser/imu topic 落到 sensor1 ns 下）。现已通过在 sensor_gazebo.xacro /
zsl1_gazebo.xacro 中改用 *绝对路径 <remapping>* 修复，topic 名不再依赖 plugin
节点 ns，因此可以安全并行 spawn。
"""

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


# ============================================================
# 机器人清单：增删机器人只改这里
# ============================================================
SENSORS = [
    {"name": "zsl1sensor1", "default_x": "0", "default_y": "0", "default_z": "0.45"},
    {"name": "zsl1sensor2", "default_x": "0", "default_y": "0", "default_z": "0.45"},
    # 示例：要新增 sensor3 / sensor4，仅需追加：
    # {"name": "zsl1sensor3", "default_x": "4", "default_y": "0", "default_z": "0.45"},
    # {"name": "zsl1sensor4", "default_x": "0", "default_y": "4", "default_z": "0.45"},
]


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
                # 把 RSP 默认订阅的 'joint_states'（即 /<name>/joint_states）
                # remap 到全局汇总 topic /joint_states_all。
                # 原因：ros2_control 的 controller LifecycleNode 会被 rclcpp 全局 args
                # 污染 ns，导致所有 robot 的 joint_state_broadcaster 都发到同一个错误
                # ns。我们用 zsl1_TFpub_rviz launch 里的 1 个 topic_tools relay 把那个
                # 错误位置的 joint_states 镜像到 /joint_states_all；每个 RSP 用各自
                # URDF 自动过滤本机器人的 joint，互不干扰。
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
    for cfg in SENSORS:
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
