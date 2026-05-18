#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File    : path_follow_open.py
@Author  : kunpeng fan
@Brief   : Open-loop path follower (pure Python, no ROS dependency).
           Computes a (v, w) control sequence offline from a trajectory array.
           Designed to be paired with CmdVelPublisher for timed execution.
@License : Copyright (c) 2026. Licensed under the MIT License.

Design
------
PathFollowerOpen 与 ROS 解耦，算法可在无 ROS 环境下独立测试。
执行侧由 CmdVelPublisher（cmd_pub.py）按固定频率定时发布预计算的 (v, w) 序列。

  PathLib ──► PathFollowerOpen ──► [(v0,w0), ...] ──► CmdVelPublisher ──► /cmd_vel

Usage examples
--------------
# 纯 Python 测试（无 ROS）：
    import numpy as np
    from path_follow_open import PathFollowerOpen

    ctrl = PathFollowerOpen(dt=0.25, max_v=1.0, max_w=3.0)
    traj = ...  # [T, 3] numpy array (x, y, yaw) in robot's local frame
    actions = list(ctrl.path_follow(traj))  # [(v0, w0), (v1, w1), ...]

# 嵌入 test.py（与 CmdVelPublisher 配合）：
    controller = PathFollowerOpen(dt=1.0 / cmd_pub_hz, max_w=cmd_max_w)
    actions = list(controller.path_follow(traj=path))
    cmd_pub = CmdVelPublisher(freq=cmd_pub_hz, cmd_topic=cmd_topic)
    cmd_pub.set_actions(actions)
"""

import numpy as np


class PathFollowerOpen:
    """
    Open-loop path follower: integrates a [T, 3] trajectory (x, y, yaw in
    robot-local frame) into a (v, w) control sequence.

    No ROS dependency — the output is a plain list of (v, w) tuples that
    CmdVelPublisher publishes at the specified rate.

    Parameters
    ----------
    dt    : control time step [s]  (should match CmdVelPublisher frequency)
    eps   : near-zero distance threshold [m]
    max_v : maximum forward speed [m/s]
    max_w : maximum yaw rate [rad/s]
    """

    def __init__(self,
                 dt: float = 0.1,
                 eps: float = 1e-3,
                 max_v: float = 1.0,
                 max_w: float = 1.0,
    ) -> None:
        self.DT    = dt
        self.EPS   = eps
        self.MAX_V = max_v
        self.MAX_W = max_w

    # ── Static helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def clip_angle(angle: float) -> float:
        """Wrap angle to (−π, π]."""
        return (angle + np.pi) % (2 * np.pi) - np.pi

    @staticmethod
    def global_to_local(base_pose: np.ndarray,
                        target_pose: np.ndarray) -> np.ndarray:
        """
        Transform target_pose into base_pose's coordinate frame.

        Parameters
        ----------
        base_pose   : [x, y, yaw]
        target_pose : [x, y, yaw]

        Returns
        -------
        np.ndarray : [dx_local, dy_local, dyaw_local]
        """
        bx, by, byaw = base_pose
        tx, ty, tyaw = target_pose

        dx_g = tx - bx
        dy_g = ty - by

        dx_l   =  dx_g * np.cos(byaw) + dy_g * np.sin(byaw)
        dy_l   = -dx_g * np.sin(byaw) + dy_g * np.cos(byaw)
        dyaw_l = PathFollowerOpen.clip_angle(tyaw - byaw)

        return np.array([dx_l, dy_l, dyaw_l])

    # ── Core control ───────────────────────────────────────────────────────────

    def control_single_step(self, waypoint: np.ndarray):
        """
        Compute (v, w) for one step towards a local-frame waypoint.

        Parameters
        ----------
        waypoint : [dx, dy, dyaw]  in robot's local frame

        Returns
        -------
        (v, w) : forward speed [m/s], yaw rate [rad/s]
        """
        assert len(waypoint) == 3, 'waypoint must be [dx, dy, dyaw]'
        dx, dy, d_yaw = waypoint

        if np.abs(dx) < self.EPS and np.abs(dy) < self.EPS:
            v = 0.0
            w = self.clip_angle(d_yaw) / self.DT
        elif np.abs(dx) < self.EPS:
            v = 0.0
            w = np.sign(dy) * np.pi / (2 * self.DT)
        else:
            v = dx / self.DT
            w = self.clip_angle(d_yaw) / self.DT

        v = float(np.clip(v, 0, self.MAX_V))
        w = float(np.clip(w, -self.MAX_W, self.MAX_W))
        return v, w

    def path_follow(self, traj: np.ndarray):
        """
        Compute (v, w) sequence for a complete trajectory.

        Parameters
        ----------
        traj : np.ndarray, shape [T, 3]
            Trajectory in robot's local frame (x, y, yaw).

        Returns
        -------
        list of (v, w) tuples, one per trajectory waypoint.
        """
        assert traj.shape[-1] == 3, 'traj must be [T, 3] (x, y, yaw)'
        controls     = []
        current_pose = np.array([0.0, 0.0, 0.0])

        for i in range(traj.shape[0]):
            local_wp = self.global_to_local(current_pose, traj[i])
            v, w = self.control_single_step(local_wp)
            controls.append((v, w))

            cx, cy, cyaw = current_pose
            cx   += v * np.cos(cyaw) * self.DT
            cy   += v * np.sin(cyaw) * self.DT
            cyaw  = self.clip_angle(cyaw + w * self.DT)
            current_pose = np.array([cx, cy, cyaw])

        return controls
