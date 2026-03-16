#!/usr/bin/env python3

import rospy
import socket
import json
from geometry_msgs.msg import Twist

# Localhost IP and port for UDP communication
TARGET_IP = "172.23.105.204"  # Change to receiver IP if remote
TARGET_PORT = 5005       # Must match the receiver

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def cmd_vel_callback(msg):
    payload = {
        "x": msg.linear.x,
        "y": msg.linear.y,
        "theta": msg.angular.z
    }
    sock.sendto(json.dumps(payload).encode("utf-8"), (TARGET_IP, TARGET_PORT))

def main():
    rospy.init_node("ros_velocity_publisher")
    rospy.Subscriber("/pepper/cmd_vel", Twist, cmd_vel_callback)
    rospy.loginfo("Publishing /pepper/cmd_vel via UDP to %s:%d", TARGET_IP, TARGET_PORT)
    rospy.spin()

if __name__ == "__main__":
    main()
