import os
import time
import subprocess
import boto3
from .config import MultiKubeConfig
from botocore.exceptions import CredentialRetrievalError
import logging

logger = logging.getLogger(__name__)

class KubeUtils:
    """
    Utility class for managing kubeconfig files and executing kubectl commands.
    """

    @staticmethod
    def update_kubeconfig(cluster_name, profile, region):
        """
        Update or retrieve the kubeconfig for a specific EKS cluster and AWS profile.

        Args:
            cluster_name (str): EKS cluster name.
            profile (str): AWS profile name.

        Returns:
            str: Path to the updated or existing kubeconfig file.

        Raises:
            subprocess.CalledProcessError: If the AWS CLI command fails.
        """
        session = boto3.Session(profile_name=profile)
        try:
            account_id = session.client("sts").get_caller_identity()["Account"]
        except CredentialRetrievalError as e:
            raise SystemExit("Failed to retrieve credentials. Please ensure you are logged in via SSO.") from e

        kubeconfig_path = os.path.join(MultiKubeConfig.KUBECONFIG_DIR, f"{account_id}-{cluster_name}.kubeconfig")

        if os.path.exists(kubeconfig_path) and (
            time.time() - os.path.getmtime(kubeconfig_path)
        ) < MultiKubeConfig.KUBECONFIG_TTL:
            return kubeconfig_path

        env = os.environ.copy()
        env["AWS_PROFILE"] = profile
        subprocess.run(
            [
                "aws",
                "eks",
                "update-kubeconfig",
                "--name",
                cluster_name,
                "--kubeconfig",
                kubeconfig_path,
                "--profile",
                profile,
                "--region",
                region
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return kubeconfig_path

    @staticmethod
    def execute_kubectl_command(cluster_name, kubeconfig_path, kubectl_args):
        """
        Execute a kubectl command on a specific cluster using the provided kubeconfig.

        Args:
            cluster_name (str): EKS cluster name.
            kubeconfig_path (str): Path to the kubeconfig file.
            kubectl_args (list): Arguments for the kubectl command.

        Returns:
            list: Parsed output from the kubectl command.

        Raises:
            subprocess.CalledProcessError: If kubectl encounters a fatal error.
            subprocess.TimeoutExpired: If the command times out.
        """
        command_type = kubectl_args[0] if kubectl_args else "get"
        timeout = 20

        for attempt in range(MultiKubeConfig.RETRY_COUNT):
            try:
                result = subprocess.run(
                    ["kubectl", "--kubeconfig", kubeconfig_path] + kubectl_args,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=True,
                )
                output_lines = result.stdout.splitlines()
                if command_type == "logs":
                    return [
                        [f"[{cluster_name}][{time.strftime('%Y-%m-%d %H:%M:%S')}] {line}"]
                        for line in output_lines
                    ]
                elif output_lines:
                    data = [
                        [cluster_name] + line.split(None, len(output_lines[0].split()) - 1)
                        for line in output_lines[1:]
                    ]
                    return data
                return []

            except subprocess.CalledProcessError as e:
                if "not found" in e.stderr:
                    logger.info("Pod not found in cluster %s, skipping.", cluster_name)
                    return []
                if attempt < MultiKubeConfig.RETRY_COUNT - 1:
                    time.sleep(MultiKubeConfig.RETRY_BACKOFF * (2**attempt))
                    continue
                logger.error("Error running kubectl on %s:\n %s", cluster_name, e.stderr.strip())
                return []
            except subprocess.TimeoutExpired:
                logger.error("Timeout expired for cluster %s, skipping.", cluster_name)
                return []
