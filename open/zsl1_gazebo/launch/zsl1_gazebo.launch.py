"""顶层 Gazebo launch（可扩展到任意数量的 zsl1sensorN）。

调整机器人数量：只需修改同目录的 robots_config.py，本文件无需改动。
"""

import os as _os
import sys as _sys

# 从同目录读取统一机器人配置（容器内路径：/workspace/src/zsl1/zsl1_gazebo/launch/）
_sys.path.insert(0, _os.path.dirname(__file__))
from robots_config import ROBOTS  # noqa: E402

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare

SENSORS = ROBOTS  # 保持向下兼容的别名


def generate_launch_description():
    declare_args = [
        DeclareLaunchArgument(
            'use_sim_time', default_value='true',
            description='Use simulation clock'),
        DeclareLaunchArgument(
            'gui', default_value='true',
            description='Launch Gazebo GUI (gzclient)'),
        DeclareLaunchArgument(
            'pause', default_value='false',
            description='Start Gazebo with physics paused until the control node starts motion'),
        DeclareLaunchArgument(
            'world', default_value=PathJoinSubstitution([
                FindPackageShare('zsl1_world'), 'worlds', 'study_room.world'
            ]),
            description='Full path to world file.'),
    ]

    forwarded = {
        'use_sim_time': LaunchConfiguration('use_sim_time'),
        'gui':          LaunchConfiguration('gui'),
        'pause':        LaunchConfiguration('pause'),
        'world':        LaunchConfiguration('world'),
    }

    for cfg in SENSORS:
        name = cfg["name"]
        declare_args += [
            DeclareLaunchArgument(
                f'enable_{name}', default_value='true',
                description=f'是否 spawn {name}'),
            DeclareLaunchArgument(
                f'{name}_x', default_value=cfg["default_x"],
                description=f'{name} spawn x'),
            DeclareLaunchArgument(
                f'{name}_y', default_value=cfg["default_y"],
                description=f'{name} spawn y'),
            DeclareLaunchArgument(
                f'{name}_z', default_value=cfg["default_z"],
                description=f'{name} spawn z'),
        ]
        forwarded[f'enable_{name}'] = LaunchConfiguration(f'enable_{name}')
        forwarded[f'{name}_x']      = LaunchConfiguration(f'{name}_x')
        forwarded[f'{name}_y']      = LaunchConfiguration(f'{name}_y')
        forwarded[f'{name}_z']      = LaunchConfiguration(f'{name}_z')

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
        PythonLaunchDescriptionSource(
            _os.path.join(_os.path.dirname(__file__), 'zsl1sensor_description.launch.py')
        ),
        launch_arguments=forwarded.items()
    )

    return LaunchDescription([
        *declare_args,
        world_launch,
        description_launch,
    ])
