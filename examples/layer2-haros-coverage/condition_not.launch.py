from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('a', default_value='false'),

        Node(
            package='demo_nodes_cpp',
            executable='talker',
            condition=UnlessCondition(
                LaunchConfiguration('a')
            )
        )
    ])