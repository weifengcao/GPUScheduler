# GPUScheduler: Client-Side Agent Design Document

 **Version:** 1.0
 **Status:** Proposed
 **Author:** Engineering Team

 ---

 ## 1. Introduction

 ### 1.1. Overview

 The AI-powered client agent is a cornerstone of the GPUScheduler product vision. It is a lightweight, user-owned application that runs within the customer's environment to anticipate resource needs and proactively request them from the GPUScheduler control plane.

 Its core design principle is **trust through architecture**. The agent is open-source and processes all sensitive data locally, ensuring that no private customer data (code, logs, etc.) is ever transmitted externally.

 ### 1.2. Goals

 *   **Proactive Allocation**: Monitor local workloads to predict the need for a GPU before a user manually requests one.
 *   **Zero Configuration (as much as possible)**: Use LLM capabilities to infer intent from logs and scripts with minimal user configuration.
 *   **Security & Privacy**: Operate with complete data privacy, never sending sensitive information to the GPUScheduler backend.
 *   **Extensibility**: Allow users to define custom "triggers" or "monitors" for their specific workflows.

 ---

 ## 2. Agent Architecture

 The agent is designed as a modular, event-driven application that runs as a continuous background process.

 ```mermaid
 graph TD
     subgraph "User's Local Environment"
         Config["Configuration<br>(config.yaml)"]
         Monitors["Monitor Plugins<br>(LogTailer, FileWatcher)"]
         Analyzer["Analyzer<br>(LLM Interface)"]
         ActionTaker["Action Taker<br>(API Client)"]
     end
 
     subgraph "External Services"
         ControlPlane["GPUScheduler Control Plane"]
     end
 
     Config --> Monitors
     Monitors -- "Events (log lines, file changes)" --> Analyzer
     Analyzer -- "Inferred Intent<br>(e.g., 'start training')" --> ActionTaker
     ActionTaker -- "POST /allocate" --> ControlPlane
 ```

 ### 2.1. Components

 *   **Configuration (`config.yaml`)**: A YAML file defines the agent's behavior. It will support environment variable substitution for sensitive values.

     ```yaml
     # config.yaml
     gpuscheduler:
       api_endpoint: "https://api.gpuscheduler.io"
       api_key: "env(GPUSCHEDULER_API_KEY)" # Support for env var substitution

     llm:
       provider: "openai" # or "anthropic", etc.
       api_key: "env(OPENAI_API_KEY)"
       model: "gpt-3.5-turbo"

     # Default allocation parameters when a GPU is requested
     allocation_defaults:
       user_region: "us-east-1"
       job_type: "TRAINING"
       requirements:
         min_memory_gb: 16

     monitors:
       - name: "training_log_monitor"
         type: "log_tailer"
         path: "/var/log/ml_jobs.log"
         prompt: "Does this log line indicate a GPU-intensive training job is starting? Respond with only YES or NO. Line: {line}"
       - name: "jupyter_save_monitor"
         type: "file_watcher"
         path: "~/notebooks/"
         pattern: "*.ipynb"
         prompt: "Does this Jupyter notebook appear to be a heavy ML training job? Respond with only YES or NO. Content: {content}"
     ```

 *   **Monitor Plugins**: A set of pluggable modules responsible for watching for events in the user's environment.
     *   `LogTailer`: Tails specified log files using an efficient library (e.g., Python's `watchdog`) and streams new lines to the Analyzer.
     *   `FileWatcher`: Watches directories for new or modified files. It will read the file content and pass it to the Analyzer.
     *   `ProcessMonitor`: (Future) Watches for specific running processes.
 
 *   **Analyzer (LLM Interface)**: The "brain" of the agent.
     *   Receives events from the monitors.
     *   Uses a prompt template defined in the configuration to construct a precise prompt for the configured LLM.
     *   Parses the LLM's response robustly, trimming whitespace and handling case-insensitivity (e.g., "yes", "YES", " Yes.").
 
 *   **Action Taker**: Executes actions based on the Analyzer's decision.
     *   The primary action is to call the `POST /api/gpuscheduler/v1/allocate` endpoint on the GPUScheduler control plane.
     *   It constructs the request body based on user preferences in `config.yaml` (e.g., preferred region, default job type).
     *   **State Management**: To prevent spamming allocation requests for the same event, the Action Taker will maintain an internal state. After successfully triggering an action for a specific monitor (e.g., `training_log_monitor`), it will enter a "cooldown" period for that monitor (e.g., 30 minutes), ignoring further signals from it until the cooldown expires.

 ---

 ## 3. Detailed Workflow

 This sequence diagram illustrates the agent's internal event processing loop.

 ```mermaid
 sequenceDiagram
     participant User
     participant FileSystem
     participant Monitor
     participant Analyzer
     participant LLM_API
     participant ActionTaker
     participant GPUScheduler_API

     User->>+FileSystem: Saves `job.log`
     Monitor->>FileSystem: (Tailing file)
     Monitor->>+Analyzer: Event: New log line
     Analyzer->>+LLM_API: POST /completions (prompt)
     LLM_API-->>-Analyzer: Response: "YES"
     Analyzer->>+ActionTaker: Signal: "Allocate GPU"
     ActionTaker->>ActionTaker: Check Cooldown (OK)
     ActionTaker->>+GPUScheduler_API: POST /allocate
     GPUScheduler_API-->>-ActionTaker: 202 Accepted
     ActionTaker->>ActionTaker: Start Cooldown for Monitor
 ```

 ---

 ## 4. Security & Trust

 This is the most critical aspect of the agent's design.

 *   **Open Source**: The agent's complete source code will be available on a public repository (e.g., GitHub) under a permissive license (e.g., Apache 2.0).
 *   **Secure Credential Storage**: The agent will not store credentials in plain text. It will leverage the host operating system's native secret management service (e.g., macOS Keychain, Windows Credential Manager, or Linux Secret Service / KWallet).
 *   **No Data Egress**: The agent is explicitly designed to *never* send customer logs, file contents, or any other sensitive information to the GPUScheduler backend or any other third party. The only outbound communication is to the user-configured LLM API and the GPUScheduler API.
 *   **Signed Binaries**: For distribution, we will provide cryptographically signed binaries and container images, allowing users to verify that the code they are running has not been tampered with.

---

## 5. Extensibility

The agent will be designed with a simple plugin architecture to allow the community and customers to create their own monitors.

A new monitor will be a Python class that inherits from a `BaseMonitor` and implements a single `start()` method. The agent's main process will dynamically load all monitor classes specified in the `config.yaml` file.

```python
# Example of a custom monitor plugin
class BaseMonitor:
    def __init__(self, config, analyzer): ...
    def start(self): raise NotImplementedError

class MyCustomSlurmMonitor(BaseMonitor):
    def start(self):
        # Custom logic to poll the Slurm queue
        while True:
            if "new_gpu_job" in self.poll_slurm_queue():
                self.analyzer.process_event("Slurm job detected")
            time.sleep(60)
```

---

## 6. Packaging and Distribution

To ensure ease of use, the agent will be distributed as a single, self-contained executable.
*   **Tooling**: We will use **PyInstaller** to package the Python application, its dependencies, and the standard monitor plugins into a single binary for each target OS (Linux, macOS, Windows).
*   **Distribution**: Signed binaries will be attached to GitHub Releases, and we will also provide a multi-arch Docker image for containerized environments.
