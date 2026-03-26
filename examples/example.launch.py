from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable, UnsetEnvironmentVariable, ExecuteProcess, IncludeLaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([

        # Argumentos e variáveis globais
        DeclareLaunchArgument(name="use_sim", default_value="false"),
        SetEnvironmentVariable(name="RMW_IMPLEMENTATION", value="rmw_fastrtps_cpp"),

        # Node SEM namespace: nome e remaps ficam em '/'
        Node(
            package="nav2",
            executable="controller_server",
            name="controller",
        ),

        # talker: remap relativo + remap absoluto
        # /chatter_global é absoluto -> não deve ser prefixado com o namespace
        Node(
            package="demo_nodes_cpp",
            executable="talker",
            name="talker_node",
            namespace="robot1",
            remappings=[("chatter", "robot_chat"), ("/chatter_global", "/global/chat")],
            parameters=[{"rate": 10}],
        ),

        # listener: mesmo namespace, remap para o mesmo tópico que o talker
        Node(
            package="demo_nodes_cpp",
            executable="listener",
            name="listener_node",
            namespace="robot1",
            remappings=[("chatter", "robot_chat")],
        ),

        # Node com namespace diferente
        Node(
            package="sensor_pkg",
            executable="lidar_driver",
            name="lidar",
            namespace="sensors",
            remappings=[("scan", "base_scan")],
        ),

        # Include com arg passado
        IncludeLaunchDescription("sensors.launch.xml"),

        # Executable e unset_env
        ExecuteProcess(cmd=["ls", "-las"], cwd="/home"),
        UnsetEnvironmentVariable(name="OLD_ENV"),

    ])