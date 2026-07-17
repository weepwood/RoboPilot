#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/jazzy/setup.bash
cd "${ROOT_DIR}"

rosdep install --from-paths src --ignore-src --rosdistro jazzy -r -y
colcon build --symlink-install --event-handlers console_direct+

echo
echo "Build complete. Source install/setup.bash before running ROS commands."
