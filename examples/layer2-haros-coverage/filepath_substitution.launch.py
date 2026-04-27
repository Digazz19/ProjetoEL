from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='demo_nodes_cpp',
            executable='talker',
            name='talker_node',
            parameters=[
                {
                    'config_file': PathJoinSubstitution([
                        FindPackageShare('demo_nodes_cpp'),
                        'config',
                        'params.yaml'
                    ])
                }
            ]
        )
    ])