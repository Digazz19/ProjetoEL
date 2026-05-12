import launch
import launch_ros

def prepare_nodes(context, ld):
    n_lc = launch.substitutions.LaunchConfiguration("num_pairs")
    N = int(n_lc.perform(context))

    if N < 1 or N > 5:
        message = launch.actions.LogInfo(
            msg="Invalid number of pairs"
        )
        ld.add_action(message)
    else:
        for i in range(0, N):
            ld.add_action(
                launch_ros.actions.Node(
                    package="demo_nodes_cpp",
                    executable="talker",
                    namespace=f"ns{i}",
                )
            )
            ld.add_action(
                launch_ros.actions.Node(
                    package="demo_nodes_cpp",
                    executable="listener",
                    namespace=f"ns{i}",
                )
            )


def generate_launch_description():
    ld = launch.LaunchDescription()

    ld.add_action(
        launch.actions.DeclareLaunchArgument(
            "num_pairs",
            default_value="1",
        )
    )

    ld.add_action(
        launch.actions.OpaqueFunction(
            function=prepare_nodes,
            args=[ld],
        )
    )

    return ld