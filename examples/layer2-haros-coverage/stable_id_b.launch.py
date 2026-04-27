from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            name="talker_node",
            executable="talker",
            package="demo_nodes_cpp",
        )
    ])