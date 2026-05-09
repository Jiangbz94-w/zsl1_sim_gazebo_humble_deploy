"""robots_config.py — 机器人实例配置，唯一入口。

调整机器人数量只需修改本文件的 ROBOTS 列表：
  • 新增机器人：追加一项（取消下方注释中的示例）
  • 减少机器人：注释或删除对应行

ROBOTS 中的每一项同时被以下三个 launch 文件读取：
  • zsl1_gazebo.launch.py          ── 决定 Gazebo 中 spawn 哪些机器人及初始位姿
  • zsl1sensor_description.launch.py ── 决定启动哪些 robot_state_publisher
  • zsl1sensor_control.launch.py   ── 决定启动哪些 locomotion_sim 控制节点

字段说明：
  name            机器人 Gazebo entity 名，同时作为 ROS namespace
  default_x/y/z  spawn 初始位姿（字符串，单位 m）
  keyboard_master 只能有一台为 True，负责读 stdin 并广播到 /zsl1_keyboard
  joy_dev         手柄设备路径（enable_joy:=true 时生效）
  enable_default  "true"/"false"，对应 ros2 launch 的 enable_<name> 参数默认值
  policy_default  策略子目录名（policy/<robot_name>/<policy_default>/）
  startup_delay   控制节点的延迟启动时间（秒），给 Gazebo 留出加载时间
"""

ROBOTS = [
    {
        "name": "zsl1sensor1",
        "default_x": "7.5", "default_y": "7.5", "default_z": "0.45",
        "keyboard_master": True,
        "joy_dev": "/dev/input/js0",
        "enable_default": "true",
        "policy_default": "wya_lab",
        "startup_delay": 0.0,
    },
    # {
    #     "name": "zsl1sensor2",
    #     "default_x": "7.5", "default_y": "4.5", "default_z": "0.45",
    #     "keyboard_master": False,
    #     "joy_dev": "/dev/input/js1",
    #     "enable_default": "true",
    #     "policy_default": "wya_lab",
    #     "startup_delay": 3.0,
    # },
    # 新增 sensor3 示例，取消注释即可（同时确保 policy/zsl1/zsl1sensor3/ 目录存在）：
    # {
    #     "name": "zsl1sensor3",
    #     "default_x": "4.5", "default_y": "4.5", "default_z": "0.45",
    #     "keyboard_master": False,
    #     "joy_dev": "/dev/input/js2",
    #     "enable_default": "false",
    #     "policy_default": "wya_lab",
    #     "startup_delay": 6.0,
    # },
]
