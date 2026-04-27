from launch import LaunchDescription
from launch.actions import GroupAction, SetParameter
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        GroupAction([
            SetParameter(
                name='use_sim_time',
                value=True
            ),
            Node(
                package='demo_nodes_cpp',
                executable='talker'
            )
        ])
    ])