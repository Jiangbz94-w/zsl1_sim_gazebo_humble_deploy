#!/bin/bash
# make_deploy_package.sh
#
# 在「开发机」上运行。
# 从项目源码中提取开放包，生成可分发的目录。
# 输出目标：/home/jiangbz/project/locomotion/jbz/zsl1_sim_gazebo_humble_deploy
#
# 分发给对方的内容：
#   zsl1_sim_gazebo_humble_deploy/
#   ├── README.md                — 部署使用说明
#   ├── docker_start_deploy.sh   — 启动容器的脚本
#   ├── docker_join_deploy.sh    — 进入容器的脚本
#   ├── make_deploy_package.sh   — 本脚本（方便接收方再次生成）
#   └── open/
#       ├── zsl1_TFpub_rviz/     — TF + RViz 可视化包（完整源码）
#       ├── zsl1_world/          — 仿真世界文件（完整源码）
#       ├── zsl1_gazebo/         — Gazebo launch 包（含 robots_config.py，完整源码）
#       └── zsl1_control_launch/ — 控制 launch 文件（单文件）
#
# 使用方法：
#   cd <项目根目录>/docker_deploy
#   bash make_deploy_package.sh

set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PKG_DIR="/home/jiangbz/project/locomotion/jbz/zsl1_sim_gazebo_humble_deploy"
OPEN_DIR="${PKG_DIR}/open"

echo "[INFO] 清理目标目录内容（保留 .git）..."
# 只删内容，不删 .git，避免破坏 git repo
find "${PKG_DIR}" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
mkdir -p "${OPEN_DIR}"

echo "[INFO] 复制开放包 ..."
cp -r "${PROJECT_ROOT}/src/zsl1/zsl1_TFpub_rviz"  "${OPEN_DIR}/"
cp -r "${PROJECT_ROOT}/src/zsl1/zsl1_world"        "${OPEN_DIR}/"
cp -r "${PROJECT_ROOT}/src/zsl1/zsl1_gazebo"       "${OPEN_DIR}/"

mkdir -p "${OPEN_DIR}/zsl1_control_launch"
cp "${PROJECT_ROOT}/src/zsl1/zsl1_control/launch/zsl1sensor_control.launch.py" \
   "${OPEN_DIR}/zsl1_control_launch/"

echo "[INFO] 复制启动脚本 ..."
cp "${SCRIPT_DIR}/docker_start_deploy.sh" "${PKG_DIR}/"
cp "${SCRIPT_DIR}/docker_join_deploy.sh"  "${PKG_DIR}/"
chmod +x "${PKG_DIR}/docker_start_deploy.sh"
chmod +x "${PKG_DIR}/docker_join_deploy.sh"

echo "[INFO] 复制部署工具脚本 ..."
cp "${SCRIPT_DIR}/make_deploy_package.sh" "${PKG_DIR}/"
chmod +x "${PKG_DIR}/make_deploy_package.sh"

echo "[INFO] 复制 README ..."
cp "${SCRIPT_DIR}/README_deploy.md" "${PKG_DIR}/README.md"

echo ""
echo "[SUCCESS] 部署包已生成：${PKG_DIR}"
echo ""
echo "分发给对方的目录结构："
find "${PKG_DIR}" -print | head -30
echo ""
echo "对方操作步骤："
echo "  1. docker pull jiangbz/zsl1_sim_gazebo_humble:deploy"
echo "  2. cd deploy_package && bash docker_start_deploy.sh"
