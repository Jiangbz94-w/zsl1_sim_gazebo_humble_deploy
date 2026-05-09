"""
zsl1_rviz.launch.py — ROS 2 Humble

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
功能
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
为每台机器人启动：
  * gt_odom_tf_publisher — 用 mid360 ground-truth 里程计推算 world → BASE_LINK
  * controller_manager spawner — 激活 joint_state_broadcaster，从 ros2_control
                                  读出真实关节角并发布到 /<name>/joint_states，
                                  让 robot_state_publisher 能算出腿部 TF
然后启动一个 rviz2 同时可视化所有机器人。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
扩展方式
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
在文件顶部的 SENSOBOTS 列表里追加一行，即可支持 zsl1sensor3、zsl1sensor4 等，
其余代码无需修改。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
典型用法
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  # 默认两台都开（与 SENSOBOTS 中 enable_default 对齐）
  ros2 launch zsl1_TFpub_rviz zsl1_rviz.launch.py

  # 仅可视化 sensor1
  ros2 launch zsl1_TFpub_rviz zsl1_rviz.launch.py enable_zsl1sensor2:=false

  # 已经在跑 zsl1_control（另一处 spawn 了 broadcaster），别重复 spawn
  ros2 launch zsl1_TFpub_rviz zsl1_rviz.launch.py \
      spawn_jsb_zsl1sensor1:=false spawn_jsb_zsl1sensor2:=false

  # 不开 rviz，仅发布 TF
  ros2 launch zsl1_TFpub_rviz zsl1_rviz.launch.py rviz:=false
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, OpaqueFunction, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

import os
import tempfile

# 每台机器人 group 的颜色（PointCloud / Odom 箭头），列表会循环使用
_COLORS = [
    {"pc": "0; 255; 255",   "odom": "0; 200; 0"},
    {"pc": "255; 200; 0",   "odom": "200; 0; 200"},
    {"pc": "255; 80; 80",   "odom": "80; 80; 255"},
    {"pc": "180; 255; 120", "odom": "255; 140; 0"},
]


def _rviz_group_yaml(name: str, color: dict) -> str:
    """生成单个机器人的 RViz Group YAML 块（4 空格缩进，作为 Displays 子项）。"""
    return f"""    - Class: rviz_common/Group
      Name: {name}
      Enabled: true
      Displays:
        - Alpha: 1
          Class: rviz_default_plugins/RobotModel
          Description Source: Topic
          Description Topic:
            Depth: 5
            Durability Policy: Transient Local
            History Policy: Keep Last
            Reliability Policy: Reliable
            Value: /{name}/robot_description
          Enabled: true
          Name: RobotModel ({name})
          Visual Enabled: true
          Collision Enabled: false

        - Alpha: 1
          Autocompute Intensity Bounds: true
          Autocompute Value Bounds: {{ Max Value: 5, Min Value: -5, Value: true }}
          Axis: Z
          Channel Name: intensity
          Class: rviz_default_plugins/PointCloud2
          Color: {color['pc']}
          Color Transformer: AxisColor
          Enabled: true
          Name: Mid360 Points ({name})
          Position Transformer: XYZ
          Selectable: true
          Size (Pixels): 2
          Size (m): 0.02
          Style: Points
          Topic:
            Depth: 5
            Durability Policy: Volatile
            History Policy: Keep Last
            Reliability Policy: Reliable
            Value: /{name}/mid360_mid/points
          Use Fixed Frame: true
          Use rainbow: true
          Value: true

        - Class: rviz_default_plugins/Odometry
          Covariance: {{ Value: false }}
          Enabled: true
          Keep: 100
          Name: Mid360 GT Odom ({name})
          Position Tolerance: 0.1
          Angle Tolerance: 0.1
          Shape:
            Alpha: 1
            Color: {color['odom']}
            Head Length: 0.1
            Head Radius: 0.05
            Shaft Length: 0.3
            Shaft Radius: 0.02
            Value: Arrow
          Topic:
            Depth: 10
            Durability Policy: Volatile
            History Policy: Keep Last
            Reliability Policy: Best Effort
            Value: /{name}/mid360_mid/gazebo_gt/odometry
          Value: true

        - Class: rviz_default_plugins/Image
          Enabled: true
          Max Value: 1
          Median window: 5
          Min Value: 0
          Name: Camera Front ({name})
          Normalize Range: true
          Topic:
            Depth: 5
            Durability Policy: Volatile
            History Policy: Keep Last
            Reliability Policy: Reliable
            Value: /{name}/camera_front/camera/image_raw
          Value: true
