from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="demo_pkg",
            executable="talker_a",
            name="talker_a",
        ),
        Node(
            package="demo_pkg",
            executable="talker_b",
            name="talker_b",
        ),
        Node(
            package="demo_pkg",
            executable="shared_listener",
            name="shared_listener",
        ),
        Node(
            package="demo_pkg",
            executable="qos_publisher",
            name="qos_publisher",
        ),
        Node(
            package="demo_pkg",
            executable="qos_subscriber",
            name="qos_subscriber",
        ),
        Node(
            package="demo_pkg",
            executable="isolated",
            name="isolated",
        ),
        Node(
            package="demo_pkg",
            executable="lonely_publisher",
            name="lonely_publisher",
        ),
        Node(
            package="demo_pkg",
            executable="lonely_subscriber",
            name="lonely_subscriber",
        ),
    ])