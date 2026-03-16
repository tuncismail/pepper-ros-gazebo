#!/usr/bin/env python3

import rospy
import socket
import json
from geometry_msgs.msg import Twist

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

TARGET_IP = None
TARGET_PORT = None

def cmd_vel_callback(msg):
    payload = {
        "x": msg.linear.x,
        "y": msg.linear.y,
        "theta": msg.angular.z
    }
    try:
        sock.sendto(json.dumps(payload).encode("utf-8"), (TARGET_IP, TARGET_PORT))
    except Exception as e:
        rospy.logerr("Failed to send UDP packet: %s", str(e))

def main():
    global TARGET_IP, TARGET_PORT
    rospy.init_node("ros_velocity_publisher")
    TARGET_IP = rospy.get_param("~target_ip", "127.0.0.1")
    TARGET_PORT = rospy.get_param("~target_port", 5005)
    rospy.Subscriber("/pepper/cmd_vel", Twist, cmd_vel_callback)
    rospy.loginfo("Publishing /pepper/cmd_vel via UDP to %s:%d", TARGET_IP, TARGET_PORT)
    rospy.spin()

if __name__ == "__main__":
    try:
        main()
    finally:
        sock.close()
