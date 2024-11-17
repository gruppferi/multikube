import json
import sys
import os
import inquirer
from .config import MultiKubeConfig
import logging

logger = logging.getLogger(__name__)

class ContextManager:
    """
    A utility class for managing cluster contexts, including storing, retrieving, and setting default contexts.
    """

    @staticmethod
    def store_cluster_context(pattern):
        """
        Store a new cluster context with a unique name.

        Args:
            pattern (str): The pattern associated with the cluster context.
        """
        contexts = ContextManager.load_contexts()

        while True:
            context_name = input("Enter a unique name for this context: ").strip()
            if context_name in contexts:
                logger.info(
                    "The context name %s already exists. "
                    "Please choose a different name.", context_name
                )
            else:
                break

        contexts[context_name] = pattern

        with open(MultiKubeConfig.CONTEXTS_FILE, "w", encoding="utf-8") as f:
            json.dump(contexts, f)
        logger.info("Context %s with pattern %s stored successfully.", context_name, pattern)

    @staticmethod
    def set_default_context(context_name):
        """
        Set the default context to the specified context name.

        Args:
            context_name (str): The name of the context to set as default.

        Raises:
            SystemExit: If the context name is not found or no contexts are stored.
        """
        if os.path.exists(MultiKubeConfig.CONTEXTS_FILE):
            with open(MultiKubeConfig.CONTEXTS_FILE, "r", encoding="utf-8") as f:
                contexts = json.load(f)
            if context_name in contexts:
                with open(MultiKubeConfig.DEFAULT_CONTEXT_FILE, "w", encoding="utf-8") as f:
                    json.dump({"default_context": context_name}, f)
                logger.info("Default context set to %s", context_name)
            else:
                logger.info("Context %s not found.", context_name)
        else:
            logger.error("No contexts stored. Use --store-clusters-contexts to add contexts first.")
            sys.exit(1)

    @staticmethod
    def get_default_context_pattern():
        """
        Retrieve the pattern associated with the default context.

        Returns:
            str or None: The pattern for the default context, or None if no default context exists.
        """
        if os.path.exists(MultiKubeConfig.DEFAULT_CONTEXT_FILE):
            with open(MultiKubeConfig.DEFAULT_CONTEXT_FILE, "r", encoding="utf-8") as f:
                default_context = json.load(f).get("default_context")
            if os.path.exists(MultiKubeConfig.CONTEXTS_FILE):
                with open(MultiKubeConfig.CONTEXTS_FILE, "r", encoding="utf-8") as f:
                    contexts = json.load(f)
                return contexts.get(default_context, None)
        return None

    @staticmethod
    def prompt_user_for_context():
        """
        Prompt the user to select a context interactively.

        Returns:
            str: The pattern associated with the selected context.

        Raises:
            SystemExit: If no contexts are available.
        """
        if os.path.exists(MultiKubeConfig.CONTEXTS_FILE):
            with open(MultiKubeConfig.CONTEXTS_FILE, "r", encoding="utf-8") as f:
                contexts = json.load(f)
            context_choices = list(contexts.keys())
            question = [
                inquirer.List(
                    "context",
                    message="Select a context",
                    choices=context_choices
                )
            ]
            answer = inquirer.prompt(question)
            return contexts.get(answer["context"])
        logger.error("No contexts available. Please add one using --store-clusters-contexts.")
        sys.exit(1)

    @staticmethod
    def load_contexts():
        """
        Load all stored contexts.

        Returns:
            dict: A dictionary of context names and their associated patterns.
        """
        if os.path.exists(MultiKubeConfig.CONTEXTS_FILE):
            with open(MultiKubeConfig.CONTEXTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
