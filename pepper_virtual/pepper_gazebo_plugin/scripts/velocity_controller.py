#!/usr/bin/env python3
"""Physics-based velocity controller for pepper_MP in Gazebo.

Subscribes to /pepper/cmd_vel and applies the requested velocity directly
to the Gazebo physics engine via /gazebo/set_entity_state.  Position is
NOT integrated here — it comes from the physics simulation, so collisions,
friction, and the real-time factor are all respected.

The pose sent with each SetEntityState call is always the robot's CURRENT
physics pose (read from /gazebo/model_states), so there is no teleporting.
Only the twist is driven by cmd_vel; Gazebo integrates position from there.
"""
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from gazebo_msgs.msg import ModelStates
from gazebo_msgs.srv import SetEntityState
from gazebo_msgs.msg import EntityState
import geometry_msgs.msg


MODEL_NAME = 'pepper_MP'


class VelocityController(Node):
    def __init__(self):
        super().__init__('velocity_controller')

        self._cmd_vel = Twist()
        self._last_cmd_time = self.get_clock().now()
        self._cmd_timeout = 0.5   # seconds before auto-stop

        # Latest physics pose from /gazebo/model_states
        self._current_pose = geometry_msgs.msg.Pose()
        self._pose_ready = False

        self._sub_cmd = self.create_subscription(
            Twist, '/pepper/cmd_vel', self._cmd_cb, 10)

        self._sub_states = self.create_subscription(
            ModelStates, '/gazebo/model_states', self._states_cb, 10)

        self._set_cli = self.create_client(
            SetEntityState, '/gazebo/set_entity_state')

        # 20 Hz control loop
        self._timer = self.create_timer(0.05, self._update)
        self.get_logger().info('VelocityController ready (physics-based).')

    # ------------------------------------------------------------------
    def _cmd_cb(self, msg: Twist):
        self._cmd_vel = msg
        self._last_cmd_time = self.get_clock().now()

    def _states_cb(self, msg: ModelStates):
        """Cache the current physics pose from Gazebo model states."""
        try:
            idx = msg.name.index(MODEL_NAME)
            self._current_pose = msg.pose[idx]
            self._pose_ready = True
        except ValueError:
            pass

    # ------------------------------------------------------------------
    def _update(self):
        if not self._pose_ready:
            return
        if not self._set_cli.service_is_ready():
            return

        # Zero velocity after timeout (safety stop)
        elapsed = (self.get_clock().now() - self._last_cmd_time).nanoseconds * 1e-9
        cmd = self._cmd_vel if elapsed < self._cmd_timeout else Twist()

        # Convert cmd_vel (robot frame) to world frame using current yaw
        q = self._current_pose.orientation
        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z),
        )
        vx_world = cmd.linear.x * math.cos(yaw) - cmd.linear.y * math.sin(yaw)
        vy_world = cmd.linear.x * math.sin(yaw) + cmd.linear.y * math.cos(yaw)

        # Apply velocity to physics engine; pose = current physics pose (no teleport)
        state = EntityState()
        state.name = MODEL_NAME
        state.reference_frame = 'world'
        state.pose = self._current_pose          # exact current physics pose
        state.twist.linear.x  = vx_world
        state.twist.linear.y  = vy_world
        state.twist.linear.z  = 0.0
        state.twist.angular.x = 0.0
        state.twist.angular.y = 0.0
        state.twist.angular.z = cmd.angular.z

        req = SetEntityState.Request()
        req.state = state
        self._set_cli.call_async(req)


def main(args=None):
    rclpy.init(args=args)
    node = VelocityController()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
