# Pepper Robot Gazebo Simulation (ROS 2 Humble)

A complete ROS 2 Humble simulation environment for the [SoftBank Pepper humanoid robot](https://www.softbankrobotics.com/emea/en/pepper), with Gazebo Classic 11, joint control, autonomous navigation, and realistic odometry.

> **Ported from ROS 1 → ROS 2 Humble** (Ubuntu 22.04). All packages migrated to ament/colcon. Fully containerized for Apple Silicon (arm64) and x86_64 via Docker x86 emulation.

## Branches

| Branch | ROS Version | Platform | How to run |
|--------|-------------|----------|------------|
| `main` | ROS Noetic | macOS / any | Docker — browser GUI via noVNC |
| `ubuntu` | ROS Noetic | Ubuntu 20.04 | Native or Docker |
| `humble` | **ROS 2 Humble** | macOS / any | Docker — browser GUI via noVNC |

---

## Features

- **Browser-based GUI** — Gazebo renders inside a noVNC window at `http://localhost:6080/vnc.html`. No XQuartz or X11 forwarding needed.
- **One-command start** — `docker-compose up pepper_gui` builds and launches everything.
- **Apple Silicon compatible** — runs on arm64 via Docker x86 emulation.
- **Joint control** — ros2_control with joint_state_broadcaster, head and pelvis trajectory controllers.
- **Physics-based velocity** — velocity controller reads current pose from Gazebo physics, applies cmd_vel without teleportation.
- **Realistic odometry** — Gaussian noise (σ_xy=0.005m, σ_yaw=0.001rad) calibrated to real Pepper, plus a groundtruth topic.
- **Navigation stack** — Nav2 with SLAM (slam_toolbox) or AMCL localization, DWB local planner.
- **Multiple worlds** — empty, house, small office, office with people, nao test arena.
- **Merged laser scan** — three physical laser sensors combined into a single `/pepper/scan_merged` topic.
- **gazebo_ros2_control patch** — fixes the URDF-in-argv crash that breaks controller_manager on large URDFs.

---

## Quick Start (Docker)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (with BuildKit enabled)
- A modern browser (Chrome, Firefox, Safari)

### Run

```bash
git clone -b humble https://github.com/tuncismail/pepper-ros-gazebo.git
cd pepper-ros-gazebo

docker-compose up pepper_gui
```

Open your browser at:

```
http://localhost:6080/vnc.html?autoconnect=true&resize=scale
```

Gazebo will load with Pepper in an empty world. First build takes ~10–15 min.

### Headless (no display)

```bash
docker-compose up pepper_headless
```

### Interactive shell

```bash
docker-compose run --rm pepper_shell
```

---

## Architecture

```
pepper-ros-gazebo/
│
├── Dockerfile                   # ROS 2 Humble + Gazebo 11 image (amd64)
├── docker-compose.yml           # GUI / headless / shell services
├── docker-entrypoint.sh         # Xvnc → openbox → noVNC → ros2 launch
├── test_e2e_headless.sh         # End-to-end test (headless, 9 checks)
├── patches/                     # Source patches (gazebo_ros2_control fix)
│
├── pepper_robot/                # Pepper URDF description & metapackage
├── pepper_virtual/              # Gazebo plugin, controllers, launch files
├── pepper_meshes/               # 3D mesh files (CC-BY-NC-ND 4.0)
├── gazebo_model_velocity_plugin/# Base velocity Gazebo plugin (C++)
├── pepper_laser_bridge/         # Laser data bridge (sim ↔ real robot)
├── velocity_bridge/             # cmd_vel bridge
│
├── people/                      # [COLCON_IGNORE] ROS 1 leg detector suite
├── pepper_face_detector/        # [COLCON_IGNORE] ROS 1 face detection
├── navigation_layers/           # [COLCON_IGNORE] ROS 1 costmap layers
└── pepper_bridge/               # [COLCON_IGNORE] ROS 1 NAOqi bridge
```

### GUI pipeline (inside container)

```
Xvnc :1 (port 5901)
  └── openbox (window manager)
  └── ros2 launch Gazebo (DISPLAY=:1)
websockify → noVNC (port 6080)  ←  browser
```

---

## Packages

### `pepper_robot` / `pepper_description`

URDF model of Pepper with corrected TF tree (`base_footprint`-oriented). Includes joint definitions, inertias, and sensor mounts. Uses the no-arms CPU variant for simulation.

### `pepper_virtual`

#### `pepper_gazebo_plugin`

Launches Pepper in Gazebo. Handles sensor plugins (camera, depth, laser), spawns the robot, runs velocity and odometry nodes.

Scripts:
- `laser_publisher.py` — merges 3 laser sensors into a unified `/pepper/scan_merged` topic
- `velocity_controller.py` — physics-based base motion via `/pepper/cmd_vel`
- `odom_publisher.py` — publishes `/pepper/odom` (noisy) and `/pepper/odom_groundtruth` (clean)

Config:
- `nav2_params.yaml` — full Nav2 configuration (AMCL, DWB, costmaps, SLAM)

#### `pepper_control`

ROS 2 controllers for Pepper's joints using `ros2_control`.

Config: `pepper_ros2_controllers.yaml`

| Controller | Type | Joints |
|-----------|------|--------|
| `joint_state_broadcaster` | JointStateBroadcaster | all |
| `head_controller` | JointTrajectoryController | HeadYaw, HeadPitch |
| `pelvis_controller` | JointTrajectoryController | HipRoll, HipPitch, KneePitch |

### `gazebo_model_velocity_plugin`

Gazebo world plugin (C++) that drives Pepper's base. Provides the physics interface used by `velocity_controller.py`.

### `patches/fix_gazebo_ros2_control_urdf_argv.patch`

Patches `gazebo_ros2_control` 0.4.10 to fix a crash where `rcl_parse_arguments()` fails on large URDFs passed via `--param` argv. The fix passes `robot_description` via `NodeOptions::append_parameter_override()` instead.

---

## Launch Files

All launch files are in `pepper_virtual/pepper_gazebo_plugin/launch/`.

### Simulation variants

| Launch file | World |
|------------|-------|
| `pepper_gazebo_plugin_Y20_CPU_no_arms.launch.py` | empty (default) |
| `pepper_gazebo_plugin_house1.launch.py` | house |
| `pepper_gazebo_plugin_small_office.launch.py` | small office |
| `pepper_gazebo_plugin_simple_office_with_people.launch.py` | office with people |
| `pepper_gazebo_plugin_nao_test.launch.py` | nao test arena |

### Navigation

```bash
# Launch with SLAM (default)
ros2 launch pepper_gazebo_plugin pepper_navigation.launch.py

# Launch with AMCL + existing map
ros2 launch pepper_gazebo_plugin pepper_navigation.launch.py use_slam:=false map:=/path/to/map.yaml

# Choose a different world
ros2 launch pepper_gazebo_plugin pepper_navigation.launch.py world:=house1.world
```

---

## Control Commands

### Base movement (`cmd_vel`)

```bash
# Move forward
ros2 topic pub --once /pepper/cmd_vel geometry_msgs/msg/Twist \
  '{"linear": {"x": 0.3}, "angular": {"z": 0.0}}'

# Rotate in place
ros2 topic pub --once /pepper/cmd_vel geometry_msgs/msg/Twist \
  '{"linear": {"x": 0.0}, "angular": {"z": 0.5}}'

# Stop
ros2 topic pub --once /pepper/cmd_vel geometry_msgs/msg/Twist \
  '{"linear": {"x": 0.0}, "angular": {"z": 0.0}}'
```

### Head control

```bash
ros2 action send_goal /head_controller/follow_joint_trajectory \
  control_msgs/action/FollowJointTrajectory \
  '{trajectory: {joint_names: ["HeadYaw", "HeadPitch"],
    points: [{positions: [0.5, -0.2], time_from_start: {sec: 1}}]}}'
```

### Pelvis control

```bash
ros2 action send_goal /pelvis_controller/follow_joint_trajectory \
  control_msgs/action/FollowJointTrajectory \
  '{trajectory: {joint_names: ["HipRoll", "HipPitch", "KneePitch"],
    points: [{positions: [0.0, 0.1, 0.1], time_from_start: {sec: 1}}]}}'
```

### Key topics

| Topic | Type | Description |
|-------|------|-------------|
| `/pepper/cmd_vel` | `geometry_msgs/msg/Twist` | Base velocity command |
| `/pepper/odom` | `nav_msgs/msg/Odometry` | Base odometry (with noise) |
| `/pepper/odom_groundtruth` | `nav_msgs/msg/Odometry` | Ground truth odometry |
| `/pepper/scan_front` | `sensor_msgs/msg/LaserScan` | Front laser scan |
| `/pepper/scan_left` | `sensor_msgs/msg/LaserScan` | Left laser scan |
| `/pepper/scan_right` | `sensor_msgs/msg/LaserScan` | Right laser scan |
| `/pepper/scan_merged` | `sensor_msgs/msg/LaserScan` | Merged 360° laser scan |
| `/pepper/camera/front/image_raw` | `sensor_msgs/msg/Image` | Front RGB camera |
| `/pepper/camera/depth/image_raw` | `sensor_msgs/msg/Image` | Depth camera |
| `/joint_states` | `sensor_msgs/msg/JointState` | All joint states |
| `/tf` | `tf2_msgs/msg/TFMessage` | TF transforms |

### Navigation topics (when using `pepper_navigation.launch.py`)

| Topic | Type | Description |
|-------|------|-------------|
| `/goal_pose` | `geometry_msgs/msg/PoseStamped` | Navigation goal |
| `/map` | `nav_msgs/msg/OccupancyGrid` | SLAM/map server output |
| `/local_costmap/costmap` | `nav_msgs/msg/OccupancyGrid` | Local costmap |
| `/global_costmap/costmap` | `nav_msgs/msg/OccupancyGrid` | Global costmap |

---

## Docker Reference

### Build manually

```bash
docker build --platform linux/amd64 -t pepper_with_gazebo:humble .
```

### Run manually

```bash
# GUI mode (browser)
docker run -d --rm --init \
  --name pepper_gui \
  -p 6080:6080 -p 5901:5901 \
  --platform linux/amd64 \
  pepper_with_gazebo:humble gui

# Then open:
# http://localhost:6080/vnc.html?autoconnect=true&resize=scale

# Headless
docker run --rm --init --platform linux/amd64 \
  pepper_with_gazebo:humble headless

# Interactive shell
docker run -it --rm --init --platform linux/amd64 \
  pepper_with_gazebo:humble bash
```

### Docker Compose services

| Service | Description | URL |
|---------|-------------|-----|
| `pepper_gui` | Full GUI via browser (noVNC) | http://localhost:6080/vnc.html |
| `pepper_headless` | Headless Gazebo (no display) | — |
| `pepper_shell` | Interactive bash shell | — |

---

## Testing

An end-to-end headless test verifies 9 checks:

```bash
# Inside Docker
docker-compose run --rm pepper_shell bash /colcon_ws/src/test_e2e_headless.sh
```

The test verifies:
- Xvfb + Gazebo start successfully
- Pepper model spawns in Gazebo
- All laser scan topics active (`/pepper/scan_front`, `scan_left`, `scan_right`)
- `/joint_states` and `/tf` publishing
- `/pepper/odom` publishing (confirms odom_publisher + model spawn)
- `robot_description` parameter loaded on `/robot_state_publisher`
- `/pepper/cmd_vel` accepts velocity commands

---

## Notes & Known Limitations

- **ROS 1 packages disabled** — `people/`, `pepper_face_detector/`, `navigation_layers/`, `pepper_bridge/` are marked with `COLCON_IGNORE`. They require ROS 1 (rospy/catkin) and need porting to work with ROS 2.
- **No arm controllers** — the no-arms URDF variant is used; arm joints are not simulated.
- **x86 emulation on Apple Silicon** — Gazebo runs under Docker's x86 emulation, which is slower than native. Expect ~55s startup time for the simulation.
- **VNC has no password** — for LAN/local use only. Do not expose port 5901 to the internet.
- **gazebo_ros2_control patch** — built from source with a patch because the apt package crashes on Pepper's large URDF. See `patches/` for details.

---

## Credits

This project is based on and extends the following upstream work:

- [ros-naoqi/pepper_virtual](https://github.com/ros-naoqi/pepper_virtual) — original Pepper Gazebo simulation
- [ros-naoqi/pepper_robot](https://github.com/ros-naoqi/pepper_robot) — Pepper URDF description
- [awesomebytes/gazebo_model_velocity_plugin](https://github.com/awesomebytes/gazebo_model_velocity_plugin) — base velocity plugin
- [ros-controls/gazebo_ros2_control](https://github.com/ros-controls/gazebo_ros2_control) — ros2_control Gazebo integration

---

## License

- Project code: see [LICENSE](LICENSE)
- Pepper meshes (`pepper_meshes/`): [CC-BY-NC-ND 4.0](pepper_meshes/debian_license/) — Aldebaran Robotics / SoftBank
