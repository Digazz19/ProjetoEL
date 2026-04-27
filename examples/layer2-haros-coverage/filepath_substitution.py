from launch_ros.actions import Node
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

Node(
 package="demo_nodes_cpp",
 executable="talker",
 parameters=[
   PathJoinSubstitution([
      FindPackageShare("demo_nodes_cpp"),
      "config",
      "params.yaml"
   ])
 ]
)