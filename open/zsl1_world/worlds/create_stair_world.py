#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_stair_world.py — 生成 stair_climb.world

参考 demo/models/wm_stair_module 结构，在狗的正前方放置三列并排楼梯：
  · 每阶高度 0.07 m（7 cm），每阶深度 0.20 m，台阶宽 1.3 m
  · 3 列楼梯紧靠排列，颜色：左=红，中=黄，右=蓝
  · 楼梯起点距机器人 4.5 m（x=4.5 m）
  · 机器人出生点：(0, 0, 0.45)，朝向 +x

运行方式:
  cd src/zsl1/zsl1_world/worlds
  python3 create_stair_world.py
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent

# ──────────────────────────────────────────────
# 楼梯参数
# ──────────────────────────────────────────────
N_STEPS    = 8      # 台阶数
STEP_RUN   = 0.20   # 每阶水平深度（m）
STEP_RISE  = 0.07   # 每阶高度（m）——7 cm，适合四足机器狗
STEP_W     = 1.3    # 每列台阶宽度（y 方向，m）
STEP_THICK = 0.06   # 台阶板厚度（m）
START_X    = 4.5    # 楼梯最低阶前沿距机器人的距离（m）

PLATFORM_D  = 1.0   # 顶部平台深度（m）
PLATFORM_H  = 0.06  # 平台板厚度（m）

# 3 列颜色：左=红，中=黄，右=蓝
STAIRS = [
    # (列名,  y中心,               台阶颜色 RGB,       平台颜色 RGB)
    ("left",   -STEP_W,  "0.85 0.15 0.15",  "0.65 0.20 0.20"),  # 红
    ("center",  0.0,     "0.90 0.82 0.10",  "0.70 0.62 0.10"),  # 黄
    ("right",  +STEP_W,  "0.15 0.30 0.85",  "0.15 0.20 0.65"),  # 蓝
]


def _box_link(name, cx, cy, cz, sx, sy, sz, rgb):
    return (
        f'      <link name="{name}">\n'
        f'        <pose>{cx:.4f} {cy:.4f} {cz:.4f} 0 0 0</pose>\n'
        f'        <collision name="col">\n'
        f'          <geometry><box>'
        f'<size>{sx:.4f} {sy:.4f} {sz:.4f}</size></box></geometry>\n'
        f'        </collision>\n'
        f'        <visual name="vis">\n'
        f'          <geometry><box>'
        f'<size>{sx:.4f} {sy:.4f} {sz:.4f}</size></box></geometry>\n'
        f'          <material>\n'
        f'            <ambient>{rgb} 1</ambient>\n'
        f'            <diffuse>{rgb} 1</diffuse>\n'
        f'            <specular>0.3 0.3 0.3 20</specular>\n'
        f'          </material>\n'
        f'        </visual>\n'
        f'      </link>'
    )


def _stair_links_for(col_name, y_center, color_step, color_plat):
    """生成单列楼梯的所有 link（台阶 + 顶部平台）"""
    links = []
    for i in range(N_STEPS):
        cx   = START_X + i * STEP_RUN + STEP_RUN / 2.0
        z_top = (i + 1) * STEP_RISE
        cz   = z_top - STEP_THICK / 2.0
        links.append(
            _box_link(f'{col_name}_step_{i+1:02d}',
                      cx, y_center, cz,
                      STEP_RUN, STEP_W, STEP_THICK, color_step)
        )
    # 顶部平台
    top_z   = N_STEPS * STEP_RISE
    plat_cx = START_X + N_STEPS * STEP_RUN + PLATFORM_D / 2.0
    plat_cz = top_z - PLATFORM_H / 2.0
    links.append(
        _box_link(f'{col_name}_platform',
                  plat_cx, y_center, plat_cz,
                  PLATFORM_D, STEP_W, PLATFORM_H, color_plat)
    )
    return links


def create_world():
    all_links = []
    for col_name, y_center, color_step, color_plat in STAIRS:
        all_links.extend(_stair_links_for(col_name, y_center, color_step, color_plat))
    links_xml = '\n'.join(all_links)

    total_rise = N_STEPS * STEP_RISE
    total_run  = N_STEPS * STEP_RUN
    stair_end_x = START_X + total_run + PLATFORM_D

    world_text = (
        '<?xml version="1.0"?>\n'
        '<!--\n'
        '================================================================================\n'
        '  stair_climb.world — 三列并排楼梯爬坡场景\n'
        '================================================================================\n'
        '  【楼梯参数（参考 demo/models/wm_stair_module）】\n'
        f'    台阶数   = {N_STEPS} 阶\n'
        f'    每阶高度 = {STEP_RISE:.2f} m  （7 cm，适合四足机器狗）\n'
        f'    每阶深度 = {STEP_RUN:.2f} m\n'
        f'    台阶宽度 = {STEP_W:.1f} m（每列）\n'
        f'    总爬升高 = {total_rise:.2f} m\n'
        f'    楼梯总长 = {total_run:.2f} m  (x: {START_X:.1f} → {START_X+total_run:.1f})\n'
        f'    顶部平台 = {PLATFORM_D:.1f} m 深  (x: {START_X+total_run:.1f} → {stair_end_x:.1f})\n'
        '\n'
        '  【3 列排列（紧靠，无间隙）】\n'
        f'    左列 (y=-{STEP_W:.1f})：红色\n'
        f'    中列 (y= 0.0 )：黄色\n'
        f'    右列 (y=+{STEP_W:.1f})：蓝色\n'
        '\n'
        '  【机器人出生点】\n'
        '    x=0, y=0, z=0.45，朝向 +x 方向\n'
        '    楼梯起点距机器人 1.5 m，机器人正前方为黄色中列\n'
        '\n'
        '  【重新生成】\n'
        '    cd src/zsl1/zsl1_world/worlds\n'
        '    python3 create_stair_world.py\n'
        '================================================================================\n'
        '-->\n'
        '<sdf version="1.6">\n'
        '  <world name="stair_climb">\n'
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
        '      <shadows>true</shadows>\n'
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
        '      <ros><namespace>/</namespace></ros>\n'
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
        '    <!-- ==================== Three-column Staircase ==================== -->\n'
        '    <!--\n'
        f'      左(红) y=-{STEP_W:.1f}  中(黄) y=0  右(蓝) y=+{STEP_W:.1f}\n'
        f'      每阶 {STEP_RISE:.2f}m 高 × {STEP_RUN:.2f}m 深，共 {N_STEPS} 阶\n'
        '    -->\n'
        '    <model name="staircase">\n'
        '      <static>true</static>\n'
        '      <pose>0 0 0 0 0 0</pose>\n'
        f'{links_xml}\n'
        '    </model>\n'
        '\n'
        '  </world>\n'
        '</sdf>\n'
    )

    out = HERE / 'stair_climb.world'
    out.write_text(world_text, encoding='utf-8')
    return out


if __name__ == '__main__':
    print('[create_stair_world] 楼梯参数:')
    print(f'  台阶数   = {N_STEPS}')
    print(f'  每阶高度 = {STEP_RISE:.2f} m')
    print(f'  每阶深度 = {STEP_RUN:.2f} m')
    print(f'  每列宽度 = {STEP_W:.1f} m  × 3 列（左红/中黄/右蓝）')
    print(f'  总爬升高 = {N_STEPS * STEP_RISE:.2f} m')
    out = create_world()
    print(f'\n[create_stair_world] 完成！  {out}')
    print('  ros2 launch zsl1_gazebo zsl1_gazebo.launch.py scene:=stair_climb')

