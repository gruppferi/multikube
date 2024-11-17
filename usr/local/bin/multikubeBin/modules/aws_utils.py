import configparser
import json
import sys
import os
import time
import subprocess
import boto3
from botocore.exceptions import SSOTokenLoadError
from .config import MultiKubeConfig
import logging

logger = logging.getLogger(__name__)

class AWSUtils:
    """
    Utility class for managing AWS-related operations such as loading profiles,
    ensuring SSO login, generating caches, and validating cache freshness.
    """

    @staticmethod
    def load_profiles_from_aws_config():
        """
        Load AWS profiles from the user's AWS configuration file.

        Returns:
            list: A list of profile names found in the AWS configuration file.
        """
        profiles = []
        aws_config_path = os.path.expanduser("~/.aws/config")
        if os.path.exists(aws_config_path):
            config = configparser.ConfigParser()
            config.read(aws_config_path)
            profiles = [
                section.split(" ", 1)[1] for section in config.sections()
                if section.startswith("profile ")
            ]
        return profiles

    @staticmethod
    def ensure_sso_login(profile, init=False):
        """
        Ensure that the given AWS profile has a valid SSO token. If not, prompt the user to log in.

        Args:
            profile (str): The AWS profile name.

        Raises:
            SystemExit: If SSO login fails or an unexpected error occurs.
        """
        try:
            if init:
                subprocess.run(["aws", "sso", "login", "--profile", profile], check=True)
                logging.info("SSO login successful.")
            session = boto3.Session(profile_name=profile)
            session.client("sts").get_caller_identity()
        except SSOTokenLoadError:
            logging.info("SSO token for profile %s is missing or expired.", profile)
            logging.info("Attempting to log in to AWS SSO...")
            try:
                subprocess.run(["aws", "sso", "login", "--profile", profile], check=True)
                logging.info("SSO login successful.")
            except subprocess.CalledProcessError:
                logger.error(
                    "Failed to log in to AWS SSO for profile '%s'. Ensure your AWS SSO config is correct.", profile
                )
                sys.exit(1)
        except Exception as e:
            logger.error("Unexpected error while checking SSO login for profile '%s': %s", profile, e)
            sys.exit(1)

    @staticmethod
    def generate_cache(profiles, init=False):
        regions = MultiKubeConfig.load_or_prompt_regions()
        cache_data = {}

        for profile in profiles:
            profile_cache = []
            for region in regions:
                try:
                    AWSUtils.ensure_sso_login(profile, init)
                    init = False
                    session = boto3.Session(profile_name=profile, region_name=region)
                    account_id = session.client("sts").get_caller_identity()["Account"]
                    eks_client = session.client("eks")
                    clusters = eks_client.list_clusters()["clusters"]

                    profile_cache.extend([f"{account_id}/{region}/{cluster}" for cluster in clusters])
                    logging.info("Successfully listed clusters for profile '%s' in region '%s' and account '%s'.", profile, region, account_id)
                except boto3.exceptions.Boto3Error as e:
                    logging.error("Failed to list clusters for profile '%s' in region '%s': %s", profile, region, e)
                except Exception as e:
                    logging.error("Unexpected error with profile '%s' in region '%s': %s", profile, region, e)

            cache_data[profile] = profile_cache

        with open(MultiKubeConfig.CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)
        logging.info("Cache generated successfully.")

    @staticmethod
    def is_cache_fresh():
        """
        Check if the cache file is fresh based on the defined CACHE_TTL.

        Returns:
            bool: True if the cache is fresh, False otherwise.
        """
        cache_path = MultiKubeConfig.CACHE_FILE
        if os.path.exists(cache_path):
            return (time.time() - os.path.getmtime(cache_path)) < MultiKubeConfig.CACHE_TTL
        return False

    @staticmethod
    def load_cache():
        """
        Load the cached data from the cache file.

        Returns:
            dict: The cached data as a dictionary.
        """
        with open(MultiKubeConfig.CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
