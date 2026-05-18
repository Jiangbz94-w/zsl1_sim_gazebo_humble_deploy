"""顶层 Gazebo launch — 通过 scene 参数切换场景预设。

用法:
  ros2 launch zsl1_gazebo zsl1_gazebo.launch.py scene:=empty
  ros2 launch zsl1_gazebo zsl1_gazebo.launch.py scene:=study_room
  ros2 launch zsl1_gazebo zsl1_gazebo.launch.py scene:=colored_balls
  ros2 launch zsl1_gazebo zsl1_gazebo.launch.py scene:=colored_balls_arc
  ros2 launch zsl1_gazebo zsl1_gazebo.launch.py scene:=letter_cubes_arc
  ros2 launch zsl1_gazebo zsl1_gazebo.launch.py scene:=tunnel_arc
  ros2 launch zsl1_gazebo zsl1_gazebo.launch.py scene:=stair_climb
  ros2 launch zsl1_gazebo zsl1_gazebo.launch.py scene:=isaaclab_train
  ros2 launch zsl1_gazebo zsl1_gazebo.launch.py scene:=obstacle_course
"""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare


# ============================================================
# 场景预设：每个场景指定世界文件和机器人初始位置
# 新增场景：在此 dict 追加一项即可，无需改其余代码
# ============================================================
SCENE_PRESETS = {
    "empty": {
        "world": "empty_state.world",
        "sensors": [
            {"name": "zsl1sensor1", "x": "0.0", "y": "0.0", "z": "0.45", "enable": True},
            {"name": "zsl1sensor2", "x": "0.0", "y": "0.0", "z": "0.45", "enable": False},
        ],
    },
    "study_room": {
        "world": "study_room.world",
        "sensors": [
            {"name": "zsl1sensor1", "x": "7.5", "y": "7.5", "z": "0.45", "enable": True},
            {"name": "zsl1sensor2", "x": "7.5", "y": "4.5", "z": "0.45", "enable": False},
        ],
    },
    "colored_balls": {
        "world": "colored_balls.world",
        "sensors": [
            {"name": "zsl1sensor1", "x": "0.0", "y": "0.0", "z": "0.45", "enable": True},
            {"name": "zsl1sensor2", "x": "0.0", "y": "0.0", "z": "0.45", "enable": False},
        ],
    },
    "colored_balls_arc": {
        "world": "colored_balls_arc.world",
        "sensors": [
            {"name": "zsl1sensor1", "x": "0.0", "y": "0.0", "z": "0.45", "enable": True},
            {"name": "zsl1sensor2", "x": "0.0", "y": "0.0", "z": "0.45", "enable": False},
        ],
    },
    "letter_cubes_arc": {
        "world": "letter_cubes_arc.world",
        "sensors": [
            {"name": "zsl1sensor1", "x": "0.0", "y": "0.0", "z": "0.45", "enable": True},
            {"name": "zsl1sensor2", "x": "0.0", "y": "0.0", "z": "0.45", "enable": False},
        ],
    },
    "tunnel_arc": {
        "world": "tunnel_arc.world",
        "sensors": [
            {"name": "zsl1sensor1", "x": "0.0", "y": "0.0", "z": "0.45", "enable": True},
            {"name": "zsl1sensor2", "x": "0.0", "y": "0.0", "z": "0.45", "enable": False},
        ],
    },
    "stair_climb": {
        "world": "stair_climb.world",
        "sensors": [
            {"name": "zsl1sensor1", "x": "0.0", "y": "0.0", "z": "0.45", "enable": True},
            {"name": "zsl1sensor2", "x": "0.0", "y": "0.0", "z": "0.45", "enable": False},
        ],
    },
    "isaaclab_train": {
        "world": "isaaclab_train.world",
        "sensors": [
            {"name": "zsl1sensor1", "x": "0.0", "y": "0.0", "z": "0.45", "enable": True},
            {"name": "zsl1sensor2", "x": "0.0", "y": "0.0", "z": "0.45", "enable": False},
        ],
    },
    "obstacle_course": {
        "world": "obstacle_course.world",
        "sensors": [
            {"name": "zsl1sensor1", "x": "0.0", "y": "0.0", "z": "0.45", "enable": True},
            {"name": "zsl1sensor2", "x": "0.0", "y": "0.0", "z": "0.45", "enable": False},
        ],
    },
}

# description launch 需要覆盖所有可能的机器人名称
ALL_SENSOR_NAMES = ["zsl1sensor1", "zsl1sensor2"]


def _launch_setup(context, *args, **kwargs):
    scene = LaunchConfiguration('scene').perform(context)
    if scene not in SCENE_PRESETS:
        raise ValueError(
            f"Unknown scene '{scene}'. Available: {list(SCENE_PRESETS)}"
        )
    preset = SCENE_PRESETS[scene]
    sensors_map = {s["name"]: s for s in preset["sensors"]}

    world_pkg = FindPackageShare('zsl1_world').perform(context)
    world_path = os.path.join(world_pkg, 'worlds', preset['world'])

    forwarded = {
        'use_sim_time': LaunchConfiguration('use_sim_time').perform(context),
        'gui':          LaunchConfiguration('gui').perform(context),
        'pause':        LaunchConfiguration('pause').perform(context),
        'world':        world_path,
    }

    for name in ALL_SENSOR_NAMES:
        s = sensors_map.get(name, {})
        forwarded[f'enable_{name}'] = 'true' if s.get('enable', False) else 'false'
        forwarded[f'{name}_x'] = s.get('x', '0.0')
        forwarded[f'{name}_y'] = s.get('y', '0.0')
        forwarded[f'{name}_z'] = s.get('z', '0.45')

    world_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('zsl1_world'), 'launch', 'zsl1_world.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': forwarded['use_sim_time'],
            'gui':          forwarded['gui'],
            'pause':        forwarded['pause'],
            'world':        forwarded['world'],
        }.items()
    )

    description_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('zsl1_description'), 'launch', 'zsl1sensor_description.launch.py'
            ])
        ]),
        launch_arguments=forwarded.items()
    )

    return [world_launch, description_launch]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'scene', default_value='empty',
            description=f'场景预设: {" | ".join(SCENE_PRESETS)}'),
        DeclareLaunchArgument(
            'use_sim_time', default_value='true',
            description='Use simulation clock'),
        DeclareLaunchArgument(
            'gui', default_value='true',
            description='Launch Gazebo GUI (gzclient)'),
        DeclareLaunchArgument(
            'pause', default_value='false',
            description='Start Gazebo with physics paused'),
        OpaqueFunction(function=_launch_setup),
    ])