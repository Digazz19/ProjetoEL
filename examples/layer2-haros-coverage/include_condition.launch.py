from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    use_child = LaunchConfiguration("use_child")

    return LaunchDescription([
        DeclareLaunchArgument(
            "use_child",
            default_value="true",
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource("child.launch.py"),
            condition=IfCondition(use_child),
            launch_arguments={
                "foo": "bar",
            }.items(),
        )
    ])