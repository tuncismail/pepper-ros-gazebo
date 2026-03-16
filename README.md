# Pepper Robot Gazebo Simulation

A complete ROS Noetic simulation environment for the [SoftBank Pepper humanoid robot](https://www.softbankrobotics.com/emea/en/pepper), with Gazebo 11, autonomous navigation, people detection, and face detection — all runnable in a single Docker container with a browser-based GUI (no XQuartz required).

> **Ported from ROS Kinetic → ROS Noetic** (Ubuntu 20.04). All Python 2 code migrated to Python 3. Fully containerized for Apple Silicon (arm64) and x86_64.

---

## Table of Contents

- [Features](#features)
- [Quick Start (Docker)](#quick-start-docker)
- [Architecture](#architecture)
- [Packages](#packages)
- [Launch Files](#launch-files)
- [Control Commands](#control-commands)
- [Navigation](#navigation)
- [People & Face Detection](#people--face-detection)
- [Native Installation](#native-installation)
- [Docker Reference](#docker-reference)
- [Testing](#testing)
- [License](#license)

---

## Features

- **Browser-based GUI** — Gazebo renders inside a noVNC window accessible at `http://localhost:6080/vnc.html`. No XQuartz, no X11 forwarding needed on macOS.
- **One-command start** — `docker-compose up pepper_gui` builds and launches everything.
- **Apple Silicon (arm64) compatible** — all dependencies resolved for arm64 Ubuntu 20.04.
- **Realistic odometry** — Gaussian noise and drift matching real Pepper hardware.
- **Multiple simulation variants** — GPU / CPU / no-arms / office / house / navigation worlds.
- **Full navigation stack** — AMCL, move_base, costmap layers (range sensor + social navigation).
- **People detection suite** — leg detector (laser-based ML), face detector (OpenCV Haar cascade), velocity tracker.
- **ROS control** — trajectory controllers for head, pelvis, and arms; velocity plugin for base movement.
- **Real robot bridge** — `pepper_bridge` package for bridging to physical Pepper via NAOqi (excluded from Docker build; Python 2 + NAOqi SDK required).

---

## Quick Start (Docker)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (with BuildKit enabled)
- A modern browser (Chrome, Firefox, Safari)

### Run

```bash
git clone https://github.com/tuncismail/pepper_with_gazebo.git
cd pepper_with_gazebo

docker-compose up pepper_gui
```

Open your browser at:

```
http://localhost:6080/vnc.html?autoconnect=true&resize=scale
```

Gazebo will load with Pepper standing in an empty world. The first run builds the Docker image (~10–15 min depending on connection speed).

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
pepper_with_gazebo/
│
├── Dockerfile                   # ROS Noetic + Gazebo 11 image (arm64 + amd64)
├── docker-compose.yml           # GUI / headless / shell services
├── docker-entrypoint.sh         # Xvnc → openbox → noVNC → roslaunch
├── test_e2e_headless.sh         # End-to-end test (headless)
│
├── pepper_robot/                # Pepper URDF description & metapackage
├── pepper_virtual/              # Gazebo plugin + ROS controllers
├── pepper_meshes/               # 3D mesh files (CC-BY-NC-ND 4.0)
├── gazebo_model_velocity_plugin/# Base velocity plugin (odometry, noise, limits)
├── people/                      # Leg detector, tracking filter, velocity tracker
├── pepper_face_detector/        # OpenCV Haar cascade face detection
├── pepper_laser_bridge/         # Laser data bridge (sim ↔ real)
├── velocity_bridge/             # cmd_vel bridge
├── navigation_layers/           # Range sensor + social navigation costmap layers
└── pepper_bridge/               # Real robot bridge (NAOqi, excluded from Docker)
```

### GUI pipeline (inside container)

```
Xvnc :1 (port 5901)
  └── openbox (window manager)
  └── roslaunch Gazebo (DISPLAY=:1)
websockify → noVNC (port 6080)  ←  browser
```

---

## Packages

### `pepper_robot` / `pepper_description`

URDF model of Pepper with corrected TF tree (`base_footprint`-oriented). Includes all joint definitions, inertias, and sensor mounts.

Key files:
- `pepper_description/urdf/pepper.urdf.xacro` — main robot model
- `pepper_description/launch/pepper_upload_CPU_no_arms.launch` — upload URDF to parameter server (CPU, no arms)

### `pepper_virtual`

#### `pepper_gazebo_plugin`

Launches Pepper in Gazebo. Handles sensor plugins (camera, depth, laser), loads controllers, spawns the robot model.

Config files (in `config/`):
| File | Purpose |
|------|---------|
| `costmap_common_params.yaml` | Shared costmap parameters |
| `global_costmap_params.yaml` | Global planner costmap |
| `local_costmap_params.yaml` | Local planner costmap |
| `dwa_local_planner_params.yaml` | DWA planner tuning |
| `base_local_planner_params.yaml` | Base planner parameters |

Scripts:
- `laser_publisher.py` — merges 3 laser sensors into a unified `/pepper/scan` topic
- `pub_lasers.py` — publishes individual laser scans

#### `pepper_control`

ROS controllers for Pepper's joints using `ros_control`.

Config: `pepper_trajectory_control.yaml`

| Controller | Type | Joints |
|-----------|------|--------|
| `joint_state_controller` | JointStateController | all |
| `Head_controller` | JointTrajectoryController | HeadYaw, HeadPitch |
| `Pelvis_controller` | JointTrajectoryController | HipRoll, HipPitch, KneePitch |
| `LeftArm_controller` | JointTrajectoryController | LShoulderPitch, LShoulderRoll, LElbowYaw, LElbowRoll, LWristYaw |
| `RightArm_controller` | JointTrajectoryController | RShoulderPitch, RShoulderRoll, RElbowYaw, RElbowRoll, RWristYaw |

### `gazebo_model_velocity_plugin`

Gazebo world plugin that drives Pepper's base via `/pepper/cmd_vel`. Features:
- Gaussian odometry noise (XY + Yaw configurable)
- Velocity, acceleration, and jerk limits
- Publishes `/pepper/odom` with realistic drift

### `people`

People detection and tracking suite:

| Package | Purpose |
|---------|---------|
| `people_msgs` | Custom message types (`Person`, `People`, `PositionMeasurement`) |
| `leg_detector` | ML-based leg detection from 2D laser scan |
| `people_tracking_filter` | Kalman filter for person position tracking |
| `people_velocity_tracker` | Tracks velocity of detected persons (requires `easy_markers` + `kalman_filter` — excluded from Docker build via `CATKIN_IGNORE`) |

### `pepper_face_detector`

Face detection using OpenCV Haar cascades. Subscribes to `/pepper/camera/front/image_raw`, publishes detected faces and combined people+face detections.

- `face_detector_node.py` — detects faces, publishes bounding boxes
- `leg_face_validator2.py` — validates leg detections with face confirmation, publishes `/people`

### `navigation_layers`

Custom costmap plugins:
- `range_sensor_layer` — adds sonar/IR range sensors to the costmap
- `social_navigation_layers` — maintains personal space around detected people

### `pepper_laser_bridge` / `velocity_bridge`

Lightweight bridges for republishing laser scans and velocity commands between namespaces.

---

## Launch Files

### Simulation variants

| Launch file | World | GPU | Arms |
|------------|-------|-----|------|
| `pepper_gazebo_plugin_Y20.launch` | empty | yes | yes |
| `pepper_gazebo_plugin_Y20_CPU.launch` | empty | no | yes |
| `pepper_gazebo_plugin_Y20_CPU_no_arms.launch` | empty | no | no |
| `pepper_gazebo_plugin_in_office.launch` | office | yes | yes |
| `pepper_gazebo_plugin_in_office_CPU.launch` | office | no | yes |
| `pepper_gazebo_plugin_in_office_CPU_no_arms.launch` | office | no | no |
| `pepper_gazebo_plugin_house_CPU_no_arms.launch` | house | no | no |
| `pepper_gazebo_plugin_Y20_CPU_no_arms_navigation.launch` | empty | no | no |

> All launch files are in `pepper_virtual/pepper_gazebo_plugin/launch/`.

### Navigation & mapping

```bash
# Start navigation (after simulation is running)
roslaunch pepper_gazebo_plugin pepper_gazebo_plugin_Y20_CPU_no_arms_navigation.launch

# Mapping
roslaunch pepper_gazebo_plugin pepper_mapping.launch
```

### People detection

```bash
roslaunch leg_detector leg_detector.launch
roslaunch people_tracking_filter filter.launch
roslaunch pepper_face_detector face_detector.launch
roslaunch pepper_face_detector leg_face_validator.launch
```

---

## Control Commands

### Base movement (`cmd_vel`)

```bash
# Move forward
rostopic pub /pepper/cmd_vel geometry_msgs/Twist \
  "linear: {x: 0.3, y: 0.0, z: 0.0}" \
  "angular: {x: 0.0, y: 0.0, z: 0.0}" --once

# Rotate in place
rostopic pub /pepper/cmd_vel geometry_msgs/Twist \
  "linear: {x: 0.0, y: 0.0, z: 0.0}" \
  "angular: {x: 0.0, y: 0.0, z: 0.5}" --once

# Stop
rostopic pub /pepper/cmd_vel geometry_msgs/Twist "{}" --once
```

### Head control

```bash
rostopic pub /pepper/Head_controller/command \
  trajectory_msgs/JointTrajectory \
  '{joint_names: ["HeadYaw","HeadPitch"],
    points: [{positions: [0.5, -0.2], velocities: [0,0], time_from_start: {secs: 1}}]}' --once
```

### Pelvis control

```bash
rostopic pub /pepper/Pelvis_controller/command \
  trajectory_msgs/JointTrajectory \
  '{joint_names: ["HipRoll","HipPitch","KneePitch"],
    points: [{positions: [0.0, 0.1, 0.1], velocities: [0,0,0], time_from_start: {secs: 1}}]}' --once
```

### Key topics

| Topic | Type | Description |
|-------|------|-------------|
| `/pepper/cmd_vel` | `geometry_msgs/Twist` | Base velocity command |
| `/pepper/odom` | `nav_msgs/Odometry` | Base odometry |
| `/pepper/scan` | `sensor_msgs/LaserScan` | Merged laser scan |
| `/pepper/camera/front/image_raw` | `sensor_msgs/Image` | Front RGB camera |
| `/pepper/camera/depth/image_raw` | `sensor_msgs/Image` | Depth camera |
| `/pepper/joint_states` | `sensor_msgs/JointState` | All joint states |
| `/pepper/Head_controller/command` | `trajectory_msgs/JointTrajectory` | Head trajectory |
| `/pepper/Pelvis_controller/command` | `trajectory_msgs/JointTrajectory` | Pelvis trajectory |
| `/pepper/LeftArm_controller/command` | `trajectory_msgs/JointTrajectory` | Left arm trajectory |
| `/pepper/RightArm_controller/command` | `trajectory_msgs/JointTrajectory` | Right arm trajectory |
| `/people` | `people_msgs/People` | Detected people |
| `/face_detections` | custom | Detected faces |

---

## Navigation

The navigation stack uses AMCL for localization and `move_base` for path planning.

```bash
# Inside the container, after simulation is up:
roslaunch pepper_gazebo_plugin pepper_gazebo_plugin_Y20_CPU_no_arms_navigation.launch

# Send a navigation goal via RViz or:
rostopic pub /move_base_simple/goal geometry_msgs/PoseStamped \
  '{header: {frame_id: "map"},
    pose: {position: {x: 2.0, y: 1.0, z: 0.0},
           orientation: {w: 1.0}}}' --once
```

---

## Native Installation

If you prefer to run without Docker (ROS Noetic on Ubuntu 20.04 required):

```bash
# Install ROS Noetic
# http://wiki.ros.org/noetic/Installation/Ubuntu

sudo apt-get install -y \
  ros-noetic-gazebo-ros ros-noetic-gazebo-ros-control ros-noetic-gazebo-plugins \
  ros-noetic-ros-control ros-noetic-ros-controllers ros-noetic-controller-manager \
  ros-noetic-navigation ros-noetic-move-base ros-noetic-amcl \
  ros-noetic-tf2-sensor-msgs ros-noetic-tf2-geometry-msgs \
  ros-noetic-depthimage-to-laserscan ros-noetic-pcl-ros \
  ros-noetic-robot-state-publisher ros-noetic-joint-state-publisher ros-noetic-xacro \
  ros-noetic-cv-bridge ros-noetic-image-transport python3-opencv \
  ros-noetic-ddynamic-reconfigure \
  liborocos-bfl-dev libprotobuf-dev protobuf-compiler

mkdir -p ~/catkin_ws/src
cd ~/catkin_ws/src

git clone https://github.com/tuncismail/pepper_with_gazebo.git

# Skip packages with unresolvable dependencies
touch pepper_with_gazebo/people/people_velocity_tracker/CATKIN_IGNORE

cd ~/catkin_ws
source /opt/ros/noetic/setup.bash
catkin_make -DCMAKE_BUILD_TYPE=Release -DCATKIN_ENABLE_TESTING=OFF
source devel/setup.bash

export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:$(rospack find pepper_gazebo_plugin)/models

# Launch
roslaunch pepper_gazebo_plugin pepper_gazebo_plugin_Y20_CPU_no_arms.launch
```

---

## Docker Reference

### Build manually

```bash
docker build -t pepper_with_gazebo:noetic .
```

### Run manually

```bash
# GUI mode (browser)
docker run -d --rm --init \
  --name pepper_gui \
  -p 6080:6080 -p 5901:5901 \
  pepper_with_gazebo:noetic gui

# Then open:
# http://localhost:6080/vnc.html?autoconnect=true&resize=scale

# Headless
docker run --rm --init pepper_with_gazebo:noetic headless

# Interactive shell
docker run -it --rm --init pepper_with_gazebo:noetic bash
```

### Docker Compose services

| Service | Description | URL |
|---------|-------------|-----|
| `pepper_gui` | Full GUI via browser (noVNC) | http://localhost:6080/vnc.html |
| `pepper_headless` | Headless Gazebo (no display) | — |
| `pepper_shell` | Interactive bash shell | — |

```bash
# GUI
docker-compose up pepper_gui

# Headless
docker-compose up pepper_headless

# Shell
docker-compose run --rm pepper_shell
```

> **Note**: `--init` is set in `docker-compose.yml` for all services to prevent zombie processes (Xvnc, openbox, websockify child processes).

---

## Testing

An end-to-end headless test script is included:

```bash
# Native
./test_e2e_headless.sh

# Inside Docker shell
docker-compose run --rm pepper_shell bash /catkin_ws/src/test_e2e_headless.sh
```

The test verifies:
- roscore starts
- Gazebo spawns Pepper model
- All 13 expected topics are active (`/pepper/joint_states`, `/pepper/scan`, `/pepper/odom`, cameras, controllers)
- Base movement (`cmd_vel`) produces odometry displacement

---

## Notes & Known Limitations

- **`people_velocity_tracker`** is disabled (`CATKIN_IGNORE`) — it requires `easy_markers` and `kalman_filter` packages not available in this repo.
- **`pepper_bridge`** is excluded from the Docker build — it requires Python 2 and the proprietary NAOqi SDK for real robot communication.
- **`ros-noetic-pepper-meshes`** has no arm64 binary on apt; the `pepper_meshes/` package in this repo provides the meshes directly.
- The VNC session has no password (LAN/local use only). Do not expose port 5901 to the internet.

---

## Credits

This project is based on and extends the following upstream work:

- [ros-naoqi/pepper_virtual](https://github.com/ros-naoqi/pepper_virtual) — original Pepper Gazebo simulation
- [ros-naoqi/pepper_robot](https://github.com/ros-naoqi/pepper_robot) — Pepper URDF description
- [awesomebytes/gazebo_model_velocity_plugin](https://github.com/awesomebytes/gazebo_model_velocity_plugin) — base velocity plugin
- [DLu/navigation_layers](https://github.com/DLu/navigation_layers) — social & range sensor costmap layers
- [wg-perception/people](https://github.com/wg-perception/people) — people detection suite

---

## License

- Project code: see [LICENSE](LICENSE)
- Pepper meshes (`pepper_meshes/`): [CC-BY-NC-ND 4.0](pepper_meshes/debian_license/) — Aldebaran Robotics / SoftBank