"""


def _generate_rviz_config(active_names: list) -> str:
    """根据启用的机器人列表生成 .rviz 文件，返回路径。"""
    panels_displays = "\n".join(
        f"        - /{n}1" for n in active_names
    )
    groups_yaml = "\n".join(
        _rviz_group_yaml(n, _COLORS[i % len(_COLORS)])
        for i, n in enumerate(active_names)
    )

    config = f"""Panels:
  - Class: rviz_common/Displays
    Help Height: 0
    Name: Displays
    Property Tree Widget:
      Expanded:
        - /Global Options1
        - /TF1
{panels_displays}
      Splitter Ratio: 0.5
    Tree Height: 700
  - Class: rviz_common/Selection
    Name: Selection
  - Class: rviz_common/Tool Properties
    Name: Tool Properties
  - Class: rviz_common/Views
    Name: Views
Visualization Manager:
  Class: ""
  Displays:
    - Alpha: 0.5
      Cell Size: 1
      Class: rviz_default_plugins/Grid
      Color: 160; 160; 164
      Enabled: true
      Line Style: {{ Line Width: 0.03, Value: Lines }}
      Name: Grid
      Normal Cell Count: 0
      Offset: {{ X: 0, Y: 0, Z: 0 }}
      Plane: XY
      Plane Cell Count: 20
      Reference Frame: <Fixed Frame>
      Value: true

    - Class: rviz_default_plugins/TF
      Enabled: true
      Frame Timeout: 15
      Frames: {{ All Enabled: false }}
      Marker Scale: 0.5
      Name: TF
      Show Arrows: true
      Show Axes: true
      Show Names: false
      Tree: {{}}
      Update Interval: 0
      Value: true

{groups_yaml}
  Enabled: true
  Global Options:
    Background Color: 48; 48; 48
    Fixed Frame: world
    Frame Rate: 30
  Name: root
  Tools:
    - Class: rviz_default_plugins/MoveCamera
    - Class: rviz_default_plugins/Select
    - Class: rviz_default_plugins/FocusCamera
    - Class: rviz_default_plugins/Measure
  Transformation:
    Current: {{ Class: rviz_default_plugins/TF }}
  Value: true
  Views:
    Current:
      Class: rviz_default_plugins/Orbit
      Distance: 6.0
      Enable Stereo Rendering: {{ Value: false }}
      Focal Point: {{ X: 0, Y: 0, Z: 0 }}
      Focal Shape Fixed Size: true
      Focal Shape Size: 0.05
      Invert Z Axis: false
      Name: Current View
      Near Clip Distance: 0.01
      Pitch: 0.6
      Target Frame: <Fixed Frame>
      Value: Orbit (rviz)
      Yaw: 0.785
    Saved: ~
Window Geometry:
  Displays: {{ collapsed: false }}
  Height: 900
  Hide Left Dock: false
  Hide Right Dock: false
  Width: 1500
  X: 100
  Y: 100
"""
    fd, path = tempfile.mkstemp(prefix="zsl1_rviz_", suffix=".rviz")
    with os.fdopen(fd, "w") as f:
        f.write(config)
    return path

# =====================================================================
# 在此处添加/删除/注释机器人实例，其余代码无需修改
#   name           : 机器人命名空间
#   enable_default : 默认是否启动该实例的 TF / spawner 节点（"true" / "false"）
#   spawn_jsb      : 默认是否 spawn joint_state_broadcaster（别处已 spawn 时设 "false"）
# =====================================================================
SENSOBOTS = [
    {"name": "zsl1sensor1", "enable_default": "true",  "spawn_jsb": "true"},
    {"name": "zsl1sensor2", "enable_default": "true",  "spawn_jsb": "true"},
    # {"name": "zsl1sensor3", "enable_default": "false", "spawn_jsb": "true"},
    # {"name": "zsl1sensor4", "enable_default": "false", "spawn_jsb": "true"},
]


def _spawn_jsb_script(name: str) -> str:
    """Bash 脚本：容错地激活 joint_state_broadcaster。

    cm 节点 ns 由 zsl1_gazebo.xacro 的 ros2_control plugin 显式 <namespace> 决定，
    现在所有 gazebo_ros 插件都已显式声明 <namespace>，gazebo_ros::Node::Get() 的
    default_ns_ 缓存不再被污染，broadcaster 会落到正确的 /<name> ns 下。
    """
    return f"""
CM=/{name}/controller_manager
if ros2 control list_controllers -c $CM 2>/dev/null | grep -q 'joint_state_broadcaster.*active'; then
  echo '[{name}_jsb] already active, skip spawn'
  exit 0
fi
if ros2 run controller_manager spawner joint_state_broadcaster -c $CM; then
  exit 0
fi
echo '[{name}_jsb] spawn failed, try unload + respawn'
ros2 service call $CM/unload_controller controller_manager_msgs/srv/UnloadController '{{name: joint_state_broadcaster}}' >/dev/null 2>&1
sleep 1
ros2 run controller_manager spawner joint_state_broadcaster -c $CM || \
  echo '[{name}_jsb] WARNING: still failed; legs TF will be missing'
