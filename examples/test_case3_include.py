from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    included_file = "other_launch.py"

    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(included_file)
        ),
        Node(
            package="demo_nodes_cpp",
            executable="talker",
            name="main_node"
        )
    ])