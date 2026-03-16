#!/bin/bash
set -e

source /opt/ros/noetic/setup.bash
source /catkin_ws/devel/setup.bash
export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:/catkin_ws/src/pepper_virtual/pepper_gazebo_plugin/models

if [ "$1" = "gui" ]; then
    # ── Browser-accessible Gazebo GUI via Xvnc + noVNC ───────────────────────
    # Open http://localhost:6080/vnc.html in your browser.
    VNC_DISPLAY=:1
    VNC_PORT=5901
    NOVNC_PORT=6080

    echo "[INFO] Starting Xvnc on display ${VNC_DISPLAY} (no password)"
    # Note: no -localhost flag → Xvnc accepts connections from any address.
    # websockify runs inside the same container so it always connects locally.
    Xvnc ${VNC_DISPLAY} \
        -geometry 1600x900 \
        -depth 24 \
        -SecurityTypes None \
        -rfbport ${VNC_PORT} &
    export DISPLAY=${VNC_DISPLAY}
    sleep 3

    echo "[INFO] Starting Openbox window manager"
    openbox &
    sleep 1

    echo "[INFO] Starting noVNC websocket proxy on port ${NOVNC_PORT}"
    websockify --web /usr/share/novnc ${NOVNC_PORT} localhost:${VNC_PORT} &
    sleep 1

    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  Gazebo GUI ready — open in your browser:            ║"
    echo "║  http://localhost:${NOVNC_PORT}/vnc.html                  ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo ""

    exec roslaunch pepper_gazebo_plugin pepper_gazebo_plugin_Y20_CPU_no_arms.launch gui:=true

elif [ "$1" = "headless" ]; then
    Xvfb :99 -screen 0 1280x1024x24 &
    export DISPLAY=:99
    exec roslaunch pepper_gazebo_plugin pepper_gazebo_plugin_Y20_CPU_no_arms.launch gui:=false headless:=true

else
    exec "$@"
fi
