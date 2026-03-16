#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import socket
import json
import qi
import threading
import time

# Localhost for UDP (ROS → Pepper bridge on same machine)
LISTEN_IP = "172.23.105.204"
LISTEN_PORT = 5005
BUFFER_SIZE = 1024

# Pepper's real IP for NAOqi session
PEPPER_IP = "192.168.1.188"   # ⚠️ ← Change to your Pepper's IP
PEPPER_PORT = 9559

class VelocityReceiver(object):
    def __init__(self):
        # Setup UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((LISTEN_IP, LISTEN_PORT))
        print("[INFO] Listening for velocity on UDP %s:%d..." % (LISTEN_IP, LISTEN_PORT))

        # Connect to Pepper via qi
        self.session = qi.Session()
        self.session.connect("tcp://{}:{}".format(PEPPER_IP, PEPPER_PORT))
        self.motion = self.session.service("ALMotion")
        self.motion.wakeUp()

        self.running = True
        self.current_cmd = (0.0, 0.0, 0.0)
        self.last_recv_time = time.time()

        # Start motion thread
        self.thread = threading.Thread(target=self.motion_loop)
        self.thread.start()

        self.listen()

    def listen(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(BUFFER_SIZE)
                parsed = json.loads(data)
                self.current_cmd = (
                    float(parsed.get("x", 0.0)),
                    float(parsed.get("y", 0.0)),
                    float(parsed.get("theta", 0.0))
                )
                self.last_recv_time = time.time()
            except Exception as e:
                print("[ERROR] JSON parse failed: %s" % str(e))

    def motion_loop(self):
        while self.running:
            x, y, theta = self.current_cmd
            if time.time() - self.last_recv_time > 1.0:
                self.motion.stopMove()
            else:
                self.motion.moveToward(x, y, theta)
            time.sleep(0.1)

    def shutdown(self):
        self.running = False
        self.motion.stopMove()
        print("[INFO] Shutdown complete")

if __name__ == "__main__":
    try:
        VelocityReceiver()
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
