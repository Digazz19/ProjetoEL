from launch import LaunchDescription
from launch.actions import GroupAction
from launch_ros.actions import Node, PushRosNamespace

def generate_launch_description():
    return LaunchDescription([
        GroupAction([
            PushRosNamespace('robot1'),
            GroupAction([
                PushRosNamespace('sensors'),
                Node(
                    package='demo_nodes_cpp',
                    executable='talker',
                    name='talker_node'
                )
            ])
        ])
    ])