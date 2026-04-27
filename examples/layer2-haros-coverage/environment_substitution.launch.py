from launch import LaunchDescription
from launch.substitutions import EnvironmentVariable
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='demo_nodes_cpp',
            executable='talker',
            name=EnvironmentVariable(
                'ROBOT_NAME',
                default_value='robot1'
            )
        )
    ])