import launch
import launch_ros


def prepare_nodes(context, *args, **kwargs):
    n_lc = launch.substitutions.LaunchConfiguration("num_pairs")
    N = int(n_lc.perform(context))

    nodes = []

    if N < 1 or N > 5:
        message = launch.actions.LogInfo(
            msg="Invalid number of pairs"
        )
    else:
        for i in range(0, N):
            nodes.append(
                launch_ros.actions.Node(
                    package="demo_nodes_cpp",
                    executable="talker",
                    namespace=f"ns{i}",
                )
            )
            nodes.append(
                launch_ros.actions.Node(
                    package="demo_nodes_cpp",
                    executable="listener",
                    namespace=f"ns{i}",
                )
            )

    return nodes


def generate_launch_description():
    return launch.LaunchDescription([
        launch.actions.DeclareLaunchArgument(
            "num_pairs",
            default_value="1",
        ),
        launch.actions.OpaqueFunction(
            function=prepare_nodes,
        ),
    ])