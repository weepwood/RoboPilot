from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    package_share = FindPackageShare("robopilot_sim")
    world_name = LaunchConfiguration("world")
    use_rviz = LaunchConfiguration("use_rviz")
    use_rosbridge = LaunchConfiguration("use_rosbridge")
    headless = LaunchConfiguration("headless")

    world_path = PathJoinSubstitution([package_share, "worlds", world_name])
    xacro_path = PathJoinSubstitution([package_share, "urdf", "robopilot.urdf.xacro"])
    bridge_config = PathJoinSubstitution([package_share, "config", "bridge.yaml"])
    rviz_config = PathJoinSubstitution([package_share, "rviz", "robopilot.rviz"])

    robot_description = Command([FindExecutable(name="xacro"), " ", xacro_path])

    gazebo_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"])
        ),
        launch_arguments={"gz_args": ["-r -v 3 ", world_path]}.items(),
        condition=UnlessCondition(headless),
    )

    gazebo_headless = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"])
        ),
        launch_arguments={"gz_args": ["-s -r -v 3 ", world_path]}.items(),
        condition=IfCondition(headless),
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_description, "use_sim_time": True}],
    )

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-world",
            "training_world",
            "-topic",
            "robot_description",
            "-name",
            "robopilot",
            "-x",
            "0.0",
            "-y",
            "0.0",
            "-z",
            "0.14",
        ],
    )

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="ros_gz_bridge",
        output="screen",
        parameters=[{"config_file": bridge_config}],
    )

    rosbridge = Node(
        package="rosbridge_server",
        executable="rosbridge_websocket",
        name="rosbridge_websocket",
        output="screen",
        parameters=[
            {
                "address": "0.0.0.0",
                "port": 9090,
                "fragment_timeout": 600,
                "delay_between_messages": 0.0,
            }
        ],
        condition=IfCondition(use_rosbridge),
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config],
        parameters=[{"use_sim_time": True}],
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "world",
                default_value="training_world.sdf",
                description="World file located in robopilot_sim/worlds.",
            ),
            DeclareLaunchArgument("use_rviz", default_value="true"),
            DeclareLaunchArgument("use_rosbridge", default_value="true"),
            DeclareLaunchArgument("headless", default_value="false"),
            gazebo_gui,
            gazebo_headless,
            robot_state_publisher,
            spawn_robot,
            bridge,
            rosbridge,
            rviz,
        ]
    )
