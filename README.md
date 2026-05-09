# ZSL-1 仿真环境部署指南

## 环境要求

- Docker（含 NVIDIA Container Toolkit，支持 `--gpus all`）
- NVIDIA 显卡驱动

---

## 第一步：拉取镜像

```bash
docker pull jiangbz/zsl1_sim_gazebo_humble:deploy
```

---

## 第二步：创建并启动容器

```bash
bash docker_start_deploy.sh
```

首次执行会创建容器并挂载 `open/` 目录；  
后续再次执行会直接启动已有容器，不会重新创建。

---

## 第三步：进入容器

```bash
bash docker_join_deploy.sh
```

可多次执行（每次打开一个新终端会话）。

---

## 停止容器

```bash
docker stop zsl1_sim_gazebo_humble_deploy
```

---

## 修改配置

`open/` 目录已挂载到容器内，**在宿主机直接修改文件即时生效**，无需重启容器：

| 目录 | 说明 | 生效方式 |
|---|---|---|
| `open/zsl1_world/` | 仿真世界 / 场景文件 | 重启 Gazebo |
| `open/zsl1_gazebo/` | Gazebo 启动配置 | 重启 Gazebo |
| `open/zsl1_control_launch/` | 控制器启动配置 | 重启 ros2 launch |
| `open/zsl1_TFpub_rviz/` | TF 发布与 RViz 可视化 | 容器内重新编译（见下） |

修改 `zsl1_TFpub_rviz` 源码后，进入容器执行：

```bash
colcon build --packages-select zsl1_TFpub_rviz
source install/setup.bash
```

---

## 调整机器人数量

所有机器人的配置（数量、位姿、策略等）集中在**一个文件**中：

```
open/zsl1_gazebo/launch/robots_config.py
```

### 减少机器人

注释掉对应条目，例如只使用 1 台：

```python
ROBOTS = [
    {
        "name": "zsl1sensor1",
        ...
    },
    # {                        ← 注释掉这一整块即可禁用 sensor2
    #     "name": "zsl1sensor2",
    #     ...
    # },
]
```

### 增加机器人

取消注释示例条目（或新增一项），同时确保对应 policy 目录存在：
`policy/zsl1/zsl1sensorN/`（需联系开发者获取策略文件）。

### 生效方式

修改 `robots_config.py` 后，**无需重建镜像**，执行以下两步即可：

**第 1 步：清除 Python 字节码缓存**

在宿主机执行：
```bash
docker exec zsl1_sim_gazebo_humble_deploy find /workspace -name '__pycache__' -path '*/launch/*' -exec rm -rf {} +
```

或进入容器后执行：
```bash
find /workspace -name '__pycache__' -path '*/launch/*' -exec rm -rf {} +
```

**第 2 步：重启两个 launch**（在容器内各终端重启）

```bash
# 终端 1：重启 Gazebo
ros2 launch zsl1_gazebo zsl1_gazebo.launch.py

# 终端 2：重启控制节点
ros2 launch zsl1_control zsl1sensor_control.launch.py
```

---

## 运行

**每个命令在容器内的独立终端中执行。**  
进入容器后，每次都先执行以下环境初始化：

```bash
cd /workspace
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=77
export GAZEBO_MASTER_URI=http://127.0.0.1:11377
```

---

### 1. 启动 Gazebo 仿真环境（含机器人模型）

**终端 1**（第一个启动，启动后等待 Gazebo 完全加载再开第二步）：

```bash
ros2 launch zsl1_gazebo zsl1_gazebo.launch.py
```

---

### 2. 启动运动控制节点

**终端 2**（Gazebo 加载完成后执行）：

```bash
ros2 launch zsl1_control zsl1sensor_control.launch.py
```

---

### 3. 查看话题列表（可选）

**终端 3**：

```bash
ros2 topic list
```

---

### 4. 启动 RViz 可视化（可选）

**终端 4**（需要 X11 / 显示器支持）：

```bash
ros2 launch zsl1_TFpub_rviz zsl1_rviz.launch.py
```

---

## 清理仿真残留进程

如果 Gazebo 崩溃或 launch 卡死，在容器内执行：

```bash
pkill -9 -f gzserver || true
pkill -9 -f gzclient || true
pkill -9 -f locomotion_sim || true
pkill -9 -f robot_state_publisher || true
```