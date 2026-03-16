#!/usr/bin/env python3

import rospy
import numpy as np
from people_msgs.msg import PositionMeasurementArray
from std_msgs.msg import Int32, String

class LegFaceValidator:
    def __init__(self):
        # Initialize the ROS node
        rospy.init_node('leg_face_validator', anonymous=True)
        
        # Log node startup
        rospy.loginfo("Starting Leg-Face Validator Node")
        
        # Parameters
        self.max_distance = rospy.get_param('~max_distance', 2.0)  # Maximum distance to consider a leg valid when faces are detected
        
        # State variables
        self.detected_faces = 0
        self.last_face_update = rospy.Time.now()
        
        # Publishers
        self.validated_legs_pub = rospy.Publisher('/validated_people_measurements', PositionMeasurementArray, queue_size=10)
        self.status_pub = rospy.Publisher('/leg_face_validator/status', String, queue_size=10)
        
        # Subscribers
        rospy.Subscriber('/people_tracker_measurements', PositionMeasurementArray, self.leg_callback)
        rospy.Subscriber('/pepper/face_detector/count', Int32, self.face_count_callback)
        
        # Timer for periodic status updates
        rospy.Timer(rospy.Duration(1.0), self.publish_status)
        
        rospy.loginfo("Leg-Face Validator Node initialized successfully")
    
    def face_count_callback(self, msg):
        """Callback for face detection count messages"""
        self.detected_faces = msg.data
        self.last_face_update = rospy.Time.now()
        rospy.loginfo(f"Received face count: {self.detected_faces}")
    
    def leg_callback(self, msg):
        """Callback for leg detection messages"""
        # Create a new message for validated legs
        validated_msg = PositionMeasurementArray()
        validated_msg.header = msg.header
        
        # If no legs detected, just publish empty message
        if not msg.people:
            self.validated_legs_pub.publish(validated_msg)
            return
        
        # Check if we have recent face detections (within last 2 seconds)
        time_since_face_update = (rospy.Time.now() - self.last_face_update).to_sec()
        
        if self.detected_faces > 0 and time_since_face_update < 2.0:
            # We have faces detected, only keep legs within max_distance of robot
            rospy.loginfo(f"Validating legs with {self.detected_faces} faces detected")
            
            for person in msg.people:
                # Calculate distance from robot (assuming robot is at origin)
                distance = np.sqrt(person.pos.x**2 + person.pos.y**2)
                
                if distance <= self.max_distance:
                    # This leg is within range, keep it
                    validated_msg.people.append(person)
                    rospy.loginfo(f"Validated leg at ({person.pos.x:.2f}, {person.pos.y:.2f}), distance: {distance:.2f}m")
                else:
                    rospy.loginfo(f"Rejected leg at ({person.pos.x:.2f}, {person.pos.y:.2f}), distance: {distance:.2f}m")
        else:
            # No faces detected, pass through all leg detections
            rospy.loginfo("No faces detected, passing through all leg detections")
            validated_msg.people = msg.people
        
        # Publish validated legs
        self.validated_legs_pub.publish(validated_msg)
    
    def publish_status(self, event=None):
        """Publish periodic status updates"""
        status = f"Faces: {self.detected_faces}, Time since last face: {(rospy.Time.now() - self.last_face_update).to_sec():.1f}s"
        self.status_pub.publish(status)

if __name__ == '__main__':
    try:
        validator = LegFaceValidator()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass