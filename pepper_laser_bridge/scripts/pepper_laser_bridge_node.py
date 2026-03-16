#!/usr/bin/env python3
import rospy
import socket
import json
import math
import numpy as np
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Header

# --- CONFIGURATION (sadece ön lazer) ---
UDP_IP            = "0.0.0.0"     # Tüm arabirimlerde dinle
UDP_PORT          = 5006
ANGLE_MIN         = -math.pi/6    # -30°
ANGLE_MAX         =  math.pi/6    # +30°
PHYS_SEGMENTS     = 15            # Fiziksel beam sayısı
PUBLISH_SEGMENTS  = 60            # Yayınlamak istediğimiz (interpolated) beam sayısı
# --- END CONFIGURATION ---

def main():
    # /use_sim_time parametresini isteğe bağlı ayarlayın
    rospy.set_param('/use_sim_time', False)
    rospy.init_node("pepper_laser_receiver")
    pub = rospy.Publisher("/real_scan", LaserScan, queue_size=1)

    # UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((UDP_IP, UDP_PORT))
    except socket.error as e:
        rospy.logfatal("Socket bind hatası %s:%d – %s", UDP_IP, UDP_PORT, str(e))
        return

    rospy.loginfo("Listening for front-laser (%d phys → %d pub beams) on UDP %s:%d",
                  PHYS_SEGMENTS, PUBLISH_SEGMENTS, UDP_IP, UDP_PORT)
    rate = rospy.Rate(10)

    while not rospy.is_shutdown():
        try:
            data, _ = sock.recvfrom(16_384)
            parsed   = json.loads(data.decode("utf-8"))
            vectors  = parsed.get("vectors", [])

            # Beam sayısını kontrol et
            if len(vectors) != PHYS_SEGMENTS:
                rospy.logwarn_throttle(
                    5,
                    "Gelen fiziksel beam sayısı %d, beklenen %d",
                    len(vectors),
                    PHYS_SEGMENTS
                )
                continue

            # 1) Fiziksel mesafeleri hesapla
            phys_ranges = np.array([math.hypot(float(x), float(y)) for x, y in vectors])

            # 2) Açı eksenlerini oluştur
            phys_angles = np.linspace(ANGLE_MIN, ANGLE_MAX, PHYS_SEGMENTS)
            pub_angles  = np.linspace(ANGLE_MIN, ANGLE_MAX, PUBLISH_SEGMENTS)

            # 3) Lineer interpolasyon ile yeni mesafeler üret
            interp_ranges = np.interp(pub_angles, phys_angles, phys_ranges)

            # 4) LaserScan mesajını hazırla
            scan = LaserScan()
            scan.header = Header(stamp=rospy.Time(0), frame_id="base_footprint")

            scan.angle_min       = ANGLE_MIN
            scan.angle_max       = ANGLE_MAX
            scan.angle_increment = (ANGLE_MAX - ANGLE_MIN) / (PUBLISH_SEGMENTS - 1)
            scan.time_increment  = 0.0
            scan.scan_time       = 0.1
            scan.range_min       = 0.05
            scan.range_max       = 3.0

            scan.ranges      = interp_ranges.tolist()
            scan.intensities = [1.0] * PUBLISH_SEGMENTS

            pub.publish(scan)

        except json.JSONDecodeError as e:
            rospy.logwarn_throttle(5, "JSON decode hatası: %s", str(e))
        except Exception as e:
            rospy.logerr("UDP işleme hatası: %s", str(e))

        rate.sleep()

    sock.close()
    rospy.loginfo("Laser alıcı node kapatıldı.")

if __name__ == "__main__":
    try:
        main()
    except rospy.ROSInterruptException:
        pass
