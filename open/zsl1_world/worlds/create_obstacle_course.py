#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_obstacle_course.py — 生成 obstacle_course.world

20×20 m 障碍赛道：
  · 10×10 地砖网格（每块 2×2 m），随机去除 ~22% 形成真实凹坑
    （凹坑底部有 z=-2 m 兜底面，防止无限下坠）
  · 30 根随机尖刺柱（高 0.5~2.2 m，宽 0.12~0.25 m）
  · 12 个随机障碍方块（高 0.8~1.8 m，宽 0.5~1.2 m）
  · 4 个彩球（红/黄/蓝/绿）分别位于场地四个角落附近 (±8, ±8)
  · 机器人出生点 (0,0,0.45)，出生区 2.5 m 内及球所在格子强制不挖坑

运行:
  cd src/zsl1/zsl1_world/worlds
  python3 create_obstacle_course.py
"""

import random
import math
from pathlib import Path

random.seed(42)

HERE = Path(__file__).resolve().parent

# ── 地砖参数 ──────────────────────────────────────────
GRID_N      = 10          # 10×10 网格
TILE_SIZE   = 2.0         # 每块地砖边长 (m) → 总面积 20×20 m
TILE_THICK  = 0.30        # 地砖厚度 (m)
PIT_RATIO   = 0.22        # 随机挖坑概率
CLEAR_SPAWN_R = 2.5       # 出生点安全半径 (m)

# ── 尖刺参数 ──────────────────────────────────────────
SPIKE_COUNT = 42
SPIKE_H_MIN = 0.50
SPIKE_H_MAX = 2.20

# ── 彩球参数：位于场地四角附近 ─────────────────────────
BALL_R = 0.20
BALLS = [
    # (名称, x, y, RGB)          角落位置 (±8, ±8)
    ("red",     8.0,  8.0,  (0.90, 0.10, 0.10)),   # 右前角
    ("yellow",  8.0, -8.0,  (0.90, 0.82, 0.10)),   # 左前角
    ("blue",   -8.0,  8.0,  (0.15, 0.30, 0.85)),   # 右后角
    ("green",  -8.0, -8.0,  (0.10, 0.75, 0.20)),   # 左后角
]

AREA_HALF = GRID_N * TILE_SIZE / 2   # = 10.0 m


# ──────────────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────────────
def tile_center(i, j):
    """第(i,j)块地砖的中心 (cx, cy)"""
    cx = -AREA_HALF + TILE_SIZE / 2 + i * TILE_SIZE
    cy = -AREA_HALF + TILE_SIZE / 2 + j * TILE_SIZE
    return cx, cy


def point_to_tile(x, y):
    """将坐标 (x,y) 映射到所在地砖 (i,j)"""
    i = int((x + AREA_HALF) / TILE_SIZE)
    j = int((y + AREA_HALF) / TILE_SIZE)
    return (min(max(i, 0), GRID_N - 1),
            min(max(j, 0), GRID_N - 1))


def dist2(x, y):
    return math.sqrt(x * x + y * y)


# ──────────────────────────────────────────────────────
# 地砖生成
# ──────────────────────────────────────────────────────
def gen_tiles():
    """生成地砖，随机挖坑，但保护出生区和球所在格子"""
    # 球所在的格子坐标
    ball_tiles = set()
    for _, bx, by, _ in BALLS:
        ball_tiles.add(point_to_tile(bx, by))

    tiles = []   # [(i, j, cx, cy)]
    pits  = set()
    for i in range(GRID_N):
        for j in range(GRID_N):
            cx, cy = tile_center(i, j)
            d = dist2(cx, cy)
            is_protected = (d <= CLEAR_SPAWN_R) or ((i, j) in ball_tiles)
            if not is_protected and random.random() < PIT_RATIO:
                pits.add((i, j))
            else:
                tiles.append((i, j, cx, cy))
    return tiles, pits, ball_tiles


# ──────────────────────────────────────────────────────
# 障碍物生成
# ──────────────────────────────────────────────────────
def _pick_obstacle_positions(tiles, ball_tiles, count):
    """从安全区外的地砖上随机选取障碍物放置位置"""
    candidates = [
        (cx, cy)
        for i, j, cx, cy in tiles
        if dist2(cx, cy) > CLEAR_SPAWN_R and (i, j) not in ball_tiles
    ]
    random.shuffle(candidates)
    return candidates[:count]


def gen_spikes(tiles, ball_tiles):
    positions = _pick_obstacle_positions(tiles, ball_tiles, SPIKE_COUNT)
    spikes = []
    for idx, (tx, ty) in enumerate(positions):
        ox = random.uniform(-TILE_SIZE * 0.38, TILE_SIZE * 0.38)
        oy = random.uniform(-TILE_SIZE * 0.38, TILE_SIZE * 0.38)
        h  = random.uniform(SPIKE_H_MIN, SPIKE_H_MAX)
        w  = random.uniform(0.12, 0.25)
        roll  = random.uniform(-0.10, 0.10)
        pitch = random.uniform(-0.10, 0.10)
        yaw   = random.uniform(0, math.pi)
        spikes.append(dict(
            idx=idx, cx=tx + ox, cy=ty + oy,
            cz=h / 2.0, roll=roll, pitch=pitch, yaw=yaw,
            h=h, w=w,
        ))
    return spikes



# ──────────────────────────────────────────────────────
# SDF 片段
# ──────────────────────────────────────────────────────
def tile_link_sdf(i, j, cx, cy):
    g = 0.58
    return (
        f'      <link name="tile_{i}_{j}">\n'
        f'        <pose>{cx:.3f} {cy:.3f} {-TILE_THICK/2:.3f} 0 0 0</pose>\n'
        f'        <collision name="col">\n'
        f'          <geometry><box>'
        f'<size>{TILE_SIZE:.2f} {TILE_SIZE:.2f} {TILE_THICK:.2f}</size>'
        f'</box></geometry>\n'
        f'          <surface><friction>'
        f'<ode><mu>1.0</mu><mu2>1.0</mu2></ode></friction></surface>\n'
        f'        </collision>\n'
        f'        <visual name="vis">\n'
        f'          <geometry><box>'
        f'<size>{TILE_SIZE:.2f} {TILE_SIZE:.2f} {TILE_THICK:.2f}</size>'
        f'</box></geometry>\n'
        f'          <material>'
        f'<ambient>{g:.2f} {g:.2f} {g:.2f} 1</ambient>'
        f'<diffuse>{g:.2f} {g:.2f} {g:.2f} 1</diffuse>'
        f'<specular>0 0 0 1</specular>'
        f'</material>\n'
        f'        </visual>\n'
        f'      </link>\n'
    )


def spike_link_sdf(s):
    dg = 0.35
    return (
        f'      <link name="spike_{s["idx"]}">\n'
        f'        <pose>{s["cx"]:.3f} {s["cy"]:.3f} {s["cz"]:.3f} '
        f'{s["roll"]:.4f} {s["pitch"]:.4f} {s["yaw"]:.4f}</pose>\n'
        f'        <collision name="col">\n'
        f'          <geometry><box>'
        f'<size>{s["w"]:.3f} {s["w"]:.3f} {s["h"]:.3f}</size>'
        f'</box></geometry>\n'
        f'        </collision>\n'
        f'        <visual name="vis">\n'
        f'          <geometry><box>'
        f'<size>{s["w"]:.3f} {s["w"]:.3f} {s["h"]:.3f}</size>'
        f'</box></geometry>\n'
        f'          <material>'
        f'<ambient>{dg:.2f} {dg:.2f} {dg:.2f} 1</ambient>'
        f'<diffuse>{dg:.2f} {dg:.2f} {dg:.2f} 1</diffuse>'
        f'<specular>0 0 0 1</specular>'
        f'</material>\n'
        f'        </visual>\n'
        f'      </link>\n'
    )


def box_link_sdf(b):
    dg = 0.42
    return (
        f'      <link name="box_{b["idx"]}">\n'
        f'        <pose>{b["cx"]:.3f} {b["cy"]:.3f} {b["cz"]:.3f} '
        f'0 0 {b["yaw"]:.4f}</pose>\n'
        f'        <collision name="col">\n'
        f'          <geometry><box>'
        f'<size>{b["wx"]:.3f} {b["wy"]:.3f} {b["h"]:.3f}</size>'
        f'</box></geometry>\n'
        f'        </collision>\n'
        f'        <visual name="vis">\n'
        f'          <geometry><box>'
        f'<size>{b["wx"]:.3f} {b["wy"]:.3f} {b["h"]:.3f}</size>'
        f'</box></geometry>\n'
        f'          <material>'
        f'<ambient>{dg:.2f} {dg:.2f} {dg:.2f} 1</ambient>'
        f'<diffuse>{dg:.2f} {dg:.2f} {dg:.2f} 1</diffuse>'
        f'<specular>0 0 0 1</specular>'
        f'</material>\n'
        f'        </visual>\n'
        f'      </link>\n'
    )


def ball_model_sdf(ball_name, bx, by, color):
    bz      = BALL_R
    cr, cg, cb = color
    mass    = 0.5
    inertia = 0.4 * mass * BALL_R ** 2
    return (
        f'    <model name="{ball_name}_ball">\n'
        f'      <static>false</static>\n'
        f'      <pose>{bx:.3f} {by:.3f} {bz:.3f} 0 0 0</pose>\n'
        f'      <link name="link">\n'
        f'        <inertial>\n'
        f'          <mass>{mass}</mass>\n'
        f'          <inertia>'
        f'<ixx>{inertia:.4f}</ixx><ixy>0</ixy><ixz>0</ixz>'
        f'<iyy>{inertia:.4f}</iyy><iyz>0</iyz>'
        f'<izz>{inertia:.4f}</izz>'
        f'</inertia>\n'
        f'        </inertial>\n'
        f'        <collision name="collision">\n'
        f'          <geometry>'
        f'<sphere><radius>{BALL_R}</radius></sphere>'
        f'</geometry>\n'
        f'          <surface>\n'
        f'            <friction>'
        f'<ode><mu>0.6</mu><mu2>0.6</mu2></ode>'
        f'</friction>\n'
        f'            <bounce>'
        f'<restitution_coefficient>0.5</restitution_coefficient>'
        f'<threshold>0</threshold>'
        f'</bounce>\n'
        f'          </surface>\n'
        f'        </collision>\n'
        f'        <visual name="visual">\n'
        f'          <geometry>'
        f'<sphere><radius>{BALL_R}</radius></sphere>'
        f'</geometry>\n'
        f'          <material>\n'
        f'            <ambient>{cr} {cg} {cb} 1</ambient>\n'
        f'            <diffuse>{cr} {cg} {cb} 1</diffuse>\n'
        f'            <specular>0.5 0.4 0.3 50</specular>\n'
        f'          </material>\n'
        f'        </visual>\n'
        f'      </link>\n'
        f'    </model>\n'
    )


# ──────────────────────────────────────────────────────
# World 骨架
# ──────────────────────────────────────────────────────
WORLD_HEADER = """\
<?xml version="1.0"?>
<!--
================================================================================
  obstacle_course.world — 20×20 m 障碍赛道：随机尖刺 + 凹坑 + 四色球
