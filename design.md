----
 # GPUScheduler: System Design Document

 **Version:** 1.0
 **Status:** Proposed
 **Author:** Engineering Team

 ---

 ## 1. Introduction

 ### 1.1. Overview

 GPUScheduler is a dynamic, AI-driven platform for GPU resource management. Its primary goal is to provide a seamless, "zero-wait" experience for developers and researchers by moving from a reactive resource management model to a proactive, predictive allocation model.

 The system is composed of two main parts:
 1.  **A Cloud-Native Control Plane**: A highly available, scalable, and secure backend service that manages the lifecycle of GPU resources across multiple cloud providers.
 2.  **An AI-Powered Client Agent**: A lightweight, open-source, and user-owned agent that runs within the customer's environment to anticipate resource needs and proactively request them from the control plane.

 ### 1.2. Goals

 *   **Maximize GPU Utilization & Minimize Cost**: Reduce idle time and leverage cost-effective options like spot instances.
 *   **Improve Developer Velocity**: Minimize or eliminate developer wait time for GPU resources.
 *   **Provide a Secure, Multi-Tenant Service**: Ensure strict isolation and governance between customers.
 *   **Build Trust through Architecture**: Guarantee customer data privacy by processing all sensitive information locally within the user-owned agent.

 ### 1.3. Non-Goals

 *   To replace Kubernetes or act as a general-purpose workload scheduler.
 *   To be a deep learning training framework.
 *   To manage on-premise hardware in V1.

 ---

 ## 2. System Architecture

 The system is designed as a classical, horizontally-scalable distributed system.

 ```mermaid
 graph TD
     subgraph "User Environment"
         Client["Client / Agent"]
     end
 
     subgraph "Cloud Environment (VPC)"
         APIGateway["API Gateway<br>(Rate Limiting, AuthN)"]
 
         subgraph "Application Tier"
             APIService["Stateless API<br>(FastAPI App)"]
             Cache["Distributed Cache<br>(Redis)"]
         end
 
         subgraph "Asynchronous Processing"
             Broker["Message Broker<br>(RabbitMQ)"]
             Workers["Celery Workers<br>(Provisioning, Lease Mgmt)"]
         end
 
         subgraph "Database Tier"
             Pooler["Connection Pooler<br>(PgBouncer)"]
             DB_Primary["DB (Primary)"]
             DB_Replica["DB (Replica)"]
         end
 
         CloudAPI["Cloud APIs<br>(e.g., AWS)"]
 
         Client --> APIGateway --> APIService
         APIService -- "Writes / Tasks" --> Broker --> Workers
         APIService -- "Reads" --> Pooler --> DB_Replica
         APIService <--> Cache
         Workers --> Pooler --> DB_Primary
         Workers --> CloudAPI
     end
 ```

 ### 2.1. Components

 *   **API Gateway**: The public entry point. Handles TLS termination, rate limiting, and initial authentication.
 *   **Stateless API Tier (FastAPI)**: The core application logic. Handles API requests, validates data, and coordinates with other services. Runs as multiple, auto-scaling replicas.
 *   **Distributed Cache (Redis)**: Caches read-heavy data (e.g., GPU details) to reduce database load and improve latency. Also used for idempotency key storage.
 *   **Message Broker (RabbitMQ)**: Manages the queue of asynchronous tasks, providing durability and decoupling the API from the workers.
 *   **Celery Workers**: A fleet of background workers that execute long-running tasks like provisioning instances, de-provisioning, and managing resource leases.
 *   **Database (PostgreSQL)**: The single source of truth, configured in a Primary-Replica setup for scalability and high availability.
 *   **Connection Pooler (PgBouncer)**: Sits between the application and the database to manage connections efficiently under high load.

 ### 2.2. Component Deep Dive

 *   **Stateless API Tier (FastAPI)**
     *   **Framework**: Python with FastAPI for its high performance and automatic OpenAPI generation.
     *   **Data Validation**: Pydantic models will be used for all incoming request bodies and outgoing responses, ensuring strict data validation at the edge.
     *   **Database Interaction**: SQLAlchemy Core will be used for database queries to allow for fine-grained control over SQL generation. Asynchronous database access will be managed by `asyncpg`.
     *   **Dependencies**: FastAPI's dependency injection system will be used to manage database connections, authentication context, and other shared resources.

 *   **Celery Workers**
     *   **Task Routing**: Specific queues will be used for different task types (e.g., a `provisioning` queue for cloud API calls, a `management` queue for lease checks) to allow for independent scaling of worker pools.
     *   **Key Tasks**:
         *   `provision_gpu`: Handles the multi-step process of calling cloud APIs, waiting for instance readiness, and updating the database.
         *   `deprovision_gpu`: Terminates cloud instances.
         *   `check_expired_leases` (Periodic): A Celery Beat task to run on a schedule and trigger de-provisioning for expired leases.
     *   **Configuration**: Workers will be configured with `acks_late=True` and default retry policies (with exponential backoff and jitter) for all tasks that interact with external APIs.

 *   **Database (PostgreSQL)**
     *   **Indexing Strategy**: In addition to primary and foreign keys, composite indexes will be created for frequently queried combinations. For example, a composite index on `(organization_id, status)` in the `gpus` table will be critical for fast quota checks. An index on `lease_expires_at` is also required for the lease management worker.
     *   **Migrations**: Database schema changes will be managed using a migration tool like **Alembic**. All schema changes will be peer-reviewed and applied as part of the CI/CD pipeline.

 *   **Distributed Cache (Redis)**
     *   **High Availability**: An ElastiCache for Redis cluster will be deployed in multi-AZ mode with automatic failover.
     *   **Use Cases**:
         *   **Idempotency Store**: Storing `Idempotency-Key` responses.
         *   **Read-Through Cache**: Caching `GET /gpu/{id}` responses.
         *   **Rate Limiting**: (Future) Could be used for more complex, distributed rate-limiting logic if the API Gateway's capabilities are insufficient.

 ---

 ## 3. API Specification

 The service exposes a RESTful API. A full OpenAPI specification is automatically generated by the FastAPI service and available at the `/docs` endpoint.

 ### 3.1. Key Endpoints

 *   `POST /api/gpuscheduler/v1/allocate`: Asynchronously requests a new GPU.
 *   `GET /api/gpuscheduler/v1/gpus`: Lists GPUs, with filters for status and health.
 *   `GET /api/gpuscheduler/v1/gpu/{gpu_id}`: Retrieves details for a specific GPU.
 *   `DELETE /api/gpuscheduler/v1/gpu/{gpu_id}`: De-allocates and de-provisions a GPU.
 *   `PUT /api/gpuscheduler/v1/gpu/{gpu_id}/heartbeat`: Used by the on-instance agent to report health metrics.

 ### 3.2. Authentication

 All requests must be authenticated. The service will use API Key authentication. Clients must include an `Authorization: Bearer <API_KEY>` header.

 ### 3.3. Idempotency

 All state-changing endpoints (`POST`, `DELETE`) support idempotency via the `Idempotency-Key: <UUID>` header to prevent duplicate operations on retries.

 ---

 ## 4. Data Model and Database Schema

 The database is the system's source of truth. The schema is designed for multi-tenancy, security, and governance.

 ### 4.1. `organizations`
 Represents a customer entity or team.

 | Column | Type | Constraints | Description |
 |---|---|---|---|
 | `id` | `UUID` | Primary Key | Unique identifier for the organization. |
 | `name` | `VARCHAR(255)` | Not Null | Human-readable name of the organization. |
 | `max_active_gpus` | `INTEGER` | Not Null, Default: 5 | Quota for the max number of concurrent GPUs. |
 | `created_at` | `TIMESTAMPTZ` | Not Null | Timestamp of creation. |
 | `updated_at` | `TIMESTAMPTZ` | Not Null | Timestamp of last update. |

 ### 4.2. `users`
 Represents an individual user within an organization.

 | Column | Type | Constraints | Description |
 |---|---|---|---|
 | `id` | `UUID` | Primary Key | Unique identifier for the user. |
 | `organization_id` | `UUID` | FK to `organizations.id` | The organization this user belongs to. |
 | `email` | `VARCHAR(255)` | Not Null, Unique | User's email, used for identification. |
 | `role` | `VARCHAR(50)` | Not Null | User's role (`admin`, `member`). |
 | `created_at` | `TIMESTAMPTZ` | Not Null | Timestamp of creation. |
 | `updated_at` | `TIMESTAMPTZ` | Not Null | Timestamp of last update. |

 ### 4.3. `api_keys`
 Stores authentication credentials for programmatic access. **Raw API keys are never stored.**

 | Column | Type | Constraints | Description |
 |---|---|---|---|
 | `id` | `UUID` | Primary Key | Unique identifier for the key. |
 | `key_hash` | `VARCHAR(255)` | Not Null, Unique | A secure bcrypt hash of the API key. |
 | `key_prefix` | `VARCHAR(8)` | Not Null, Unique | A short, non-secret prefix for key identification (e.g., `gpus_`). |
 | `user_id` | `UUID` | FK to `users.id` | The user who owns this key. |
 | `organization_id` | `UUID` | FK to `organizations.id` | The organization this key is scoped to. |
 | `expires_at` | `TIMESTAMPTZ` | Nullable | Optional expiration date for the key. |
 | `last_used_at` | `TIMESTAMPTZ` | Nullable | Timestamp of the last time the key was used. |
 | `created_at` | `TIMESTAMPTZ` | Not Null | Timestamp of creation. |

 ### 4.4. `gpus`
 The core table tracking all GPU resources.

 | Column | Type | Constraints | Description |
 |---|---|---|---|
 | `id` | `UUID` | Primary Key | Unique identifier for the GPU resource. |
 | `organization_id` | `UUID` | FK to `organizations.id` | The organization that owns this GPU. |
 | `user_id` | `UUID` | FK to `users.id` | The user who allocated this GPU. |
 | `status` | `VARCHAR(50)` | Not Null, Indexed | `PROVISIONING`, `AVAILABLE`, `BUSY`, `DEPROVISIONING`, `ERROR`. |
 | `health_state` | `VARCHAR(50)` | Not Null | `HEALTHY`, `UNHEALTHY`, `DEGRADED`, `UNKNOWN`. |
 | `lease_expires_at`| `TIMESTAMPTZ` | Not Null | Timestamp when the lease expires and the GPU will be reclaimed. |
 | `last_seen` | `TIMESTAMPTZ` | Nullable | Timestamp of the last heartbeat from the on-instance agent. |
 | ... | ... | ... | Other fields from the `GPUInfo` model (`hostname`, `name`, `cost_per_hour`, etc.). |
 | `created_at` | `TIMESTAMPTZ` | Not Null | Timestamp of creation. |
 | `updated_at` | `TIMESTAMPTZ` | Not Null | Timestamp of last update. |

 ---

 ## 5. Core Workflows

 ### 5.1. GPU Allocation

 This sequence diagram illustrates the end-to-end flow for a new GPU allocation request.

 ```mermaid
 sequenceDiagram
     participant Client
     participant API Gateway
     participant API Service
     participant Redis
     participant DB (Replica)
     participant RabbitMQ
     participant Celery Worker
     participant DB (Primary)
     participant Cloud API

     Client->>+API Gateway: POST /allocate (Idempotency-Key)
     API Gateway->>+API Service: Forward authenticated request
     API Service->>+Redis: GET idempotency_key
     Redis-->>-API Service: (Cache miss)
     API Service->>+DB (Replica): SELECT COUNT(*) FROM gpus WHERE org_id=X AND status='BUSY'
     DB (Replica)-->>-API Service: (Quota OK)
     API Service->>+RabbitMQ: PUBLISH provision_gpu task
     RabbitMQ-->>-API Service: (Ack)
     API Service->>+Redis: SET idempotency_key response
     Redis-->>-API Service: OK
     API Service-->>-Client: 202 Accepted (task_id)

     Note over RabbitMQ, Celery Worker: Worker consumes task asynchronously
     Celery Worker->>+DB (Primary): INSERT INTO gpus (status='PROVISIONING')
     DB (Primary)-->>-Celery Worker: (Returns new gpu_id)
     Celery Worker->>+Cloud API: CreateInstance(...)
     Cloud API-->>-Celery Worker: (Instance created)
     Celery Worker->>+DB (Primary): UPDATE gpus SET status='BUSY' WHERE id=gpu_id
     DB (Primary)-->>-Celery Worker: OK
 ```

 ### 5.2. Lease Management

 1.  A periodic Celery Beat task (`check_expired_leases`) runs every 5 minutes.
 2.  The task queries the `gpus` table for all records where `lease_expires_at < NOW()` and `status` is not `DEPROVISIONING`.
 3.  For each expired GPU, it submits a `deprovision_gpu` task to RabbitMQ with the `gpu_id`.
 4.  It updates the status of these GPUs to `DEPROVISIONING` in the database to prevent them from being selected again.

 ```mermaid
 graph TD
     A[Start] --> B{Celery Beat<br>Every 5 mins};
     B --> C[Run `check_expired_leases` task];
     C --> D["DB: Find GPUs where<br>lease_expires_at < NOW()"];
     D --> E{Any expired GPUs?};
     E -- No --> F[End Cycle];
     E -- Yes --> G["For each expired GPU"];
     G --> H["DB: UPDATE status to<br>'DEPROVISIONING'"];
     H --> I["RabbitMQ: PUBLISH<br>`deprovision_gpu` task"];
 
     subgraph "Async Deprovisioning"
         J[Deprovision Worker consumes task]
         J --> K["Cloud API: Terminate Instance"];
         K --> L["DB: UPDATE status to<br>'DEPROVISIONED'"];
     end
     I --> J;
 ```

 ---

 ## 6. Non-Functional Requirements

 ### 6.1. Security

 *   **Authentication**: API Key-based. On receiving a request, the API will:
     1. Extract the key from the `Authorization: Bearer <key>` header.
     2. Split the key into its `prefix` and `token` parts.
     3. Query the `api_keys` table by the indexed `key_prefix`.
     4. Use a constant-time comparison function to check if `bcrypt.check(token, stored_hash)` is true.
     5. If valid, the `user_id` and `organization_id` from the `api_keys` table are attached to the request context for authorization checks.
 *   **Authorization**: Role-Based Access Control (RBAC) will be enforced at the API level. For example, a `DELETE /gpu/{gpu_id}` request will verify that the `organization_id` from the request context matches the `organization_id` on the GPU record in the database. Only users with the `admin` role can view GPUs outside their own allocation.
 *   **Network Security**: All components will reside in a private VPC. Only the API Gateway will be exposed to the public internet. Database access will be restricted to the API and worker security groups.

 ### 6.2. Scalability & Performance

 *   **API Tier**: Stateless and horizontally scalable via Kubernetes HPA.
 *   **Database**: A Primary-Replica model will be used. Writes go to the Primary, reads are load-balanced across Replicas. A connection pooler (PgBouncer) is mandatory.
 *   **Caching Strategy**:
     *   **Idempotency**: `POST` and `DELETE` responses are cached with the `Idempotency-Key` as the cache key. TTL: 24 hours.
     *   **Read-Through Cache**: `GET /gpu/{gpu_id}` results are cached. The cache key will be `gpu:{gpu_id}`. The cache is invalidated in the `PUT /heartbeat` endpoint or any other state-changing operation. TTL: 5 minutes.
     *   **List Cache**: `GET /gpus` is difficult to cache effectively due to filters. This will rely on fast, indexed queries against the read replicas.

 ### 6.3. Availability & Fault Tolerance

 *   **Redundancy**: All components (API, workers, cache, DB) will run with multiple replicas across different availability zones.
 *   **Database Failover**: Managed database services (e.g., AWS RDS) will be used for automated promotion of a replica to primary in case of failure.
 *   **Task Reliability**: Celery tasks will use `acks_late=True` and configured automatic retries with exponential backoff to handle transient failures and worker crashes.
 *   **Circuit Breaker**: Workers will implement a circuit breaker pattern when calling external cloud APIs to prevent cascading failures.

 ### 6.4. Cost Governance

 *   **Quotas**: The `organizations` table in the database will contain columns for `max_active_gpus`. The allocation endpoint must check this before creating a provisioning task.
 *   **Lease Management**: Every GPU record will have a `lease_expires_at` timestamp. A periodic Celery task will scan for expired leases and submit de-provisioning tasks for them.

 ---

 ## 7. Observability

 ### 7.1. Metrics (Prometheus)
 *   **API**: `http_requests_total` (by endpoint, method, status code), `http_request_duration_seconds` (histogram).
 *   **Celery**: `celery_tasks_total` (by name, state), `celery_task_duration_seconds` (histogram), `celery_queue_length`.
 *   **Database**: Connection pool stats (active, waiting), query latency, replication lag.

 ### 7.2. Logging
 All logs will be structured (JSON). A unique `request_id` generated at the API Gateway will be propagated through all services and log messages to correlate events for a single request.

 ### 7.3. Tracing (OpenTelemetry)
 Traces will be generated for all API requests, providing a detailed view of the request lifecycle across the API, message broker, and workers.

 ---

 ## 8. Client-Side Agent

 The architecture and implementation details for the client-side AI agent are extensive and are captured in a separate document.

 **Please refer to: Client-Side Agent Design Document**

