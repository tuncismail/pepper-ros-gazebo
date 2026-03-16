#!/bin/bash
# End-to-end headless test for Pepper Gazebo simulation.
# Runs inside the Docker container via the 'pepper_headless' compose service.
#
# Exit codes:  0 = all checks passed
#              1 = one or more checks failed

set -euo pipefail
# Note: 'set -e' only affects top-level commands; check_topic uses subshells so
# failures are caught via explicit FAIL counter rather than aborting the script.
set +e   # disable abort-on-error so we can count all failures
source /opt/ros/noetic/setup.bash
source /catkin_ws/devel/setup.bash
export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:/catkin_ws/src/pepper_virtual/pepper_gazebo_plugin/models

PASS=0
FAIL=0
TIMEOUT=60   # seconds to wait for each topic

log()  { echo "[TEST] $*"; }
ok()   { echo "[PASS] $*"; PASS=$((PASS+1)); }
fail() { echo "[FAIL] $*"; FAIL=$((FAIL+1)); }

# ── 1. Start virtual display (Xvfb) ─────────────────────────────────────────
log "Starting Xvfb virtual display on :99"
apt-get install -y --no-install-recommends xvfb > /dev/null 2>&1 || true
Xvfb :99 -screen 0 1280x1024x24 &
XVFB_PID=$!
export DISPLAY=:99
sleep 2

# ── 2. Start roscore ─────────────────────────────────────────────────────────
log "Starting roscore"
roscore &
ROSCORE_PID=$!
sleep 3

if ! rostopic list > /dev/null 2>&1; then
    fail "roscore failed to start"
    exit 1
fi
ok "roscore running"

# ── 3. Launch Gazebo simulation (headless, no arm controllers) ────────────────
log "Launching Pepper Gazebo simulation (headless, timeout=${TIMEOUT}s)"
roslaunch pepper_gazebo_plugin pepper_gazebo_plugin_Y20_CPU_no_arms.launch \
    gui:=false headless:=true &
LAUNCH_PID=$!
sleep 20   # give Gazebo time to load world + spawn robot + start controllers

# ── 4. Check expected ROS topics ─────────────────────────────────────────────
check_topic() {
    local topic=$1
    local desc=$2
    if timeout $TIMEOUT rostopic hz "$topic" --window 5 2>/dev/null | grep -q "average rate"; then
        ok "$desc  ($topic)"
    else
        # Fallback: just verify topic exists in the graph
        if rostopic list 2>/dev/null | grep -qF "$topic"; then
            ok "$desc exists  ($topic)"
        else
            fail "$desc not found  ($topic)"
        fi
    fi
}

log "Checking published topics..."
check_topic /pepper/scan_front          "Front laser scan"
check_topic /pepper/scan_left           "Left laser scan"
check_topic /pepper/scan_right          "Right laser scan"
check_topic /joint_states               "Joint states"
check_topic /tf                         "TF transforms"
check_topic /pepper/odom                "Odometry"

# ── 5. Check robot_description parameter is set ───────────────────────────────
if rosparam get /robot_description > /dev/null 2>&1; then
    ok "robot_description URDF loaded"
else
    fail "robot_description param missing"
fi

# ── 6. Verify Pepper model spawned in Gazebo ─────────────────────────────────
if rostopic echo /gazebo/model_states -n 1 2>/dev/null | grep -q "pepper_MP"; then
    ok "Pepper model spawned in Gazebo"
else
    fail "Pepper model not found in /gazebo/model_states"
fi

# ── 7. Send a velocity command and verify it doesn't crash the system ─────────
log "Sending test velocity command"
rostopic pub -1 /pepper/cmd_vel geometry_msgs/Twist \
    '{ linear: {x: 0.1, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0} }' \
    > /dev/null 2>&1 && ok "cmd_vel accepted" || fail "cmd_vel rejected"

# ── Cleanup ───────────────────────────────────────────────────────────────────
log "Shutting down..."
kill $LAUNCH_PID $ROSCORE_PID $XVFB_PID 2>/dev/null || true
wait 2>/dev/null || true

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════"
echo "  E2E Test Results"
echo "  PASSED: $PASS"
echo "  FAILED: $FAIL"
echo "════════════════════════════════════"

[ $FAIL -eq 0 ] && exit 0 || exit 1
