# Pepper Robot Gazebo Simulation - Docker Image
# Using ros-base (minimal) instead of desktop-full to reduce attack surface.
# Security patches are applied immediately after base image pull.
FROM ros:noetic-ros-base-focal

LABEL maintainer="pepper_with_gazebo"
LABEL description="Pepper humanoid robot simulation with Gazebo, navigation, people detection, and face detection"

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=noetic

# ─── Apply all OS security patches first ──────────────────────────────────────
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# ─── System & ROS dependencies ────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build tools
    build-essential \
    cmake \
    git \
    wget \
    python3-pip \
    python3-catkin-tools \
    # Gazebo 11 (compatible with Noetic)
    ros-noetic-gazebo-ros \
    ros-noetic-gazebo-ros-control \
    ros-noetic-gazebo-plugins \
    # ROS control
    ros-noetic-ros-control \
    ros-noetic-ros-controllers \
    ros-noetic-controller-manager \
    # Navigation stack
    ros-noetic-navigation \
    ros-noetic-move-base \
    ros-noetic-costmap-2d \
    ros-noetic-map-server \
    ros-noetic-amcl \
    # Sensor / TF utilities
    ros-noetic-tf2-sensor-msgs \
    ros-noetic-tf2-geometry-msgs \
    ros-noetic-laser-geometry \
    ros-noetic-depthimage-to-laserscan \
    ros-noetic-pcl-ros \
    ros-noetic-pointcloud-to-laserscan \
    # Robot description & state
    ros-noetic-robot-state-publisher \
    ros-noetic-joint-state-publisher \
    ros-noetic-xacro \
    ros-noetic-urdf \
    # People detection / tracking
    # ros-noetic-people-msgs is built from source (in the workspace)
    # BFL binary for arm64 is liborocos-bfl-dev (not ros-noetic-bfl)
    liborocos-bfl-dev \
    # Vision / face detection
    ros-noetic-cv-bridge \
    ros-noetic-image-transport \
    python3-opencv \
    # Dynamic reconfigure
    ros-noetic-ddynamic-reconfigure \
    # Protobuf (Gazebo plugin)
    libprotobuf-dev \
    protobuf-compiler \
    # Virtual display + VNC for browser-based GUI (no XQuartz needed on macOS)
    xvfb \
    tigervnc-standalone-server \
    tigervnc-common \
    novnc \
    websockify \
    openbox \
    x11-utils \
    mesa-utils \
    # tini: lightweight init for Docker — reaps zombie child processes
    tini \
    && rm -rf /var/lib/apt/lists/*

# ─── Pepper meshes ─────────────────────────────────────────────────────────────
# ros-noetic-pepper-meshes has no arm64 binary; the project ships its own
# pepper_meshes package in the workspace — no extra install needed.

# numpy and opencv are already pulled in via python3-numpy / python3-opencv
# through the ros-noetic-cv-bridge apt dependency above — no pip step needed.

# ─── Non-root user for security ───────────────────────────────────────────────
ARG USERNAME=rosuser
ARG USER_UID=1000
ARG USER_GID=1000
RUN groupadd --gid $USER_GID $USERNAME && \
    useradd --uid $USER_UID --gid $USER_GID -m $USERNAME && \
    echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# ─── Catkin workspace ─────────────────────────────────────────────────────────
RUN mkdir -p /catkin_ws/src && chown -R $USERNAME:$USERNAME /catkin_ws

# Copy the whole repo directly into src/ — catkin scans recursively for
# package.xml files, so all nested packages are found automatically.
# pepper_bridge is excluded: requires Python 2 + NAOqi SDK (real robot only).
COPY --chown=$USERNAME:$USERNAME gazebo_model_velocity_plugin  /catkin_ws/src/gazebo_model_velocity_plugin
COPY --chown=$USERNAME:$USERNAME navigation_layers             /catkin_ws/src/navigation_layers
COPY --chown=$USERNAME:$USERNAME people                        /catkin_ws/src/people
COPY --chown=$USERNAME:$USERNAME pepper_face_detector          /catkin_ws/src/pepper_face_detector
COPY --chown=$USERNAME:$USERNAME pepper_laser_bridge           /catkin_ws/src/pepper_laser_bridge
COPY --chown=$USERNAME:$USERNAME pepper_meshes                 /catkin_ws/src/pepper_meshes
COPY --chown=$USERNAME:$USERNAME pepper_robot                  /catkin_ws/src/pepper_robot
COPY --chown=$USERNAME:$USERNAME pepper_virtual                /catkin_ws/src/pepper_virtual
COPY --chown=$USERNAME:$USERNAME velocity_bridge               /catkin_ws/src/velocity_bridge
COPY --chown=$USERNAME:$USERNAME test_e2e_headless.sh          /catkin_ws/src/test_e2e_headless.sh

# people_velocity_tracker depends on easy_markers + kalman_filter (non-standard,
# not in this repo). Mark it to be skipped by catkin.
RUN touch /catkin_ws/src/people/people_velocity_tracker/CATKIN_IGNORE

# Make Python/shell scripts executable
RUN find /catkin_ws/src -name "*.py" -exec chmod +x {} \; && \
    find /catkin_ws/src -name "*.sh" -exec chmod +x {} \;

# ─── Build workspace ──────────────────────────────────────────────────────────
USER $USERNAME
WORKDIR /catkin_ws
RUN /bin/bash -c \
    "source /opt/ros/noetic/setup.bash && \
     catkin_make -DCMAKE_BUILD_TYPE=Release -DCATKIN_ENABLE_TESTING=OFF"

# ─── Shell environment ─────────────────────────────────────────────────────────
# GAZEBO_MODEL_PATH as ENV so it is available to all processes, not just login shells
ENV GAZEBO_MODEL_PATH=/catkin_ws/src/pepper_virtual/pepper_gazebo_plugin/models

RUN echo 'source /opt/ros/noetic/setup.bash' >> /home/$USERNAME/.bashrc && \
    echo 'source /catkin_ws/devel/setup.bash' >> /home/$USERNAME/.bashrc

# ─── VNC password (empty — LAN-only use) ─────────────────────────────────────
RUN mkdir -p /home/$USERNAME/.vnc && \
    echo "" | vncpasswd -f > /home/$USERNAME/.vnc/passwd && \
    chmod 600 /home/$USERNAME/.vnc/passwd && \
    chown -R $USERNAME:$USERNAME /home/$USERNAME/.vnc

# noVNC web port (browser GUI)
EXPOSE 6080
# VNC port (Xvnc runs on display :1 → port 5901)
EXPOSE 5901

# ─── Entrypoint ───────────────────────────────────────────────────────────────
COPY --chown=$USERNAME:$USERNAME docker-entrypoint.sh /home/$USERNAME/docker-entrypoint.sh
RUN chmod +x /home/$USERNAME/docker-entrypoint.sh

WORKDIR /catkin_ws
ENTRYPOINT ["/home/rosuser/docker-entrypoint.sh"]
CMD ["gui"]
