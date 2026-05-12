from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetParameter
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")

    return LaunchDescription([
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
        ),

        SetParameter(
            name="use_sim_time",
            value=True,
            condition=IfCondition(use_sim_time),
        ),
    ])