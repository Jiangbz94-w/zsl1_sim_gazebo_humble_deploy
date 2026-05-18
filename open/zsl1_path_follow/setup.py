from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'zsl1_path_follow'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='kunpeng',
    maintainer_email='fankunpeng0918@gmail.com',
    description='Pure pursuit and velocity control based path follower (ROS 2 Humble).',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'path_follow_close = zsl1_path_follow.scripts.path_follow_close:main',
            'cmd_pub           = zsl1_path_follow.scripts.cmd_pub:main',
            'test_path_follow  = zsl1_path_follow.scripts.test:main',
        ],
    },
)