---

## 9. Development & Deployment Strategy (CI/CD)

To ensure a high-quality, reliable product, we will adopt a modern CI/CD workflow with Infrastructure as Code (IaC) for our AWS deployment. This approach facilitates rapid iteration, automated testing, and consistent, reproducible environments.

### 9.1. Source Control

*   **Repository**: A monorepo containing both the backend service and the client-side agent code.
*   **Branching Strategy**: A trunk-based development model will be used. All changes are merged directly into the `main` branch via Pull Requests (PRs) that must pass all automated checks and receive at least one peer review. Releases will be managed via Git tags.

### 9.2. Infrastructure as Code (IaC)

*   **Tooling**: We will use **Terraform** to define and manage all AWS resources (VPC, security groups, RDS databases, EKS clusters, ElastiCache for Redis, etc.).
*   **State Management**: Terraform state will be stored remotely and securely in an S3 bucket with state locking enabled via DynamoDB to prevent conflicts.
*   **Environments**: We will maintain separate Terraform workspaces for `staging` and `production` environments to ensure strict isolation.

### 9.3. Backend Service CI/CD Pipeline

The pipeline will be triggered on every push to the `main` branch.

1.  **Lint & Test**:
    *   Run static analysis (e.g., `black`, `ruff`).
    *   Execute unit tests (`pytest`).
    *   Run integration tests against containerized versions of PostgreSQL and Redis.
