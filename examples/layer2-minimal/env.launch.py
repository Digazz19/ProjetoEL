from launch import LaunchDescription
from launch.actions import SetEnvironmentVariable
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        SetEnvironmentVariable(
            name='ROBOT_ENV',
            value='simulation'
        ),
        Node(
            package='demo_nodes_cpp',
            executable='talker',
            name='talker_node'
        )
    ])