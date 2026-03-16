#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import socket
import math
import json
import time
from naoqi import ALProxy

# ───── Setup ─────────────────────────────────────────────────────────────
PEPPER_IP   = "192.168.1.188"    # Pepper’ın IP’si
PEPPER_PORT = 9559
ROS_PC_IP   = "172.23.105.204"   # ROS PC’nizin IP’si
ROS_PC_PORT = 5006               # Aynı portu alıcı da dinlemeli

# NAOqi servislerine bağlan
laser  = ALProxy("ALLaser",  PEPPER_IP, PEPPER_PORT)
memory = ALProxy("ALMemory", PEPPER_IP, PEPPER_PORT)
motion = ALProxy("ALMotion", PEPPER_IP, PEPPER_PORT)
laser.laserON()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# ───── Constants (sadece ön lazer) ───────────────────────────────────────
BASE        = "Device/SubDeviceList/Platform/LaserSensor/"
DEVS        = ["Front/"]      # ◀︎ sadece ön lazer
SEGMENTS    = 15              # her beam bir yatay açıyı temsil eder
TOTAL_BEAMS = SEGMENTS        # = 15

print("[INFO] Sending Pepper front-laser data to {}:{}...".format(ROS_PC_IP, ROS_PC_PORT))

# ───── Loop ──────────────────────────────────────────────────────────────
while True:
    vectors = []

    # Sadece Front/ altındaki 15 segmanı oku
    for dev in DEVS:
        for seg in range(1, SEGMENTS + 1):
            kx = "%s%sHorizontal/Seg%02d/X/Sensor/Value" % (BASE, dev, seg)
            ky = "%s%sHorizontal/Seg%02d/Y/Sensor/Value" % (BASE, dev, seg)
            try:
                x = memory.getData(kx)
                y = memory.getData(ky)
                vectors.append([x, y])
            except:
                # Okuma hatasıysa sonsuz uzaklık
                vectors.append([float('inf'), float('inf')])

    # JSON olarak paketle ve UDP ile gönder
    payload = json.dumps({"vectors": vectors})
    sock.sendto(payload.encode("utf-8"), (ROS_PC_IP, ROS_PC_PORT))

    time.sleep(0.1)  # 10 Hz
