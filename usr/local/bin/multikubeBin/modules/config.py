import os
import json
import logging

logger = logging.getLogger(__name__)

class MultiKubeConfig:
    """
    Configuration class for managing paths, constants, and default settings used in the MultiKube tool.
    """

    MULTIKUBE_DIR = os.path.expanduser("~/.multikube")
    CACHE_FILE = os.path.join(MULTIKUBE_DIR, "cluster_cache.json")
    KUBECONFIG_DIR = os.path.join(MULTIKUBE_DIR, "kubeconfigs")
    CONTEXTS_FILE = os.path.join(MULTIKUBE_DIR, "contexts.json")
    DEFAULT_CONTEXT_FILE = os.path.join(MULTIKUBE_DIR, "default_context.json")
    EKS_REGIONS_FILE = os.path.join(MULTIKUBE_DIR, "eks_regions.json")

    CACHE_TTL = int(os.getenv("MULTIKUBE_CACHE_TTL", "31536000"))  # Default: 1 year
    KUBECONFIG_TTL = int(os.getenv("MULTIKUBE_KUBECONFIG_TTL", "31536000"))  # Default: 1 year

    RETRY_COUNT = 3
    RETRY_BACKOFF = 2

    @staticmethod
    def initialize_directories():
        """
        Ensure that necessary directories exist for storing MultiKube configurations and cache files.
        """
        os.makedirs(MultiKubeConfig.MULTIKUBE_DIR, exist_ok=True)
        os.makedirs(MultiKubeConfig.KUBECONFIG_DIR, exist_ok=True)

    @staticmethod
    def load_or_prompt_regions():
        """
        Load regions from a JSON file or prompt the user to input them if the file does not exist or is empty.

        Returns:
            List[str]: A list of AWS regions.
        """
        if os.path.exists(MultiKubeConfig.EKS_REGIONS_FILE):
            with open(MultiKubeConfig.EKS_REGIONS_FILE, "r", encoding="utf-8") as file:
                regions = json.load(file).get('regions', [])
                if regions:
                    return regions

        logger.error("No AWS regions configuration found.")
        user_input = input("Please enter comma-separated AWS regions (e.g., us-east-1,eu-west-1): ")
        regions = [region.strip() for region in user_input.split(",")]
        with open(MultiKubeConfig.EKS_REGIONS_FILE, "w", encoding="utf-8") as file:
            json.dump({"regions": regions}, file)
        return regions
