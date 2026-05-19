from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="demo_pkg",
            executable="remap_talker",
            name="remap_talker",
            remappings=[("/chatter", "/robot/chatter")],
        ),
        Node(
            package="demo_pkg",
            executable="remap_listener",
            name="remap_listener",
        ),
    ])