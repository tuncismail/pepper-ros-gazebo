#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
velocity_receiver.py — runs ON the real Pepper robot.

Receives cmd_vel over UDP and forwards it to NAOqi ALMotion.

Usage:
    python velocity_receiver.py [--listen-ip 0.0.0.0] [--listen-port 5005]
                                [--pepper-ip 192.168.1.x] [--pepper-port 9559]
                                [--loop-hz 30] [--timeout 0.5]

Key design decisions:
  - Uses ALMotion.move(x, y, theta) which takes ACTUAL m/s / rad/s values,
    not the normalized fractions that moveToward() expects. This ensures
    sim-to-real velocity fidelity (1 m/s in sim == 1 m/s on real robot).
  - Motion loop runs at 30 Hz (configurable) with monotonic timing so the
    sleep accounts for ALMotion call latency (~5-20 ms).
  - Timeout matches the Gazebo plugin default (0.5 s) so the real robot
    stops at the same time as the simulation when comms are lost.
  - threading.Lock protects shared state between UDP listener and motion loop.
"""

import argparse
import socket
import json
import threading
import time

try:
    import qi
except ImportError:
    raise SystemExit("qi SDK not found. Run this script on Pepper or with the NAOqi SDK installed.")


def parse_args():
    p = argparse.ArgumentParser(description="UDP cmd_vel → NAOqi ALMotion bridge")
    p.add_argument("--listen-ip",   default="0.0.0.0",       help="UDP listen address (default: 0.0.0.0)")
    p.add_argument("--listen-port", default=5005, type=int,   help="UDP listen port (default: 5005)")
    p.add_argument("--pepper-ip",   default="192.168.1.188",  help="Pepper robot IP (default: 192.168.1.188)")
    p.add_argument("--pepper-port", default=9559, type=int,   help="NAOqi port (default: 9559)")
    p.add_argument("--loop-hz",     default=30,   type=float, help="Motion loop frequency in Hz (default: 30)")
    p.add_argument("--timeout",     default=0.5,  type=float, help="Seconds before stopping if no cmd received (default: 0.5)")
    return p.parse_args()


class VelocityReceiver(object):
    def __init__(self, args):
        # ── NAOqi setup ──────────────────────────────────────────────────────
        self.session = qi.Session()
        self.session.connect("tcp://{}:{}".format(args.pepper_ip, args.pepper_port))
        self.motion = self.session.service("ALMotion")
        self.motion.wakeUp()
        print("[INFO] Connected to Pepper at {}:{}".format(args.pepper_ip, args.pepper_port))

        # ── UDP socket ───────────────────────────────────────────────────────
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((args.listen_ip, args.listen_port))
        self.sock.settimeout(1.0)   # unblock listen() so shutdown works
        print("[INFO] Listening for velocity on UDP {}:{}".format(args.listen_ip, args.listen_port))

        # ── Shared state (protected by lock) ────────────────────────────────
        self._lock = threading.Lock()
        self._current_cmd = (0.0, 0.0, 0.0)   # (x m/s, y m/s, theta rad/s)
        self._last_recv_time = time.time()

        # ── Config ───────────────────────────────────────────────────────────
        self._loop_interval = 1.0 / args.loop_hz
        self._timeout = args.timeout

        self._running = True

        # Start motion loop in background thread
        self._motion_thread = threading.Thread(target=self._motion_loop)
        self._motion_thread.daemon = True
        self._motion_thread.start()

        self._listen_loop()

    # ── Listener (main thread) ───────────────────────────────────────────────

    def _listen_loop(self):
        while self._running:
            try:
                data, _ = self.sock.recvfrom(1024)
                parsed = json.loads(data.decode("utf-8"))
                cmd = (
                    float(parsed.get("x",     0.0)),
                    float(parsed.get("y",     0.0)),
                    float(parsed.get("theta", 0.0)),
                )
                with self._lock:
                    self._current_cmd = cmd
                    self._last_recv_time = time.time()
            except socket.timeout:
                pass   # normal — lets us check self._running
            except (ValueError, KeyError) as e:
                print("[WARN] Bad packet: %s" % e)
            except Exception as e:
                print("[ERROR] Listen error: %s" % e)

    # ── Motion loop (background thread) ─────────────────────────────────────

    def _motion_loop(self):
        """
        Runs at --loop-hz (default 30 Hz).

        Uses ALMotion.move(x, y, theta) which takes actual m/s and rad/s,
        matching ROS Twist convention exactly. moveToward() takes normalized
        fractions (-1..1) and would result in incorrect speed scaling.

        Timing: each iteration measures how long ALMotion.move() took and
        subtracts it from the sleep, keeping the loop at the target rate
        even when the NAOqi call has variable latency (typically 5-20 ms).
        """
        while self._running:
            t0 = time.time()

            with self._lock:
                x, y, theta = self._current_cmd
                age = t0 - self._last_recv_time

            if age > self._timeout:
                # No command received recently — stop the robot
                self.motion.stopMove()
            else:
                # ALMotion.move(x, y, theta):
                #   x     — forward velocity in m/s  (positive = forward)
                #   y     — lateral velocity in m/s  (positive = left)
                #   theta — angular velocity in rad/s (positive = CCW)
                # This matches ROS Twist.linear.x / .y / angular.z exactly.
                self.motion.move(x, y, theta)

            elapsed = time.time() - t0
            sleep_time = self._loop_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    # ── Shutdown ─────────────────────────────────────────────────────────────

    def shutdown(self):
        self._running = False
        self.motion.stopMove()
        self.sock.close()
        print("[INFO] Shutdown complete")


if __name__ == "__main__":
    args = parse_args()
    receiver = None
    try:
        receiver = VelocityReceiver(args)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
    finally:
        if receiver is not None:
            receiver.shutdown()
