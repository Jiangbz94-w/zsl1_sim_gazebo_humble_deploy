#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File    : path_lib.py
@Author  : kunpeng fan
@Brief   : Path in robot's coor.
@License : Copyright (c) 2026. Licensed under the MIT License.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import CubicSpline
from typing import Optional

class PathLib():
    def __init__(self,
                 total_paths: int, 
                 max_angle: float, 
                 distance: float,
                 num_future_points: int,
    ) -> None:
        self.total_paths = total_paths
        self.max_angle = max_angle
        self.distance = distance
        self.num_future_points = num_future_points

        self.paths = self.generate_custom_paths(total_paths=total_paths, 
                                   max_angle=max_angle, 
                                   distance=distance,
                                   num_future_points=num_future_points)
    
    @staticmethod
    def generate_custom_paths(total_paths: int, 
                              max_angle: float, 
                              distance: float,
                              num_future_points: int,
    ) -> np.ndarray:
        '''
        Return:
            paths: [total_paths, num_future_points+1, 3]
        '''
        if total_paths <= 1:
            angles = [0.0]
        else:
            angles = np.linspace(-max_angle, max_angle, total_paths)

        path_list = []
        for _, target_angle in enumerate(angles):
            # orientation at the origin
            waypts_r = np.array([0.0, distance * 0.1, distance * 0.8, distance])
            
            waypts_shift = np.array([0.0, target_angle * 0.2, target_angle, target_angle])
            
            cs = CubicSpline(waypts_r, waypts_shift, bc_type='clamped')
            
            path_r = np.linspace(0, distance, num_future_points+1)
            ###
            path_shift_deg = cs(path_r)
            
            path_x = path_r * np.cos(np.radians(path_shift_deg))
            path_y = path_r * np.sin(np.radians(path_shift_deg))

            # dx = np.gradient(path_x)
            # dy = np.gradient(path_y)
            # path_yaw = np.arctan2(dy, dx)
            ###

            d_shift_deg_dr = cs(path_r, 1)
            shift_rad = np.radians(path_shift_deg)
            d_shift_rad_dr = np.radians(d_shift_deg_dr)

            dx_dr = np.cos(shift_rad) - path_r * np.sin(shift_rad) * d_shift_rad_dr
            dy_dr = np.sin(shift_rad) + path_r * np.cos(shift_rad) * d_shift_rad_dr
            path_yaw = np.arctan2(dy_dr, dx_dr)
            
            path = np.stack((path_x, path_y, path_yaw), axis=1)

            path_list.append(path)
        
        return np.stack(path_list, axis=0)
    
    def plot_paths(self, 
                   show_points: bool = True,
                   norm_dis: Optional[float] = None
    ) -> None:
        if norm_dis is None:
            paths = self.paths.copy()
        else:
            paths = self.norm_path(norm_dis=norm_dis)

        plt.figure(figsize=(10, 8))
        
        colors = plt.cm.jet(np.linspace(0, 1, self.total_paths))
        
        for i in range(self.total_paths):
            path_x = paths[i, :, 0]
            path_y = paths[i, :, 1]
            
            plt.plot(path_x, path_y, color=colors[i], linewidth=1.5, alpha=0.8)
            
            if show_points:
                plt.scatter(path_x, path_y, color=colors[i], s=15, zorder=3)

        plt.title(f"pathLib Trajectories\n(Paths: {self.total_paths}, Max Angle: ±{self.max_angle}°, Distance: {self.distance}m)")
        plt.xlabel("X (m) - Forward")
        plt.ylabel("Y (m) - Lateral")
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.axis("equal")
        plt.tight_layout()
        plt.show()
    
    def get_path(self, 
                 idx: int,
                 norm_dis: Optional[float] = None
    ) -> np.ndarray:
        '''
        Returns:
            path: [T, 3]
        '''
        if norm_dis is None:
            paths = self.paths.copy()
        else:
            paths = self.norm_path(norm_dis=norm_dis)

        return paths[idx][1:]
    
    def get_all_pos_dis(self, norm_dis: Optional[float] = None) -> np.ndarray:
        '''
        Return:
            pos_dis: [total_paths * num_future_points, 4] contains [x, y, yaw, time_dis]
        '''
        if norm_dis is None:
            paths = self.paths.copy()
        else:
            paths = self.norm_path(norm_dis=norm_dis)
        
        num_paths, num_points, num_dim = paths.shape
    
        time_idx = np.arange(num_points)
        time_idx_expanded = np.broadcast_to(time_idx.reshape(1, num_points, 1), 
                                            (num_paths, num_points, 1))
        
        pos_dis = np.concatenate((paths, time_idx_expanded), axis=-1)[:, 1:, :]

        pos_dis = pos_dis.reshape(-1, num_dim+1)
        
        return pos_dis
    
    def norm_path(self, norm_dis: float) -> np.ndarray:
        '''
        Returns:
            paths: [total_paths, num_future_points+1, 3]
        ''' 
        paths = self.paths.copy()
        paths[:, :, :2] /= norm_dis

        return paths


if __name__ == "__main__":
    paths = PathLib(total_paths=3, max_angle=90.0, distance=3.0, num_future_points=10)
    paths.plot_paths(show_points=True, norm_dis=0.38)
    print(paths.get_all_pos_dis())