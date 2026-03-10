from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")
    remaps = [("/cmd_vel", "/robot/cmd_vel")]

    ld = LaunchDescription()

    ld.add_action(DeclareLaunchArgument("use_sim_time", default_value="false"))
    ld.add_action(SetEnvironmentVariable("RCUTILS_LOGGING_BUFFERED_STREAM", "1"))

    ld.add_action(
        Node(
            package="demo_nodes_cpp",
            executable="talker",
            name="talker_node",
            namespace="/demo",
            remappings=remaps,
            parameters=[{"use_sim_time": use_sim_time}]
        )
    )

    ld.add_action(
        ExecuteProcess(
            cmd=["echo", "hello"],
            cwd="/tmp",
            additional_env={"A": "1"}
        )
    )

    return ld