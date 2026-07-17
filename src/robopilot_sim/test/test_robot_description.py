from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


def test_xacro_expands_to_expected_robot() -> None:
    package_root = Path(__file__).resolve().parents[1]
    xacro_file = package_root / "urdf" / "robopilot.urdf.xacro"

    completed = subprocess.run(
        ["xacro", str(xacro_file)],
        check=True,
        capture_output=True,
        text=True,
    )
    root = ET.fromstring(completed.stdout)

    links = {link.attrib["name"] for link in root.findall("link")}
    joints = {joint.attrib["name"] for joint in root.findall("joint")}

    assert root.tag == "robot"
    assert root.attrib["name"] == "robopilot"
    assert {"base_footprint", "base_link", "left_wheel_link", "right_wheel_link", "lidar_link"} <= links
    assert {"left_wheel_joint", "right_wheel_joint", "lidar_joint"} <= joints
