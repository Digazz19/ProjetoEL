from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_group = LaunchConfiguration("use_group")

    return LaunchDescription([
        DeclareLaunchArgument(
            "use_group",
            default_value="true",
        ),

        GroupAction(
            condition=IfCondition(use_group),
            actions=[
                Node(
                    package="demo_nodes_cpp",
                    executable="talker",
                    name="talker_in_group",
                )
            ],
        )
    ])