"""


def _per_robot_actions(name: str, use_sim_time) -> GroupAction:
    enable_arg = f"enable_{name}"
    spawn_jsb_arg = f"spawn_jsb_{name}"

    return GroupAction(
        condition=IfCondition(LaunchConfiguration(enable_arg)),
        actions=[
            # GT odom → world→BASE_LINK TF
            Node(
                package="zsl1_TFpub_rviz",
                executable="gt_odom_tf_publisher",
                name=f"{name}_gt_odom_tf_publisher",
                output="screen",
                parameters=[{
                    "odometry_topic":  f"/{name}/mid360_mid/gazebo_gt/odometry",
                    "child_frame":     f"{name}/mid360_mid/gazebo_gt/odometry_sensor_link",
                    "base_link_frame": f"{name}/BASE_LINK",
                    "world_frame":     "world",
                    "use_sim_time":    use_sim_time,
                }],
            ),
            # 激活 joint_state_broadcaster：让 controller_manager 把 ros2_control 的
            # 真实关节角发到 /<name>/joint_states，robot_state_publisher 据此算腿部 TF。
            # （zsl1_description 的 control yaml 里已注册该 broadcaster 但未 activate）
            # 容错处理：若已 active 则跳过；若 LoadController 因残留状态失败，先 unload 再 spawn。
            ExecuteProcess(
                cmd=["bash", "-c", _spawn_jsb_script(name)],
                output="screen",
                condition=IfCondition(LaunchConfiguration(spawn_jsb_arg)),
            ),
        ],
    )


def _launch_setup(context, *args, **kwargs):
    """运行时根据 enable_zsl1sensorN 参数动态生成 rviz 配置并启动 rviz2。"""
    use_sim_time_str = LaunchConfiguration("use_sim_time").perform(context)
    use_sim_time = use_sim_time_str.lower() in ("true", "1", "yes")

    active_names = []
    for bot in SENSOBOTS:
        val = LaunchConfiguration(f"enable_{bot['name']}").perform(context).lower()
        if val in ("true", "1", "yes"):
            active_names.append(bot["name"])

    if not active_names:
        return []

    if LaunchConfiguration("rviz").perform(context).lower() not in ("true", "1", "yes"):
        return []

    rviz_cfg_path = _generate_rviz_config(active_names)
    return [Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_cfg_path],
        parameters=[{"use_sim_time": use_sim_time}],
    )]


def generate_launch_description() -> LaunchDescription:
    args = [
        DeclareLaunchArgument(
            "rviz", default_value="true",
            description="是否启动 RViz2"),
        DeclareLaunchArgument(
            "use_sim_time", default_value="true",
            description="使用 Gazebo 的 /clock（与仿真一起跑时保持 true）"),
    ]

    use_sim_time = LaunchConfiguration("use_sim_time")

    # 上游 bug 说明：ros2_control humble 在「同进程内多 controller_manager」
    # 场景下，后加载 cm 内部创建的 controller LifecycleNode 会复用第一个 cm
    # 的 NodeOptions/namespace 缓存，导致所有机器人的 joint_state_broadcaster
    # 把 JointState 全部发到「最先加载的 cm 所在 ns 下」/<first_ns>/joint_states
    # （那条 topic 的 publisher_count = 机器人数；其余 ns 下的 topic 为空）。
    # 而 first_ns 取决于 spawn_entity 的并发顺序，每次 run 都可能不同。
    #
    # 在不 fork 上游、不拆多 gzserver 进程的前提下无法在源码层面根治；
    # 这里用一个自写的 Python 节点 joint_states_merge_relay 同时订阅所有
    # 候选 /<name>/joint_states，用 RELIABLE QoS（与 broadcaster / RSP 两端
    # 一致，避免 topic_tools::relay 默认 SensorDataQoS 造成的 QoS 不匹配）
    # 把消息原样转发到 /joint_states_all。RSP 已 remap 订阅 /joint_states_all，
    # 按各自 URDF 的 joint name 前缀自动过滤本机器人 joint。
    js_merge_relay = Node(
        package="zsl1_TFpub_rviz",
        executable="joint_states_merge_relay.py",
        name="joint_states_merge_relay",
        output="screen",
        parameters=[{
            "input_topics": [f"/{bot['name']}/joint_states" for bot in SENSOBOTS],
            "output_topic": "/joint_states_all",
            "use_sim_time": use_sim_time,
        }],
    )

    groups = []
    for bot in SENSOBOTS:
        name = bot["name"]
        args.append(DeclareLaunchArgument(
            f"enable_{name}",
            default_value=bot["enable_default"],
            description=f"是否为 {name} 启动 TF / joint 节点"))
        args.append(DeclareLaunchArgument(
            f"spawn_jsb_{name}",
            default_value=bot["spawn_jsb"],
            description=(f"{name} 是否自动 spawn joint_state_broadcaster"
                         "（如果其他 launch 已经 spawn 过，设 false 避免重复）")))
        groups.append(_per_robot_actions(name, use_sim_time))

    return LaunchDescription(args + [js_merge_relay] + groups + [OpaqueFunction(function=_launch_setup)])
