#!/bin/bash

# Wait for the head controller topic to become available
until rostopic info /pepper/Head_controller/command > /dev/null 2>&1
do
  echo "Waiting for the head controller to be ready..."
  sleep 1.0
done

echo "Lifting the head up."
sleep 2.0

# Lift the head up
# HeadPitch: -0.5 radians upwards (negative values look upwards)
# HeadYaw: 0.0 radians (straight forward)
rostopic pub --once /pepper/Head_controller/command trajectory_msgs/JointTrajectory "header:
  seq: 0
  stamp:
    secs: 0
    nsecs: 0
  frame_id: ''
joint_names: ['HeadPitch', 'HeadYaw']
points:
- positions: [-0.25, 0.0]
  velocities: []
  accelerations: []
  effort: []
  time_from_start: {secs: 1, nsecs: 0}"

echo "Head movement completed."
