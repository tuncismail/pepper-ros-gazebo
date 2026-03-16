#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import socket
import math
import json
import time
from naoqi import ALProxy

# ───── Setup ─────────────────────────────────────────────────────────────
PEPPER_IP = "192.168.1.188"
PEPPER_PORT = 9559
ROS_PC_IP = "172.23.105.204"  # ← IP of your ROS PC
ROS_PC_PORT = 5006           # ← Must match UDP_PORT in ROS node

laser = ALProxy("ALLaser", PEPPER_IP, PEPPER_PORT)
memory = ALProxy("ALMemory", PEPPER_IP, PEPPER_PORT)
motion = ALProxy("ALMotion", PEPPER_IP, PEPPER_PORT)
laser.laserON()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# ───── Constants ─────────────────────────────────────────────────────────
BASE = "Device/SubDeviceList/Platform/LaserSensor/"
DEVS = ["Front/", "Left/", "Right/"]  # Order matters: CCW from front
SEGMENTS = 15
TOTAL_BEAMS = len(DEVS) * SEGMENTS    # = 45
ANGLE_MIN = -math.pi / 2             # -90°
ANGLE_MAX = +math.pi / 2             # +90°
ANGLE_INC = (ANGLE_MAX - ANGLE_MIN) / TOTAL_BEAMS

# ───── Loop ──────────────────────────────────────────────────────────────
print("[INFO] Sending Pepper laser data to {}:{}...".format(ROS_PC_IP, ROS_PC_PORT))

while True:
    vectors = []

    for dev in DEVS:
        for seg in range(1, SEGMENTS + 1):
            kx = "%s%sHorizontal/Seg%02d/X/Sensor/Value" % (BASE, dev, seg)
            ky = "%s%sHorizontal/Seg%02d/Y/Sensor/Value" % (BASE, dev, seg)

            try:
                x = memory.getData(kx)
                y = memory.getData(ky)
                vectors.append([x, y])
            except:
                vectors.append([float('inf'), float('inf')])  # fallback if NAOqi fails

    # Send as JSON string
    payload = json.dumps({"vectors": vectors})
    sock.sendto(payload.encode("utf-8"), (ROS_PC_IP, ROS_PC_PORT))

    time.sleep(0.1)  # 10 Hz