================================================================================
  【场景说明】
    · 10×10 地砖网格（2×2 m/块），随机去除 ~22% 形成真实凹坑（z=-2 m 兜底）
    · 30 根尖刺柱 + 12 个障碍方块，随机散布在地砖上
    · 4 个彩球（红/黄/蓝/绿）分别位于场地四个角落附近 (±8, ±8)
    · 球所在地砖保证不被挖坑
  【机器人出生点】
    (0, 0, 0.45)，朝向 +x
  【启动】
    ros2 launch zsl1_gazebo zsl1_gazebo.launch.py scene:=obstacle_course
================================================================================
-->
<sdf version="1.6">
  <world name="obstacle_course">

    <!-- ==================== Physics ==================== -->
    <physics type="ode">
      <real_time_update_rate>1000.0</real_time_update_rate>
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1</real_time_factor>
    </physics>

    <!-- ==================== Scene ==================== -->
    <scene>
      <ambient>0.15 0.15 0.15 1</ambient>
      <background>0.40 0.50 0.60 1</background>
      <shadows>true</shadows>
    </scene>

    <!-- ==================== Lighting ==================== -->
    <light name="sun" type="directional">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 20 0 0 0</pose>
      <diffuse>0.90 0.90 0.90 1</diffuse>
      <specular>0.00 0.00 0.00 1</specular>
      <direction>-0.5 0.1 -0.9</direction>
      <attenuation>
        <range>1000</range>
        <linear>0.01</linear>
        <constant>0.9</constant>
        <quadratic>0.001</quadratic>
      </attenuation>
    </light>

    <!-- ==================== Gazebo ROS State Plugin ==================== -->
    <plugin name="gazebo_ros_state" filename="libgazebo_ros_state.so">
      <ros><namespace>/</namespace></ros>
    </plugin>

    <!-- ==================== 凹坑兜底平面（z=-2 m）==================== -->
    <model name="pit_floor">
      <static>true</static>
      <link name="link">
        <pose>0 0 -2.0 0 0 0</pose>
        <collision name="col">
          <geometry>
            <plane><normal>0 0 1</normal><size>100 100</size></plane>
          </geometry>
          <surface>
            <friction><ode><mu>0.5</mu><mu2>0.5</mu2></ode></friction>
          </surface>
        </collision>
        <visual name="vis">
          <cast_shadows>false</cast_shadows>
          <geometry>
            <plane><normal>0 0 1</normal><size>100 100</size></plane>
          </geometry>
          <material>
            <ambient>0.06 0.06 0.06 1</ambient>
            <diffuse>0.10 0.10 0.10 1</diffuse>
            <specular>0 0 0 1</specular>
          </material>
        </visual>
      </link>
    </model>

