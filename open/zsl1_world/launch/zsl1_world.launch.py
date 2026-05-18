import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    # Set GAZEBO_MODEL_PATH so Gazebo can find zsl1_world models
    set_gazebo_model_path = SetEnvironmentVariable(
        name='GAZEBO_MODEL_PATH',
        value=[
            PathJoinSubstitution([FindPackageShare('zsl1_world'), 'models']),
            ':/usr/share/gazebo-11/models',
            ':',
            os.environ.get('GAZEBO_MODEL_PATH', ''),
        ]
    )

    # ==================== Launch Arguments ====================
    declare_args = [
        DeclareLaunchArgument(
            'use_sim_time', default_value='true',
            description='Use simulation clock'),
        DeclareLaunchArgument(
            'gui', default_value='true',
            description='Launch Gazebo GUI (gzclient)'),
        DeclareLaunchArgument(
            'pause', default_value='true',
            description='Start Gazebo with physics paused'),
        DeclareLaunchArgument(
            'world', default_value=PathJoinSubstitution([
                FindPackageShare('zsl1_world'), 'worlds', 'empty_state.world'
            ]),
            description='Full path to world file.'),
        DeclareLaunchArgument(
            'extra_gazebo_args', default_value='',
            description='Extra arguments passed to gzserver.'),
    ]

    # ==================== Gazebo ====================
    gzserver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('gazebo_ros'), 'launch', 'gzserver.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'world':        LaunchConfiguration('world'),
            'pause':        LaunchConfiguration('pause'),
            'extra_gazebo_args': LaunchConfiguration('extra_gazebo_args'),
        }.items()
    )

    gzclient = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('gazebo_ros'), 'launch', 'gzclient.launch.py'
            ])
        ]),
        condition=IfCondition(LaunchConfiguration('gui'))
    )

    return LaunchDescription([
        set_gazebo_model_path,
        *declare_args,
        gzserver,
        gzclient,
    ])