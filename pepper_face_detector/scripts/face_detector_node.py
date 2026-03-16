#!/usr/bin/env python3

import rospy
import cv2
import numpy as np
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from std_msgs.msg import String, Int32
import os
import rospkg

# Get the path to the package
rospack = rospkg.RosPack()
package_path = rospack.get_path('pepper_face_detector')

class PepperFaceDetector:
    def __init__(self):
        # Initialize the ROS node
        rospy.init_node('pepper_face_detector', anonymous=True)

        # Log node startup
        rospy.loginfo("Starting Simple Face Detector Node")
        
        # Initialize the OpenCV bridge
        self.bridge = CvBridge()
        
        # Load the face cascade classifier
        cascade_path = os.path.join(package_path, 'data', 'haarcascade_frontalface_default.xml')
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            rospy.logerr(f"Error: Could not load face cascade classifier from {cascade_path}")
            return
        rospy.loginfo(f"Loaded face cascade classifier from {cascade_path}")
        
        # Parameters
        self.face_detection_threshold = rospy.get_param('~face_detection_threshold', 0.7)
        self.show_visualization = rospy.get_param('~show_visualization', True)
        
        # Publishers
        self.status_pub = rospy.Publisher('/pepper/face_detector/status', String, queue_size=10)
        self.face_count_pub = rospy.Publisher('/pepper/face_detector/count', Int32, queue_size=10)
        
        # Subscribers
        rospy.Subscriber('/pepper/camera/front/image_raw', Image, self.image_callback)
        
        rospy.loginfo("Simple Face Detector Node initialized successfully")
    
    def image_callback(self, msg):
        """Callback for camera image messages"""
        try:
            # Convert ROS image to OpenCV format
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            # Publish the number of detected faces
            self.face_count_pub.publish(len(faces))
            
            # Process detected faces
            if len(faces) > 0:
                rospy.loginfo(f"Detected {len(faces)} faces!")
                
                # Draw rectangles around faces (for visualization)
                for (x, y, w, h) in faces:
                    cv2.rectangle(cv_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    # Calculate face center
                    face_center_x = x + w//2
                    face_center_y = y + h//2
                    
                    # Draw face center
                    cv2.circle(cv_image, (face_center_x, face_center_y), 5, (0, 0, 255), -1)
                
                # Publish status
                self.status_pub.publish(f"Detected {len(faces)} faces")
            
            # Display the image (optional, for debugging)
            cv2.imshow("Pepper Face Detection", cv_image)
            cv2.waitKey(1)
            
        except Exception as e:
            rospy.logerr(f"Error processing image: {e}")

if __name__ == '__main__':
    try:
        detector = PepperFaceDetector()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
    finally:
        # Clean up
        cv2.destroyAllWindows()
        rospy.loginfo("Face Detector Node shutdown")