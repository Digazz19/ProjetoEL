from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('a', default_value='true'),
        DeclareLaunchArgument('b', default_value='false'),

        Node(
            package='demo_nodes_cpp',
            executable='talker',
            condition=IfCondition(
                PythonExpression([
                    LaunchConfiguration('a'),
                    ' or ',
                    LaunchConfiguration('b')
                ])
            )
        )
    ])