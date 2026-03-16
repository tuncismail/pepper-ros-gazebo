#!/usr/bin/env python3
import rospy
import socket
import json
import math
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Header

# --- CONFIGURATION ---
UDP_IP = "0.0.0.0"  # Listen on all available interfaces
UDP_PORT = 5006
ANGLE_MIN = -math.pi / 2  # Total scan angle minimum
ANGLE_MAX = math.pi / 2   # Total scan angle maximum

# Original physical segments: 3 devices * 15 segments/device = 45
# New subdivided segments: 45 physical segments * 4 subdivisions/segment = 180
NUM_SEGMENTS =  45 #* 4 # This MUST match the total number of items in 'vectors' from the sender
# --- END CONFIGURATION ---

def main():
    rospy.set_param('/use_sim_time', False) # Keep as False if using real robot time
    rospy.init_node("pepper_laser_receiver")
    pub = rospy.Publisher("/real_scan", LaserScan, queue_size=10)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((UDP_IP, UDP_PORT))
    except socket.error as e:
        rospy.logfatal("Failed to bind socket on %s:%d. Error: %s", UDP_IP, UDP_PORT, str(e))
        rospy.logfatal("Is another process using this port? Try 'sudo netstat -tulnp | grep %d'", UDP_PORT)
        return

    rospy.loginfo("Listening on UDP port %s:%d for %d laser segments...", UDP_IP, UDP_PORT, NUM_SEGMENTS)

    rate = rospy.Rate(10)  # Match sender's rate or slightly higher
    while not rospy.is_shutdown():
        try:
            data, addr = sock.recvfrom(16384) # Increased buffer size for larger payload
            # rospy.logdebug("Received %d bytes from %s", len(data), addr)
            parsed = json.loads(data.decode("utf-8"))
            vectors = parsed.get("vectors", [])

            if len(vectors) != NUM_SEGMENTS:
                rospy.logwarn_throttle(5, "Invalid vector count: received %d, expected %d. Check sender's SUBDIVISION_FACTOR and physical segment count.", len(vectors), NUM_SEGMENTS)
                continue

            ranges = []
            for vec in vectors:
                x, y = vec
                # Ensure x and y are floats, as JSON might parse them as int if 0.0
                dist = math.sqrt(float(x)**2 + float(y)**2)
                ranges.append(dist)

            scan = LaserScan()
            scan.header = Header()
            scan.header.stamp = rospy.Time(0) # rviz ile 
 #scan.header.stamp = rospy.Time.now() - rospy.Duration(0.1)  
            # scan.header.stamp = rospy.Time.now()
            scan.header.frame_id = "base_footprint" #"laser" # Or "base_laser_link" or similar, matching your Pepper's TF
            scan.angle_min = ANGLE_MIN
            scan.angle_max = ANGLE_MAX
            # Angle increment is now smaller because NUM_SEGMENTS is larger
            scan.angle_increment = (ANGLE_MAX - ANGLE_MIN) / (NUM_SEGMENTS -1) if NUM_SEGMENTS > 1 else 0.0 # Avoid division by zero if NUM_SEGMENTS is 1; ensure it's float division
            scan.time_increment = 0.0  # Assuming all points in a scan are simultaneous
            scan.scan_time = 0.1       # Corresponds to 10 Hz
            scan.range_min = 0.05      # Minimum reliable laser range
            scan.range_max = 3.0       # Maximum reliable laser range (Pepper's spec might vary slightly)
            scan.ranges = ranges
            scan.intensities = []      # Pepper laser doesn't provide intensity

            pub.publish(scan)

        except json.JSONDecodeError as e:
            rospy.logwarn_throttle(5, "JSON decode error: %s. Received data: %s", str(e), data[:200]) # Log first 200 chars
        except socket.timeout: # Add timeout if you set one on the socket
            rospy.logdebug("Socket recvfrom timeout")
            continue
        except Exception as e:
            rospy.logerr("UDP receive/processing error: %s", str(e))

        rate.sleep()

    sock.close()
    rospy.loginfo("Pepper laser receiver node shut down.")

if __name__ == "__main__":
    try:
        main()
    except rospy.ROSInterruptException:
        pass