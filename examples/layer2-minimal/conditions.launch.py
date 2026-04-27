from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_talker',
            default_value='true'
        ),
        Node(
            package='demo_nodes_cpp',
            executable='talker',
            name='talker_node',
            condition=IfCondition(LaunchConfiguration('use_talker'))
        )
    ])