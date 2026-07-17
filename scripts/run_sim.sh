#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/jazzy/setup.bash

if [[ ! -f "${ROOT_DIR}/install/setup.bash" ]]; then
  echo "Workspace is not built. Run ./scripts/build_ros.sh first." >&2
  exit 1
fi

source "${ROOT_DIR}/install/setup.bash"
exec ros2 launch robopilot_sim simulation.launch.py "$@"