"""

TERRAIN_OPEN = """\
    <!-- ==================== 地砖 + 障碍物 ==================== -->
    <model name="obstacle_terrain">
      <static>true</static>
      <pose>0 0 0 0 0 0</pose>

"""

TERRAIN_CLOSE = """\
    </model>

"""

WORLD_FOOTER = """\
  </world>
</sdf>
"""


# ──────────────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────────────
def main():
    tiles, pits, ball_tiles = gen_tiles()
    spikes = gen_spikes(tiles, ball_tiles)

    pit_count  = len(pits)
    tile_count = len(tiles)
    total_pct  = pit_count * 100 // (GRID_N * GRID_N)

    print(f"[create_obstacle_course] 障碍赛道参数:")
    print(f"  地形范围  = 20 × 20 m  ({GRID_N}×{GRID_N} 网格，砖 {TILE_SIZE:.0f}×{TILE_SIZE:.0f} m)")
    print(f"  地砖数量  = {tile_count}  (凹坑数 = {pit_count}，约 {total_pct}%)")
    print(f"  尖刺柱    = {len(spikes)}")
    print(f"  彩球      = {len(BALLS)}  (四角位置 ±8, ±8)")
    print(f"  出生安全区= {CLEAR_SPAWN_R} m 半径")

    parts = [WORLD_HEADER, TERRAIN_OPEN]

    for i, j, cx, cy in tiles:
        parts.append(tile_link_sdf(i, j, cx, cy))
    for s in spikes:
        parts.append(spike_link_sdf(s))

    parts.append(TERRAIN_CLOSE)

    parts.append("    <!-- ==================== 四色球（四角）==================== -->\n")
    for name, bx, by, color in BALLS:
        parts.append(ball_model_sdf(name, bx, by, color))

    parts.append(WORLD_FOOTER)

    out_path = HERE / "obstacle_course.world"
    out_path.write_text("".join(parts), encoding="utf-8")

    print(f"\n[create_obstacle_course] 完成！  {out_path}")
    print(f"  ros2 launch zsl1_gazebo zsl1_gazebo.launch.py scene:=obstacle_course")


if __name__ == "__main__":
    main()
