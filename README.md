<p align="center">
  <img src="assets/images/multikube.png" width="200">
</p>

# Multikube Tool

`multikube` is a command-line tool designed to run `kubectl` commands across multiple AWS EKS clusters in parallel, making it easier to manage and retrieve data from various Kubernetes clusters in aggregated format. `multikube` supports caching configurations for efficiency and formats output dynamically for a streamlined view across clusters.

## Features

- **Cluster Auto Discovery**: Automatically discovers all EKS clusters across specified AWS accounts and regions during the initial setup. This comprehensive scanning ensures that all relevant clusters are included without manual configuration.
- **Parallel Execution**: Execute `kubectl` commands across multiple clusters simultaneously, enhancing efficiency and saving time.
- **Result Aggregation**: Aggregate and display outputs from all targeted clusters in a single, unified format, simplifying analysis and monitoring.
- **Cluster Caching**: Cache critical cluster and kubeconfig information to accelerate repeated commands, reducing load times and improving responsiveness.
- **Automatic Command Formatting**: Outputs are dynamically formatted based on the `kubectl` command type to ensure clarity and readability. For example, structured tables are used for `get` commands, while raw text is used for `logs`.
- **Debian Package Installation**: Install `multikube` easily on any Debian-based system using a `.deb` package, streamlining the setup process.

## Installation

### Step 1: Download the `.deb` Package

Go to the [GitHub Releases](https://github.com/yourrepo/multikube/releases) section and download the latest `.deb` package.

### Step 2: Install the Package

Use the following command to install the package:
```bash
sudo dpkg -i multikube_<version>.deb
```

### Step 3: Initialize `multikube`:
   Initialize the cache to facilitate quicker access to your clusters:
   ```bash
   multikube --init
   ```
   During initialization, if `~/.multikube/eks_regions.json` does not exist or is empty, you will be prompted to enter the AWS regions (comma-separated). `multikube` will then scan all AWS profiles configured in `~/.aws/config` for these regions, searching for available EKS clusters. Once found, it stores the cluster information in `~/.multikube/cluster_cache.json` for faster future access.

### Step 4: Create Cluster Context:
   To streamline the management of specific clusters, you can create a context that matches your clusters using a regex pattern. This context is used to filter clusters during command execution:
   ```bash
   multikube --store-clusters-contexts "<regex-pattern>"
   ```
   Replace `<regex-pattern>` with the appropriate regular expression that matches the names of the clusters you intend to manage. This command saves the regex as a context for quick retrieval and use.
   
   #### Example: Creating a Context for Production Clusters
   If you want to manage all production clusters that follow a naming convention like `prod-app1-001`, `prod-app2-001`, etc., run:
   ```bash
   multikube --store-clusters-contexts "prod-.*-001"
   ```
   After running this command, when prompted, you can name this context something like `ProductionClusters`. This context allows you to specifically target and manage production clusters when using `multikube` commands.

This sequence of steps ensures all necessary configurations are in place to utilize `multikube` effectively, streamlining the management of EKS clusters and improving operational efficiency.


#### Dependencies

The installation handles essential dependencies:
- **Prompts for the Kubernetes version** to install `kubectl` if it's not already installed.
- **Installs AWS CLI** if it’s not already present, downloading the latest version directly from AWS.
  
## Usage

### Basic Syntax
   Once you have established one or more cluster contexts, you can utilize them in two ways to target specific cluster operations:

   - **Interactive Context Selection**:
     If you start `multikube` without any specific command, you'll be prompted interactively to select from your stored contexts. This allows you to choose the desired context for your `kubectl` operations without needing to remember the exact regex patterns. Simply run:
     ```bash
     multikube
     ```
     and follow the prompts to select the context you want to use.

   - **Direct Context Specification**:
     For automated scripts or when you prefer a more direct approach, you can specify the context explicitly using the `--set-context` option. This method is particularly useful when you want to ensure that commands are executed consistently under the same context. Use the command:
     ```bash
     multikube --set-context <context-name>
     ```
     Replace `<context-name>` with the name of the context you created. For example:
     ```bash
     multikube --set-context ProductionClusters
     ```
     This sets `ProductionClusters` as the default context for subsequent `kubectl` commands within that session.

### Examples

1. **List Pods Across Clusters**
   ```bash
   multikube get pods -n default
   ```

2. **View Logs Across Clusters**
   ```bash
   multikube  logs my-pod -n my-namespace
   ```

3. **Refresh Cluster Cache**
   ```bash
   multikube  --renew-cache
   ```

### Output Formats

For `kubectl get pods`:
```plaintext
CLUSTER             NAME                                     READY   STATUS    RESTARTS   AGE
prod-mycity-app-001 my-app-pod-1                             1/1     Running   0          4h
prod-mycity-app-002 my-app-pod-2                             1/1     Running   0          3h
```

For `kubectl logs`:
```plaintext
prod-mycity-app-001: {"logtime": "2024-11-10 12:53:37.6292", "level": "INFO", "message": "Application started"}
prod-mycity-app-002: {"logtime": "2024-11-10 12:55:37.3241", "level": "ERROR", "message": "Application error"}
```

## Caching Details

- **Cluster Data**: Cached in `~/.multikube/cluster_cache.json`.
- **Kubeconfig Files**: Stored under `~/.multikube/kubeconfigs`.

### TTL Settings

By default, the cluster and kubeconfig caches are valid for 1 year.

## Troubleshooting

If you encounter permission or authentication issues, verify that your AWS CLI profiles are correctly configured with proper access credentials for the clusters.

## Future Development

The ongoing development of `multikube` is focused on expanding its capabilities and enhancing user experience. Planned future enhancements include:

- **Support for Multiple Cloud Providers**: Extend functionality to support Kubernetes clusters hosted on other cloud platforms like Azure AKS, Google GKE, and private clouds, facilitating a truly agnostic Kubernetes management tool.
- **Cluster Output Coloring**: Implement coloring in the command output for each cluster to enhance readability and allow users to quickly identify clusters based on the command line output.
- **General Improvements**: Continuous improvements in performance, usability, and security across the tool.

## License

This project is licensed under the terms described in the [LICENSE](LICENSE) file.