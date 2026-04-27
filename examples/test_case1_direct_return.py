from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("robot_name", default_value="kobuki"),
        Node(
            package="demo_nodes_cpp",
            executable="talker",
            name="direct_node"
        )
    ])