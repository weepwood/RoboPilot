#!/usr/bin/env bash
set -euo pipefail

if [[ "$(. /etc/os-release && echo "${VERSION_CODENAME}")" != "noble" ]]; then
  echo "RoboPilot expects Ubuntu 24.04 (Noble)." >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y curl locales software-properties-common
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
sudo add-apt-repository universe -y

ROS_APT_SOURCE_VERSION="$(curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | awk -F\" '/tag_name/{print $4; exit}')"
if [[ -z "${ROS_APT_SOURCE_VERSION}" ]]; then
  echo "Unable to determine the latest ros-apt-source release." >&2
  exit 1
fi

ROS_APT_DEB="ros2-apt-source_${ROS_APT_SOURCE_VERSION}.noble_all.deb"
curl -fsSL -o "/tmp/${ROS_APT_DEB}" \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/${ROS_APT_DEB}"
sudo dpkg -i "/tmp/${ROS_APT_DEB}"
sudo apt-get update

sudo apt-get install -y \
  python3-colcon-common-extensions \
  python3-rosdep \
  ros-dev-tools \
  ros-jazzy-desktop \
  ros-jazzy-ros-gz \
  ros-jazzy-rosbridge-suite \
  ros-jazzy-teleop-twist-keyboard

if ! command -v node >/dev/null 2>&1 || [[ "$(node -p 'Number(process.versions.node.split(`.`)[0])' 2>/dev/null || echo 0)" -lt 20 ]]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  sudo rosdep init
fi
rosdep update

if ! grep -q '/opt/ros/jazzy/setup.bash' "${HOME}/.bashrc"; then
  printf '\nsource /opt/ros/jazzy/setup.bash\n' >> "${HOME}/.bashrc"
fi

echo
echo "Bootstrap complete. Start a new shell, then run ./scripts/build_ros.sh"
