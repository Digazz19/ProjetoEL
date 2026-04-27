from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'robot_name',
            default_value='robot1'
        ),
        GroupAction([
            PushRosNamespace(
                LaunchConfiguration('robot_name')
            ),
            Node(
                package='demo_nodes_cpp',
                executable='talker',
                name='talker_node'
            )
        ])
    ])