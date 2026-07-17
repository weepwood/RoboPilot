# Run RoboPilot on Windows 11 with WSLg

RoboPilot's supported Windows workflow is Ubuntu 24.04 inside WSL2. Windows 11 includes WSLg, which can display Gazebo and RViz Linux windows on the Windows desktop.

## 1. Install Ubuntu 24.04

Open PowerShell as Administrator:

```powershell
wsl --install -d Ubuntu-24.04
```

Restart Windows if requested, open Ubuntu, and create the Linux username and password.

Verify that the distribution uses WSL2:

```powershell
wsl --list --verbose
```

Set version 2 if needed:

```powershell
wsl --set-version Ubuntu-24.04 2
```

## 2. Update WSL

```powershell
wsl --update
wsl --shutdown
```

Start Ubuntu again and confirm GUI forwarding variables exist:

```bash
echo "$WAYLAND_DISPLAY"
echo "$DISPLAY"
```

At least one should be populated under WSLg.

## 3. Keep the workspace inside Linux

For much better build and file-watching performance, clone into the Linux filesystem rather than `/mnt/c`:

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/weepwood/RoboPilot.git
cd RoboPilot
```

## 4. Install and run

```bash
chmod +x scripts/*.sh
./scripts/bootstrap_ubuntu.sh
exec bash
./scripts/build_ros.sh
./scripts/run_sim.sh
```

In a second Ubuntu terminal:

```bash
cd ~/projects/RoboPilot
./scripts/run_dashboard.sh
```

Open `http://localhost:5173` in the Windows browser. WSL2 normally forwards localhost automatically. The dashboard connects back to `ws://localhost:9090`.

## Troubleshooting

### Gazebo window does not open

Update WSL, shut it down, and reopen Ubuntu:

```powershell
wsl --update
wsl --shutdown
```

Ensure the current Windows graphics driver supports WSLg acceleration.

### Gazebo renders black or crashes

Try software rendering as a diagnostic step:

```bash
LIBGL_ALWAYS_SOFTWARE=1 ./scripts/run_sim.sh
```

This is slower but helps distinguish a graphics-driver issue from a simulation issue.

### Dashboard connects but the robot does not move

Check the ROS graph:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 topic list
ros2 topic echo /cmd_vel
```

The dashboard should produce `geometry_msgs/msg/Twist` messages while a direction control is held.

### Windows browser cannot reach rosbridge

Find the WSL address:

```bash
hostname -I
```

Then set the dashboard address to `ws://<WSL-IP>:9090`. This is usually unnecessary, but can help with custom firewall or networking settings.
