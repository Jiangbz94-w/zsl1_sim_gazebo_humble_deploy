#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_tunnel_arc.py — 生成 tunnel_arc.world

俯照 colored_balls_arc.world 的圆弧排列，将 4 个球替换为 3 个形状不同的短隧道：
  · 三角形   (Triangle)   — 两斜板搭成的帐篷形拱洞（底宽 1.20 m × 高 1.00 m）
  · 半圆形   (Semicircle) — N 段矩形块拼出的半圆拱（内径 0.60 m）
  · 正方形   (Square)     — U 形三块组成的方形通道（宽 0.65 m × 高 0.60 m）

机器人可从任一隧道正面（朝向原点的一面）穿越而过。

运行方式:
  cd src/zsl1/zsl1_world/worlds
  python3 create_tunnel_arc.py
"""

import math
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ──────────────────────────────────────────────
# 全局尺寸参数
# ──────────────────────────────────────────────
D = 0.40   # 隧道深度（沿穿越方向 X，单位 m）
T = 0.10   # 墙壁厚度（单位 m）

# ──────────────────────────────────────────────
# 隧道圆弧配置（与 colored_balls_arc.world 相同）
# ARC_RADIUS = 5.0 m，角度分布 ±40°/±15°
# ──────────────────────────────────────────────
TUNNELS = [
    # (世界名, 形状, x,    y)
    ("tunnel_triangle",   "triangle",   3.83,  3.21),   # θ = +40°
    ("tunnel_semicircle", "semicircle", 5.00,  0.00),   # θ =   0° 居中
    ("tunnel_square",     "square",     3.83, -3.21),   # θ = -40°
]

SHAPE_COLORS = {
    "triangle":   "0.9 0.1 0.1",   # 红色 Red
    "semicircle": "0.9 0.8 0.1",   # 黄色 Yellow
    "square":     "0.1 0.3 0.9",   # 蓝色 Blue
}


# ──────────────────────────────────────────────
# SDF 片段生成工具
# ──────────────────────────────────────────────
def _link(name, px, py, pz, roll, pitch, yaw_l, sx, sy, sz, rgb):
    """
    生成单个 <link> XML 字符串（在 model 本地坐标系下）。
    pose: 位置 (px,py,pz)，姿态 (roll,pitch,yaw_l)
    size: 盒子尺寸 (sx,sy,sz)
    rgb:  "R G B" 字符串（不含 Alpha）
    """
    return (
        f'      <link name="{name}">\n'
        f'        <pose>{px:.4f} {py:.4f} {pz:.4f} '
        f'{roll:.4f} {pitch:.4f} {yaw_l:.4f}</pose>\n'
        f'        <collision name="col">\n'
        f'          <geometry><box>'
        f'<size>{sx:.4f} {sy:.4f} {sz:.4f}</size>'
        f'</box></geometry>\n'
        f'        </collision>\n'
        f'        <visual name="vis">\n'
        f'          <geometry><box>'
        f'<size>{sx:.4f} {sy:.4f} {sz:.4f}</size>'
        f'</box></geometry>\n'
        f'          <material>\n'
        f'            <ambient>{rgb} 1</ambient>\n'
        f'            <diffuse>{rgb} 1</diffuse>\n'
        f'            <specular>0.4 0.4 0.4 30</specular>\n'
        f'          </material>\n'
        f'        </visual>\n'
        f'      </link>'
    )


def _inclined(name, y1, y2, z_bot, z_top, rgb):
    """
    生成一块斜面板：下端中心在 (y1, z_bot)，上端中心在 (y2, z_top)。
    板子盒子尺寸：深度 D × 斜边长 L × 厚度 T。
    Roll 角通过 atan2(dz, dy) 计算使 Y_local 对准面板方向。
    """
    dy = y2 - y1
    dz = z_top - z_bot
    L  = math.sqrt(dy * dy + dz * dz)
    cy = (y1 + y2) / 2.0
    cz = (z_bot + z_top) / 2.0
    roll = math.atan2(dz, dy)
    return _link(name, 0, cy, cz, roll, 0, 0, D, L, T, rgb)


# ──────────────────────────────────────────────
# 各形状 link 生成
# ──────────────────────────────────────────────
def _links_square():
    """
    正方形隧道 — U 形截面：两竖墙 + 顶横梁
    开口：宽 W=0.90 m × 高 H=0.75 m
    （与三角形底宽 1.20m / 半圆形宽 1.20m 协调，狗可轻松通过）
    【Robot 穿越方向】沿模型局部 X 轴
    """
    W, H = 0.90, 0.75
    rgb  = SHAPE_COLORS["square"]
    return [
        _link("left_wall",
              0, -(W / 2 + T / 2), H / 2, 0, 0, 0,
              D, T, H, rgb),
        _link("right_wall",
              0, +(W / 2 + T / 2), H / 2, 0, 0, 0,
              D, T, H, rgb),
        _link("top_bar",
              0, 0, H + T / 2, 0, 0, 0,
              D, W + 2 * T, T, rgb),
    ]


def _links_triangle():
    """
    三角形隧道 — 两块斜板搭成帐篷形
    底宽 W_base=1.20 m，顶高 H=1.00 m
    斜板从底角 (±W/2, 0) 延伸到顶点 (0, H)
    实际通道：在高度 0.35 m 处宽度约 0.78 m，安全过狗
    """
    W, H = 1.20, 1.00
    half = W / 2.0
    rgb  = SHAPE_COLORS["triangle"]
    return [
        _inclined("left_panel",  -half, 0.0,  0, H, rgb),
        _inclined("right_panel",  half, 0.0,  0, H, rgb),
    ]


def _links_semicircle():
    """
    半圆形隧道 — 10 段弧形块拼成半圆拱
    内径 Ri=0.60 m，中径 Rm=0.65 m，厕 T=0.10 m
    开口：直径 1.20 m × 拱高 0.60 m
    每段 roll = atan2(cos α, -sin α) 使 Y_local 沿切线方向
    """
    Ri  = 0.60
    Rm  = Ri + T / 2.0   # 中径 = 0.65 m
    N   = 10
    rgb = SHAPE_COLORS["semicircle"]

    # 段弦长 × 1.12 略微重叠，消除间隙
    seg_len = 2.0 * Rm * math.sin(math.pi / (2.0 * N)) * 1.12

    links = []
    for i in range(N):
        # 各段中心角（从右侧 0° 到左侧 180°）
        alpha = (i + 0.5) * math.pi / N
        y_c   = Rm * math.cos(alpha)   # cos(0)=1 → 右(+y); cos(π)=-1 → 左(-y)
        z_c   = Rm * math.sin(alpha)   # sin(0)=0 → 底部; sin(π/2)=1 → 顶部
        roll  = math.atan2(math.cos(alpha), -math.sin(alpha))
        links.append(
            _link(f"arc_{i:02d}", 0, y_c, z_c, roll, 0, 0, D, seg_len, T, rgb)
        )
    return links


BUILDERS = {
    "triangle":   _links_triangle,
    "semicircle": _links_semicircle,
    "square":     _links_square,
}

SHAPE_ZH = {
    "triangle":   "三角形(Triangle)",
    "semicircle": "半圆形(Semicircle)",
    "square":     "正方形(Square)",
}

ANGLE_LABEL = {
    "tunnel_triangle":   "θ=+40°",
    "tunnel_semicircle": "θ=  0°",
    "tunnel_square":     "θ=-40°",
}


# ──────────────────────────────────────────────
# 组合成 <model> XML
# ──────────────────────────────────────────────
def _model_xml(name, shape, x, y):
    # +X 面朝向机器人（位于原点）
    yaw = math.atan2(-y, -x)
    links_xml = "\n".join(BUILDERS[shape]())
    return (
        f'    <!-- ===== {SHAPE_ZH[shape]} 隧道  {ANGLE_LABEL[name]} ===== -->\n'
        f'    <model name="{name}">\n'
        f'      <static>true</static>\n'
        f'      <!--\n'
        f'        ARC_RADIUS=5.0 m, {ANGLE_LABEL[name]}\n'
        f'        位置 x={x:.2f}  y={y:.2f}  yaw={yaw:.4f} rad\n'
        f'        （+X 面朝向机器人，机器人沿本地 -X 方向穿越）\n'
        f'      -->\n'
        f'      <pose>{x:.2f} {y:.2f} 0 0 0 {yaw:.4f}</pose>\n'
        f'{links_xml}\n'
        f'    </model>'
    )


# ──────────────────────────────────────────────
# 生成 world 文件
# ──────────────────────────────────────────────
def create_world():
    models_xml = "\n\n".join(
        _model_xml(name, shape, x, y)
        for name, shape, x, y in TUNNELS
    )

    world_text = (
        '<?xml version="1.0"?>\n'
        '<!--\n'
        '================================================================================\n'
        '  tunnel_arc.world — 四形状短隧道圆弧排列场景\n'
        '================================================================================\n'
        '  【机器人出生点】\n'
        '    位置由 zsl1_gazebo.launch.py 的 SCENE_PRESETS 决定，\n'
        '    默认 x=0, y=0, z=0.45，朝向 +x 方向。\n'
        '\n'
        '  【三隧道排列方式】\n'
        '    仿照 colored_balls_arc.world，沿 ARC_RADIUS=5.0 m 圆弧对称排列。\n'
        '    角度：三角形(+40°) 半圆形(0°居中) 正方形(-40°)\n'
        '\n'
        '  【隧道尺寸说明】\n'
        '    · 三角形  — 底宽 1.20 m × 顶高 1.00 m，两斜板（h=0.35m处净宽 0.78 m）\n'
        '    · 半圆形  — 内径 0.60 m（拱宽 1.20 m × 拱高 0.60 m），10段弧块\n'
        '    · 正方形  — 开口宽 0.90 m × 高 0.75 m，U形三块\n'
        '    · 隧道深度（穿越方向）= 0.40 m；壁厚 = 0.10 m\n'
        '\n'
        '  【机器人穿越方式】\n'
        '    每个隧道的 yaw = atan2(-y,-x) 使 +X 面正对机器人。\n'
        '    机器人走直线冲入隧道 +X 面，沿本地 X 轴穿过，从 -X 面出来。\n'
        '\n'
        '  【重新生成】\n'
        '    cd src/zsl1/zsl1_world/worlds\n'
        '    python3 create_tunnel_arc.py\n'
        '================================================================================\n'
        '-->\n'
        '<sdf version="1.6">\n'
        '  <world name="tunnel_arc">\n'
        '\n'
        '    <!-- ==================== Physics ==================== -->\n'
        '    <physics type="ode">\n'
        '      <real_time_update_rate>1000.0</real_time_update_rate>\n'
        '      <max_step_size>0.001</max_step_size>\n'
        '      <real_time_factor>1</real_time_factor>\n'
        '    </physics>\n'
        '\n'
        '    <!-- ==================== Scene ==================== -->\n'
        '    <scene>\n'
        '      <ambient>0.6 0.6 0.6 1</ambient>\n'
        '      <background>0.4 0.5 0.6 1</background>\n'
        '      <shadows>false</shadows>\n'
        '    </scene>\n'
        '\n'
        '    <!-- ==================== Lighting ==================== -->\n'
        '    <light name="sun" type="directional">\n'
        '      <cast_shadows>true</cast_shadows>\n'
        '      <pose>0 0 10 0 0 0</pose>\n'
        '      <diffuse>0.9 0.9 0.9 1</diffuse>\n'
        '      <specular>0.3 0.3 0.3 1</specular>\n'
        '      <direction>-0.3 0.3 -1</direction>\n'
        '    </light>\n'
        '\n'
        '    <!-- ==================== Gazebo ROS State Plugin ==================== -->\n'
        '    <plugin name="gazebo_ros_state" filename="libgazebo_ros_state.so">\n'
        '      <ros>\n'
        '        <namespace>/</namespace>\n'
        '      </ros>\n'
        '    </plugin>\n'
        '\n'
        '    <!-- ==================== Ground Plane ==================== -->\n'
        '    <model name="ground_plane">\n'
        '      <static>true</static>\n'
        '      <link name="link">\n'
        '        <collision name="collision">\n'
        '          <geometry>\n'
        '            <plane><normal>0 0 1</normal><size>100 100</size></plane>\n'
        '          </geometry>\n'
        '          <surface>\n'
        '            <friction><ode><mu>100</mu><mu2>50</mu2></ode></friction>\n'
        '          </surface>\n'
        '        </collision>\n'
        '        <visual name="visual">\n'
        '          <cast_shadows>false</cast_shadows>\n'
        '          <geometry>\n'
        '            <plane><normal>0 0 1</normal><size>100 100</size></plane>\n'
        '          </geometry>\n'
        '          <material>\n'
        '            <script>\n'
        '              <uri>file://media/materials/scripts/gazebo.material</uri>\n'
        '              <name>Gazebo/Grey</name>\n'
        '            </script>\n'
        '          </material>\n'
        '        </visual>\n'
        '      </link>\n'
        '    </model>\n'
        '\n'
        + models_xml
        + '\n\n'
        '  </world>\n'
        '</sdf>\n'
    )

    out = HERE / 'tunnel_arc.world'
    out.write_text(world_text, encoding='utf-8')
    print(f'  [world] {out.name}')
    return out


# ──────────────────────────────────────────────
# 主程序 — 打印各隧道几何摘要
# ──────────────────────────────────────────────
if __name__ == '__main__':
    import textwrap

    print('[create_tunnel_arc] 各隧道几何摘要:')
    for name, shape, x, y in TUNNELS:
        yaw_deg = math.degrees(math.atan2(-y, -x))
        print(f'  {name:24s}  shape={shape:12s}  pos=({x:.2f},{y:.2f})  yaw={yaw_deg:+.1f}°')

    print('[create_tunnel_arc] 生成 world 文件...')
    out = create_world()

    print('\n[create_tunnel_arc] 完成！')
    print('  world 文件:', str(out))
    print('\n  在容器内执行:')
    print('    colcon build --symlink-install --packages-select zsl1_world')
    print('    ros2 launch zsl1_gazebo zsl1_gazebo.launch.py scene:=tunnel_arc')
