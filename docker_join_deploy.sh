#!/bin/bash
# docker_join_deploy.sh
#
# 进入已运行的 ZSL-1 仿真容器。
# 请先执行 docker_start_deploy.sh 启动容器。

CONTAINER_NAME="zsl1_sim_gazebo_humble_deploy"

# 检查容器是否存在
if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "[ERROR] 容器 ${CONTAINER_NAME} 不存在，请先执行：bash docker_start_deploy.sh"
    exit 1
fi

# 如果容器未运行则启动
STATUS=$(docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null)
if [ "$STATUS" != "true" ]; then
    echo "[INFO] 容器未运行，正在启动..."
    docker start "$CONTAINER_NAME"
fi

# 自动检测 DISPLAY（兼容本地和 SSH 远程）
if [ -z "$DISPLAY" ]; then
    X_SOCKET=$(ls /tmp/.X11-unix/ 2>/dev/null | head -1)
    if [ -n "$X_SOCKET" ]; then
        DISPLAY=":${X_SOCKET#X}"
        echo "[INFO] SSH 会话，使用 DISPLAY=$DISPLAY"
    else
        echo "[WARN] 未找到 X11 显示，GUI 应用可能无法运行"
    fi
fi

echo "[INFO] 进入容器 ${CONTAINER_NAME} ..."
docker exec -it -u jiangbz -e DISPLAY="$DISPLAY" "$CONTAINER_NAME" /bin/bash
