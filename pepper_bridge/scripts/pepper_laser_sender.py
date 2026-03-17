#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import socket
import math
import json
import time
from naoqi import ALProxy

# ───── Setup ─────────────────────────────────────────────────────────────
PEPPER_IP   = "192.168.1.188"    # Pepper's IP address
PEPPER_PORT = 9559
ROS_PC_IP   = "172.23.105.204"   # ROS PC's IP address
ROS_PC_PORT = 5006               # Receiver must listen on the same port

# Connect to NAOqi services
laser  = ALProxy("ALLaser",  PEPPER_IP, PEPPER_PORT)
memory = ALProxy("ALMemory", PEPPER_IP, PEPPER_PORT)
motion = ALProxy("ALMotion", PEPPER_IP, PEPPER_PORT)
laser.laserON()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# ───── Constants (front laser only) ───────────────────────────────────────
BASE        = "Device/SubDeviceList/Platform/LaserSensor/"
DEVS        = ["Front/"]      # front laser only
SEGMENTS    = 15              # each beam represents a horizontal angle
TOTAL_BEAMS = SEGMENTS        # = 15

print("[INFO] Sending Pepper front-laser data to {}:{}...".format(ROS_PC_IP, ROS_PC_PORT))

# ───── Loop ──────────────────────────────────────────────────────────────
while True:
    vectors = []

    # Read the 15 segments under Front/
    for dev in DEVS:
        for seg in range(1, SEGMENTS + 1):
            kx = "%s%sHorizontal/Seg%02d/X/Sensor/Value" % (BASE, dev, seg)
            ky = "%s%sHorizontal/Seg%02d/Y/Sensor/Value" % (BASE, dev, seg)
            try:
                x = memory.getData(kx)
                y = memory.getData(ky)
                vectors.append([x, y])
            except:
                # On read error, use infinite range
                vectors.append([float('inf'), float('inf')])

    # Pack as JSON and send via UDP
    payload = json.dumps({"vectors": vectors})
    sock.sendto(payload.encode("utf-8"), (ROS_PC_IP, ROS_PC_PORT))

    time.sleep(0.1)  # 10 Hz