2.  **Build & Push**:
    *   Build Docker images for the API server and Celery workers.
    *   Tag images with the Git commit SHA.
    *   Push images to Amazon ECR (Elastic Container Registry).
3.  **Deploy to Staging**:
    *   Run `terraform apply` for the `staging` workspace to update the Kubernetes (EKS) deployment with the new image tag.
    *   Run a suite of end-to-end API tests against the live staging environment.
4.  **Deploy to Production**:
    *   This step will require manual approval after verifying the staging deployment.
    *   Upon approval, the pipeline will trigger a safe deployment strategy (e.g., Blue/Green or Canary) to update the production environment.

### 9.4. Client-Side Agent Release Pipeline

This pipeline is triggered manually by creating a new Git tag (e.g., `v1.1.0`).

1.  **Lint & Test**: Run static analysis and unit tests for the agent code.
2.  **Build Binaries**: Cross-compile the agent into binaries for target platforms (Linux/amd64, macOS/arm64, Windows/amd64).
3.  **Sign Binaries**: Use automated code signing (e.g., via AWS Signer) to cryptographically sign all binaries. This is critical for customer trust.
4.  **Create Release**:
    *   Create a draft release on GitHub.
    *   Upload the signed binaries, checksums, and release notes as release artifacts.
    *   Publish the release.
