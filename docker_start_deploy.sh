#!/bin/bash
# docker_start_deploy.sh
#
# ZSL-1 仿真环境启动脚本。
# 首次运行：创建并启动容器。如果同名容器已存在则直接启动。
# 进入容器请执行： bash docker_join_deploy.sh
#
# open/ 目录结构：
#   open/
#   ├── zsl1_tfpub_rviz/            ← TF 发布与 RViz 可视化（含 C++ 源码），
#   │                                  修改后在容器内 colcon build 重新编译生效
#   ├── zsl1_path_follow/           ← 路径跟踪包（纯 Python），修改后立即生效
#   ├── zsl1_world/                 ← 仿真世界/场景文件，修改后重启 Gazebo 生效
#   ├── zsl1_gazebo_launch/         ← Gazebo launch 文件（含 robots_config.py），
#   │                                  修改后重启 ros2 launch 生效（无需重建镜像）
#   ├── zsl1_control_launch/        ← 控制器 launch 文件，修改后重启 ros2 launch 生效
#   └── zsl1_description_launch/    ← 机器人描述 launch 文件，修改后重启 ros2 launch 生效
#
# 调整机器人数量：编辑 open/zsl1_gazebo_launch/robots_config.py，
#   然后清除 __pycache__ 并重启两个 launch（无需重建镜像）：
#     docker exec zsl1_sim_gazebo_humble_deploy \
#       find /workspace -name '__pycache__' -path '*/launch/*' -exec rm -rf {} +

set -e

IMAGE="jiangbz/zsl1_sim_gazebo_humble:deploy"
CONTAINER_NAME="zsl1_sim_gazebo_humble_deploy"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
OPEN_DIR="${SCRIPT_DIR}/open"

# 检查 open/ 目录
if [ ! -d "${OPEN_DIR}" ]; then
    echo "[ERROR] 找不到 open/ 目录，请确认其与本脚本在同一文件夹下"
    exit 1
fi

# 如果容器已存在则直接启动，不删除重建
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    STATUS=$(docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null)
    if [ "$STATUS" = "true" ]; then
        echo "[INFO] 容器 ${CONTAINER_NAME} 已在运行"
    else
        echo "[INFO] 容器 ${CONTAINER_NAME} 已存在但未运行，重新启动..."
        docker start "$CONTAINER_NAME"
    fi
    echo "进入容器：  bash docker_join_deploy.sh"
    exit 0
fi

xhost +local:root 2>/dev/null || true

echo "[INFO] 启动部署容器 ${CONTAINER_NAME} ..."
docker run -itd \
  --name "$CONTAINER_NAME" \
  --network host \
  --ipc=host \
  --privileged \
  --gpus all \
  \
  --device=/dev/dri \
  --env="NVIDIA_VISIBLE_DEVICES=all" \
  --env="NVIDIA_DRIVER_CAPABILITIES=all" \
  --volume="/usr/share/glvnd:/usr/share/glvnd:ro" \
  \
  --env="DISPLAY=${DISPLAY:-:0}" \
  --env="QT_X11_NO_MITSHM=1" \
  --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
  \
  --volume="/etc/localtime:/etc/localtime:ro" \
  --env="CONTAINER_NAME=${CONTAINER_NAME}" \
  \
  `# === 开放包：从宿主机挂载，直接修改文件即可 ===` \
  `# 完整源码包（挂载到 src/，修改后在容器内重新编译）` \
  --volume="${OPEN_DIR}/zsl1_tfpub_rviz:/workspace/src/zsl1/zsl1_tfpub_rviz" \
  --volume="${OPEN_DIR}/zsl1_path_follow:/workspace/src/zsl1/zsl1_path_follow" \
  --volume="${OPEN_DIR}/zsl1_world:/workspace/src/zsl1/zsl1_world" \
  `# launch 文件直接挂载到已安装位置，修改后重启 ros2 launch 即生效（无需重新编译）` \
  --volume="${OPEN_DIR}/zsl1_gazebo_launch:/workspace/install/zsl1_gazebo/share/zsl1_gazebo/launch" \
  --volume="${OPEN_DIR}/zsl1_control_launch:/workspace/install/zsl1_control/share/zsl1_control/launch" \
  --volume="${OPEN_DIR}/zsl1_description_launch:/workspace/install/zsl1_description/share/zsl1_description/launch" \
  \
  --workdir=/workspace \
  "$IMAGE"

echo "[INFO] 容器 ${CONTAINER_NAME} 已创建并启动"
echo ""
echo "进入容器：  bash docker_join_deploy.sh"
echo "停止容器：  docker stop ${CONTAINER_NAME}"
echo ""
echo "open/ 目录已挂载到容器内对应位置，宿主机修改文件即时同步。"
echo ""
echo "挂载说明："
echo "  src/zsl1/zsl1_tfpub_rviz       ← open/zsl1_tfpub_rviz (修改后需 colcon build)"
echo "  src/zsl1/zsl1_path_follow      ← open/zsl1_path_follow (纯 Python，修改后立即生效)"
echo "  src/zsl1/zsl1_world            ← open/zsl1_world (修改后重启 Gazebo)"
echo "  install/.../zsl1_gazebo/launch ← open/zsl1_gazebo_launch (修改后重启 ros2 launch)"
echo "  install/.../zsl1_control/launch← open/zsl1_control_launch (修改后重启 ros2 launch)"
echo "  install/.../zsl1_description/launch← open/zsl1_description_launch (修改后重启)"