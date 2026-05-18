#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_letter_cubes.py — 生成 A/B/C/D 字母立方体模型 + letter_cubes_arc.world

仿照 colored_balls_arc.world 的圆弧排列，将 4 个彩色球替换为带字母纹理的立方体。
立方体所有面均贴有对应字母的纹理，机器人从任意角度都能识别字母。

运行方式:
  cd src/zsl1/zsl1_world/worlds
  python3 create_letter_cubes.py
"""

import math
import os
import struct
import textwrap
import zlib
from pathlib import Path

HERE       = Path(__file__).resolve().parent
MODELS_DIR = HERE.parent / 'models'

# ──────────────────────────────────────────────
# 立方体配置（位置与 colored_balls_arc.world 相同）
# ARC_RADIUS=5.0, 角度: A+40°  B+15°  C-15°  D-40°
# ──────────────────────────────────────────────
CUBE_SIZE = 0.50   # 边长 0.5 m
CUBE_Z    = CUBE_SIZE / 2.0  # 底面贴地 → 中心 z=0.25

CUBES = [
    # name             letter  x      y      bg (R,G,B)       fg
    ("cube_letter_A",  "A",    3.83,  3.21,  (210, 55,  55),  (255, 255, 255)),  # 红底白字
    ("cube_letter_B",  "B",    4.83,  1.29,  (215, 200, 45),  (20,  20,  20)),   # 黄底黑字
    ("cube_letter_C",  "C",    4.83, -1.29,  (45,  80,  215), (255, 255, 255)),  # 蓝底白字
    ("cube_letter_D",  "D",    3.83, -3.21,  (45,  175, 60),  (255, 255, 255)),  # 绿底白字
]


# ──────────────────────────────────────────────
# 纯 Python PNG 生成器（无外部依赖）
# ──────────────────────────────────────────────
def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', crc)


def make_png(width: int, height: int, pixels: list) -> bytes:
    """pixels: 长度 = width*height 的 (R,G,B) 三元组列表，行优先。"""
    raw = b''
    for row in range(height):
        raw += b'\x00'  # filter type: None
        for col in range(width):
            raw += bytes(pixels[row * width + col])
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    return (
        b'\x89PNG\r\n\x1a\n'
        + _png_chunk(b'IHDR', ihdr)
        + _png_chunk(b'IDAT', zlib.compress(raw, 9))
        + _png_chunk(b'IEND', b'')
    )


# 8×8 点阵字体，每行用 8 位整数表示（bit7 = 最左列）
FONT_8x8 = {
    'A': [0b01111110,
          0b11000011,
          0b11000011,
          0b11111111,
          0b11000011,
          0b11000011,
          0b11000011,
          0b00000000],
    'B': [0b11111110,
          0b11000011,
          0b11000011,
          0b11111110,
          0b11000011,
          0b11000011,
          0b11111110,
          0b00000000],
    'C': [0b01111110,
          0b11000011,
          0b11000000,
          0b11000000,
          0b11000000,
          0b11000011,
          0b01111110,
          0b00000000],
    'D': [0b11111100,
          0b11000110,
          0b11000011,
          0b11000011,
          0b11000011,
          0b11000110,
          0b11111100,
          0b00000000],
}


def render_letter_png(letter: str, bg: tuple, fg: tuple, size: int = 128) -> bytes:
    """
    生成 size×size 像素的 PNG：纯色背景 + 居中放大的字母。
    字母使用 8×8 点阵字体，等比缩放至 size*0.75 高度。
    """
    scale = int(size * 0.75) // 8   # 字母高度占 75%，均匀缩放
    letter_w = 8 * scale
    letter_h = 8 * scale
    off_x = (size - letter_w) // 2
    off_y = (size - letter_h) // 2

    pixels = [tuple(bg)] * (size * size)
    for row_idx, row_bits in enumerate(FONT_8x8[letter]):
        for col_idx in range(8):
            if (row_bits >> (7 - col_idx)) & 1:
                for dr in range(scale):
                    for dc in range(scale):
                        py = off_y + row_idx * scale + dr
                        px = off_x + col_idx * scale + dc
                        if 0 <= py < size and 0 <= px < size:
                            pixels[py * size + px] = tuple(fg)
    return make_png(size, size, pixels)


# ──────────────────────────────────────────────
# 模型目录生成
# ──────────────────────────────────────────────
def create_model(name: str, letter: str, bg: tuple, fg: tuple) -> None:
    mdir    = MODELS_DIR / name
    tex_dir = mdir / 'materials' / 'textures'
    scr_dir = mdir / 'materials' / 'scripts'
    tex_dir.mkdir(parents=True, exist_ok=True)
    scr_dir.mkdir(parents=True, exist_ok=True)

    # 1) PNG 纹理
    png_name = f'letter_{letter}.png'
    (tex_dir / png_name).write_bytes(render_letter_png(letter, bg, fg, size=128))

    # 2) Ogre 材质脚本
    mat_name = f'CubeLetter/{letter}'
    (scr_dir / f'cube_{letter}.material').write_text(
        f'material {mat_name}\n'
        '{\n'
        '  technique\n'
        '  {\n'
        '    pass\n'
        '    {\n'
        '      ambient  1.0 1.0 1.0 1.0\n'
        '      diffuse  1.0 1.0 1.0 1.0\n'
        '      specular 0.3 0.3 0.3 1.0 20.0\n'
        '      texture_unit\n'
        '      {\n'
        f'        texture {png_name}\n'
        '      }\n'
        '    }\n'
        '  }\n'
        '}\n',
        encoding='utf-8',
    )

    # 3) model.sdf
    (mdir / 'model.sdf').write_text(
        '<?xml version="1.0"?>\n'
        '<sdf version="1.6">\n'
        f'  <model name="{name}">\n'
        '    <static>true</static>\n'
        '    <link name="link">\n'
        '      <collision name="collision">\n'
        '        <geometry>\n'
        f'          <box><size>{CUBE_SIZE} {CUBE_SIZE} {CUBE_SIZE}</size></box>\n'
        '        </geometry>\n'
        '        <surface>\n'
        '          <friction><ode><mu>0.8</mu><mu2>0.8</mu2></ode></friction>\n'
        '        </surface>\n'
        '      </collision>\n'
        '      <visual name="visual">\n'
        '        <geometry>\n'
        f'          <box><size>{CUBE_SIZE} {CUBE_SIZE} {CUBE_SIZE}</size></box>\n'
        '        </geometry>\n'
        '        <material>\n'
        '          <script>\n'
        f'            <uri>model://{name}/materials/scripts/</uri>\n'
        f'            <uri>model://{name}/materials/textures/</uri>\n'
        f'            <name>{mat_name}</name>\n'
        '          </script>\n'
        '        </material>\n'
        '      </visual>\n'
        '    </link>\n'
        '  </model>\n'
        '</sdf>\n',
        encoding='utf-8',
    )

    # 4) model.config
    (mdir / 'model.config').write_text(
        '<?xml version="1.0"?>\n'
        '<model>\n'
        f'  <name>Cube Letter {letter}</name>\n'
        '  <version>1.0</version>\n'
        '  <sdf version="1.6">model.sdf</sdf>\n'
        f'  <description>0.5 m cube with letter {letter} textured on all faces. bg=#{bg[0]:02x}{bg[1]:02x}{bg[2]:02x}</description>\n'
        '</model>\n',
        encoding='utf-8',
    )
    print(f'  [model] {name}  bg=#{bg[0]:02x}{bg[1]:02x}{bg[2]:02x}  fg=#{fg[0]:02x}{fg[1]:02x}{fg[2]:02x}')


# ──────────────────────────────────────────────
# World 文件生成
# ──────────────────────────────────────────────
LABEL = {'A': '红底白字(Red)',  'B': '黄底黑字(Yellow)',
         'C': '蓝底白字(Blue)', 'D': '绿底白字(Green)'}

ANGLE_LABEL = {'A': '+40°', 'B': '+15°', 'C': '-15°', 'D': '-40°'}


def create_world() -> None:
    out_path = HERE / 'letter_cubes_arc.world'

    includes = []
    for name, letter, x, y, bg, fg in CUBES:
        # +X 面朝向原点（机器人方向）
        yaw = math.atan2(-y, -x)
        includes.append(
            f'    <!-- ==================== {letter} 方块 '
            f'({LABEL[letter]}, θ={ANGLE_LABEL[letter]}) ==================== -->\n'
            f'    <include>\n'
            f'      <name>{name}</name>\n'
            f'      <uri>model://{name}</uri>\n'
            f'      <static>true</static>\n'
            f'      <!--\n'
            f'        【{letter} 方块位置】\n'
            f'        ARC_RADIUS=5.0, θ={ANGLE_LABEL[letter]}\n'
            f'        x={x:.2f}, y={y:.2f}, z={CUBE_Z:.2f}\n'
            f'        yaw={yaw:.4f} rad （+X 面正对机器人）\n'
            f'      -->\n'
            f'      <pose>{x:.2f} {y:.2f} {CUBE_Z:.2f} 0 0 {yaw:.4f}</pose>\n'
            f'    </include>'
        )

    world_text = (
        '<?xml version="1.0"?>\n'
        '<!--\n'
        '================================================================================\n'
        '  letter_cubes_arc.world — A/B/C/D 字母立方体圆弧排列场景\n'
        '================================================================================\n'
        '  【机器人出生点】\n'
        '    位置由 zsl1_gazebo.launch.py 的 SCENE_PRESETS 决定，\n'
        '    默认 x=0, y=0, z=0.45，朝向 +x 方向。\n'
        '\n'
        '  【四立方体排列方式】\n'
        '    仿照 colored_balls_arc.world，沿半径 ARC_RADIUS=5.0 m 的圆弧排列。\n'
        '    角度分布：A(+40°)  B(+15°)  C(-15°)  D(-40°)\n'
        '    立方体中心坐标（x, y, z）:\n'
        '      A  ( 3.83,  3.21, 0.25)  红底白字\n'
        '      B  ( 4.83,  1.29, 0.25)  黄底黑字\n'
        '      C  ( 4.83, -1.29, 0.25)  蓝底白字\n'
        '      D  ( 3.83, -3.21, 0.25)  绿底白字\n'
        '\n'
        '  【字母纹理】\n'
        '    每个立方体所有面均贴有对应字母纹理（8×8 点阵字体放大至 128×128 PNG）。\n'
        '    +X 面的 yaw 角已设置为正对机器人（原点方向）。\n'
        '\n'
        '  【立方体尺寸】\n'
        f'    边长 = {CUBE_SIZE} m，底面贴地（z_center = {CUBE_Z} m）\n'
        '\n'
        '  【模型路径】\n'
        '    src/zsl1/zsl1_world/models/cube_letter_X/\n'
        '    GAZEBO_MODEL_PATH 已在 zsl1_world.launch.py 中配置包含该目录。\n'
        '\n'
        '  【参数调整说明】\n'
        '  ┌───────────────────┬─────────────────────────────────────────────────────┐\n'
        '  │ 参数              │ 说明                                                │\n'
        '  ├───────────────────┼─────────────────────────────────────────────────────┤\n'
        '  │ ARC_RADIUS        │ 与 colored_balls_arc.world 相同 = 5.0 m             │\n'
        '  │ <pose> x/y        │ 直接修改数值（由 r*cos/sin(θ) 得出）               │\n'
        '  │ <pose> 第3位      │ 立方体中心高度 = CUBE_SIZE/2 = 0.25 m              │\n'
        '  │ <pose> 第6位(yaw) │ 使 +X 面朝向机器人 = atan2(-y,-x)                 │\n'
        '  └───────────────────┴─────────────────────────────────────────────────────┘\n'
        '================================================================================\n'
        '-->\n'
        '<sdf version="1.6">\n'
        '  <world name="letter_cubes_arc">\n'
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
        '            <plane>\n'
        '              <normal>0 0 1</normal>\n'
        '              <size>100 100</size>\n'
        '            </plane>\n'
        '          </geometry>\n'
        '          <surface>\n'
        '            <friction>\n'
        '              <ode><mu>100</mu><mu2>50</mu2></ode>\n'
        '            </friction>\n'
        '          </surface>\n'
        '        </collision>\n'
        '        <visual name="visual">\n'
        '          <cast_shadows>false</cast_shadows>\n'
        '          <geometry>\n'
        '            <plane>\n'
        '              <normal>0 0 1</normal>\n'
        '              <size>100 100</size>\n'
        '            </plane>\n'
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
        + '\n\n'.join(includes)
        + '\n\n'
        '  </world>\n'
        '</sdf>\n'
    )

    out_path.write_text(world_text, encoding='utf-8')
    print(f'  [world] {out_path.name}')


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
if __name__ == '__main__':
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print('[create_letter_cubes] 生成字母立方体模型...')
    for name, letter, x, y, bg, fg in CUBES:
        create_model(name, letter, bg, fg)

    print('[create_letter_cubes] 生成 world 文件...')
    create_world()

    print('\n[create_letter_cubes] 完成！')
    print('  生成的模型目录:', str(MODELS_DIR))
    print('  生成的 world 文件:', str(HERE / 'letter_cubes_arc.world'))
    print('\n  请在容器内执行:')
    print('    colcon build --symlink-install --packages-select zsl1_world')
    print('    ros2 launch zsl1_gazebo zsl1_gazebo.launch.py scene:=letter_cubes_arc')
