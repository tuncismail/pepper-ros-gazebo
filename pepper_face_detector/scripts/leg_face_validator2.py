#!/usr/bin/env python3

import rospy
import numpy as np
from people_msgs.msg import PositionMeasurementArray
from std_msgs.msg import Int32, String
from visualization_msgs.msg import Marker, MarkerArray
from people_msgs.msg import People, Person

class LegFaceValidator:
    def __init__(self):
        # Initialize the ROS node
        rospy.init_node('leg_face_validator', anonymous=False)
        
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
        self.markers_pub = rospy.Publisher('/validated_people_markers', MarkerArray, queue_size=10)
        self.people_pub = rospy.Publisher('/people', People, queue_size=10)
        
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
            # Publish empty markers (to clear previous markers)
            self.publish_markers([])
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
        
        # Publish visualization markers
        self.publish_markers(validated_msg.people)

        # In your leg_callback method, after publishing validated legs
        self.publish_people_message(validated_msg.people)

    def publish_markers(self, people):
        """Publish markers for visualization in RViz"""
        marker_array = MarkerArray()
        
        # Create a marker to delete all previous markers
        delete_marker = Marker()
        delete_marker.header.frame_id = "map"  # Use the appropriate frame
        delete_marker.header.stamp = rospy.Time.now()
        delete_marker.ns = "validated_people"
        delete_marker.id = 0
        delete_marker.action = Marker.DELETEALL
        marker_array.markers.append(delete_marker)
        
        # Create markers for each validated person
        for i, person in enumerate(people):
            # Person cylinder marker (body)
            body_marker = Marker()
            body_marker.header.frame_id = "map"  # Use the appropriate frame
            body_marker.header.stamp = rospy.Time.now()
            body_marker.ns = "validated_people"
            body_marker.id = i*3 + 1
            body_marker.type = Marker.CYLINDER
            body_marker.action = Marker.ADD
            
            # Set the position
            body_marker.pose.position.x = person.pos.x
            body_marker.pose.position.y = person.pos.y
            body_marker.pose.position.z = 0.75  # Half height of cylinder
            
            # Set the orientation (identity quaternion)
            body_marker.pose.orientation.w = 1.0
            
            # Set the scale
            body_marker.scale.x = 0.4  # Diameter
            body_marker.scale.y = 0.4  # Diameter
            body_marker.scale.z = 1.5  # Height
            
            # Set the color (green for validated)
            body_marker.color.r = 0.0
            body_marker.color.g = 0.8
            body_marker.color.b = 0.0
            body_marker.color.a = 0.6  # Semi-transparent
            
            # Set lifetime and frame locked
            body_marker.lifetime = rospy.Duration(2.0)  # Markers last for 2 seconds
            
            # Add to array
            marker_array.markers.append(body_marker)
            
            # Person sphere marker (head)
            head_marker = Marker()
            head_marker.header.frame_id = "map"  # Use the appropriate frame
            head_marker.header.stamp = rospy.Time.now()
            head_marker.ns = "validated_people"
            head_marker.id = i*3 + 2
            head_marker.type = Marker.SPHERE
            head_marker.action = Marker.ADD
            
            # Set the position (above the cylinder)
            head_marker.pose.position.x = person.pos.x
            head_marker.pose.position.y = person.pos.y
            head_marker.pose.position.z = 1.7  # Head height
            
            # Set the orientation (identity quaternion)
            head_marker.pose.orientation.w = 1.0
            
            # Set the scale
            head_marker.scale.x = 0.25  # Diameter
            head_marker.scale.y = 0.25  # Diameter
            head_marker.scale.z = 0.25  # Diameter
            
            # Set the color (skin tone for head)
            head_marker.color.r = 0.9
            head_marker.color.g = 0.7
            head_marker.color.b = 0.6
            head_marker.color.a = 0.8
            
            # Set lifetime and frame locked
            head_marker.lifetime = rospy.Duration(2.0)  # Markers last for 2 seconds
            
            # Add to array
            marker_array.markers.append(head_marker)
            
            # Text marker with distance
            text_marker = Marker()
            text_marker.header.frame_id = "map"
            text_marker.header.stamp = rospy.Time.now()
            text_marker.ns = "validated_people"
            text_marker.id = i*3 + 3
            text_marker.type = Marker.TEXT_VIEW_FACING
            text_marker.action = Marker.ADD
            
            # Set the position (above the head)
            text_marker.pose.position.x = person.pos.x
            text_marker.pose.position.y = person.pos.y
            text_marker.pose.position.z = 2.0  # Text height
            
            # Set the scale (text size)
            text_marker.scale.z = 0.3
            
            # Set the color (white text)
            text_marker.color.r = 1.0
            text_marker.color.g = 1.0
            text_marker.color.b = 1.0
            text_marker.color.a = 0.8
            
            # Set the text
            distance = np.sqrt(person.pos.x**2 + person.pos.y**2)
            text_marker.text = f"ID: {person.object_id}\nDist: {distance:.2f}m"
            
            # Set lifetime
            text_marker.lifetime = rospy.Duration(2.0)
            
            # Add to array
            marker_array.markers.append(text_marker)
        
        # Publish marker array
        self.markers_pub.publish(marker_array)
    
    def publish_status(self, event=None):
        """Publish periodic status updates"""
        status = f"Faces: {self.detected_faces}, Time since last face: {(rospy.Time.now() - self.last_face_update).to_sec():.1f}s"
        self.status_pub.publish(status)

    def publish_people_message(self, position_measurements):
        """Convert PositionMeasurementArray to People message and publish"""
        people_msg = People()
        people_msg.header.stamp = rospy.Time.now()
        people_msg.header.frame_id = "map"  # Use the appropriate frame
        
        for measurement in position_measurements:
            person = Person()
            person.name = measurement.object_id
            person.position.x = measurement.pos.x
            person.position.y = measurement.pos.y
            person.position.z = measurement.pos.z
            person.velocity.x = 0.0  # You could add velocity estimation if needed
            person.velocity.y = 0.0
            person.velocity.z = 0.0
            person.reliability = measurement.reliability
            
            people_msg.people.append(person)
        
        self.people_pub.publish(people_msg)

if __name__ == '__main__':
    try:
        validator = LegFaceValidator()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass