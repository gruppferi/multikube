#!/usr/local/bin/multikubeBin/venv/bin/python
import argparse
import re
import os
import sys
import logging
from tabulate2 import tabulate
from concurrent.futures import ThreadPoolExecutor, as_completed
from modules.aws_utils import AWSUtils
from modules.context_utils import ContextManager
from modules.kubectl_utils import KubeUtils

script_dir = os.path.dirname(os.path.realpath(__file__))
venv_dir = os.path.join(script_dir, "venv")
site_packages = os.path.join(
    venv_dir, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
def parse_args():
    """
    Parse command-line arguments for the MultiKube tool. This setup distinguishes between
    MultiKube-specific options and kubectl arguments. If the first argument is not a recognized
    option for MultiKube, it assumes that all arguments are meant for kubectl.
    """
    description = """
    MultiKube is a multi-cluster Kubernetes management tool designed to simplify the management of multiple
    Kubernetes clusters. It provides utilities for initializing and refreshing cluster caches, managing
    cluster contexts, and executing kubectl commands across multiple clusters efficiently.
    """
    epilog = """
    Examples:
        python multikube --init
        python multikube --store-clusters-contexts pattern
        python multikube --set-clusters-contexts mycontext
        python multikube get pods --all
    """

    # Set of recognized MultiKube-specific command-line options
    multikube_options = {'--init', '--store-clusters-contexts', '--set-clusters-contexts', '--renew-cache', '--help'}

    # Check if the first command-line argument is a recognized MultiKube option
    if len(sys.argv) > 1 and not any(opt == sys.argv[1] for opt in multikube_options):
        # If not, treat all arguments as kubectl arguments
        return argparse.Namespace(kubectl_args=sys.argv[1:], init=False, store_clusters_contexts=None,
                                  set_clusters_contexts=None, renew_cache=False)

    parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--init", action="store_true", help="Initialize or refresh the cluster cache.")
    parser.add_argument("--store-clusters-contexts", metavar="PATTERN",
                        help="Store a cluster context with a given pattern for future reference.")
    parser.add_argument("--set-clusters-contexts", metavar="CONTEXT",
                        help="Set the default cluster context to use for kubectl commands.")
    parser.add_argument("--renew-cache", action="store_true",
                        help="Force a renewal of the cluster cache regardless of its current state.")
    parser.add_argument("kubectl_args", nargs='*',
                        help="Pass-through arguments for the kubectl command.")

    args = parser.parse_args()
    return args

def handle_cache_initialization(args):
    """
    Initializes or refreshes the cluster cache if the '--init' option is specified in the command-line arguments.

    Args:
        args (argparse.Namespace): The parsed command-line arguments.

    Effects:
        Exits the program after initializing the cache or logs an error if no profiles are found.
    """
    if args.init:
        profiles = AWSUtils.load_profiles_from_aws_config()
        if not profiles:
            logger.error("No AWS profiles found in ~/.aws/config.")
            sys.exit(1)
        AWSUtils.generate_cache(profiles, True)
        logger.info("Cluster cache initialized.")
        sys.exit(0)

def handle_context_management(args):
    """
    Manages cluster contexts based on command-line arguments for storing and setting contexts.

    Args:
        args (argparse.Namespace): The parsed command-line arguments.

    Effects:
        Exits the program after managing the contexts or prompts for context if no kubectl arguments are given.
    """
    if args.store_clusters_contexts:
        ContextManager.store_cluster_context(args.store_clusters_contexts)
        sys.exit(0)

    if args.set_clusters_contexts:
        ContextManager.set_default_context(args.set_clusters_contexts)
        sys.exit(0)

    if not args.kubectl_args:
        selected_pattern = ContextManager.prompt_user_for_context()
        if selected_pattern:
            for context_name, pattern in ContextManager.load_contexts().items():
                if pattern == selected_pattern:
                    ContextManager.set_default_context(context_name)
                    sys.exit(0)
        logger.error("No contexts available. Please add one using --store-clusters-contexts.")
        sys.exit(1)

def prepare_clusters_for_command_execution(args):
    """
    Prepares clusters for kubectl command execution by matching them against the default context pattern.

    Args:
        args (argparse.Namespace): The parsed command-line arguments.

    Returns:
        list of tuples: A list containing tuples of (cluster_name, profile, region) for each matched cluster.

    Effects:
        Exits the program if no matching clusters are found or if there is no default cluster pattern.
    """
    cluster_pattern = ContextManager.get_default_context_pattern()
    if not cluster_pattern:
        logger.error("No cluster pattern provided or available in the default context.")
        sys.exit(1)

    profiles = AWSUtils.load_profiles_from_aws_config()
    if not profiles:
        logger.error("No AWS profiles found in ~/.aws/config.")
        sys.exit(1)

    if args.renew_cache or not AWSUtils.is_cache_fresh():
        AWSUtils.generate_cache(profiles)

    cache_data = AWSUtils.load_cache()
    clusters_to_process = []
    pattern = re.compile(cluster_pattern)
    for profile, clusters in cache_data.items():
        for cluster in clusters:
            cluster_name = cluster.split("/")[2]
            region = cluster.split("/")[1]
            if pattern.match(cluster_name):
                clusters_to_process.append((cluster_name, profile, region))

    if not clusters_to_process:
        logger.error("No matching clusters found for the pattern.")
        sys.exit(1)
    return clusters_to_process

def execute_kubectl_commands(clusters_to_process, args):
    """
    Executes kubectl commands across multiple clusters in parallel.

    Args:
        clusters_to_process (list of tuples): Clusters prepared for command execution.
        args (argparse.Namespace): The parsed command-line arguments.

    Returns:
        list: A list of outputs from each kubectl command execution.

    Effects:
        Logs an error if any command processing fails.
    """
    all_data = []
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(
                KubeUtils.execute_kubectl_command,
                cluster_name,
                KubeUtils.update_kubeconfig(cluster_name, profile, region),
                args.kubectl_args
            ): (cluster_name, profile, region)
            for cluster_name, profile, region in clusters_to_process
        }
        for future in as_completed(futures):
            try:
                output = future.result()
                if output:
                    all_data.extend(output)
            except Exception as exc:
                logger.error("Error processing a cluster: %s", exc)
    return all_data

def display_results(args, all_data):
    """
    Displays results from kubectl commands based on the command type.

    Args:
        args (argparse.Namespace): The parsed command-line arguments.
        all_data (list): The collected data from all executed kubectl commands.

    Effects:
        Prints results to stdout or logs a message if no data is returned.
    """
    if args.kubectl_args and args.kubectl_args[0] == "logs":
        for entry in all_data:
            print(entry[0])
    elif all_data:
        headers = ["CLUSTER", "NAME", "READY", "STATUS", "RESTARTS", "AGE"]
        print(tabulate(all_data, headers=headers, tablefmt="plain"))
    else:
        logger.info("No data returned from the kubectl command.")

def main():
    args = parse_args()

    handle_cache_initialization(args)
    handle_context_management(args)
    clusters_to_process = prepare_clusters_for_command_execution(args)
    all_data = execute_kubectl_commands(clusters_to_process, args)
    display_results(args, all_data)

if __name__ == "__main__":
    main()
