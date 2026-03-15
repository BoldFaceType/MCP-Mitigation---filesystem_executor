# RepoReady v1.1 — Typed Macro Catalog, 7-Policy Schema Pack, and Patch Plan

**Version:** v1.1.0  
**Date:** 2026-03-14  
**Status:** Architecture Patch Plan / RepoReady  
**Scope:** MCP filesystem executor + agent-usable control layer + CI/CD guardrails  

---

## 1. Re-read, Rephrase, Respond

### Reframed objective
Turn the prior architecture into a **single, concrete RepoReady v1.1 canvas** that includes:

- a **typed macro catalog**
- a **7-policy schema pack**
- **concrete Pydantic models**
- **CLI signatures** for helper scripts
- an **exact patch plan** with new files
- an **MCP request/response schema set**
- a **GitHub Actions workflow map**
- a **CI gate order**

### Core answer
Yes. The right move is to add a **thin, typed control layer** on top of your MCP filesystem approach so models and humans interact with:

- obvious names
- obvious boundaries
- typed requests
- deterministic helper scripts
- validated macros
- enforced policy gates

This patch makes the workflow more:
- automated
- legible
- dummy-resistant
- CI-enforceable
- agent-usable

---

## 2. Naming Standard (Locked for v1.1)

### Helper scripts use `verb_object`
Examples:
- `discover_tools`
- `describe_server`
- `create_task_stub`
- `validate_task`
- `run_task`
- `run_macro`
- `explain_error`

### Macros use `verb_object` or `verb_object_to_object`
Examples:
- `fetch_document`
- `search_documents`
- `sync_meeting_notes_to_tasks`
- `promote_artifact`
- `run_premerge_checks`

### Policies use `<Domain>Policy`
Examples:
- `ExecutionPolicy`
- `MutationPolicy`
- `SelectionPolicy`
- `RedactionPolicy`
- `ApprovalPolicy`
- `OwnershipPolicy`
- `ArtifactPolicy`

### Semantic glossary
- **document** = external readable content
- **task** = executable unit of work
- **contract** = typed specification for work
- **artifact** = file/report/output produced by execution
- **tool** = single callable capability
- **macro** = approved multi-step workflow
- **server** = provider/container of tools

---

## 3. Exact New Files

```text
mcp-filesystem-executor/
├─ README.md
├─ CHANGELOG.md
├─ pyproject.toml
├─ package.json
├─ Makefile
├─ .env.example
├─ docs/
│  ├─ architecture/
│  │  ├─ macro-catalog.md
│  │  ├─ policy-pack.md
│  │  ├─ mcp-schemas.md
│  │  ├─ ci-gates.md
│  │  └─ naming-standard.md
│  ├─ agent-quickstart.md
│  ├─ helper-cli.md
│  ├─ server-manifest-spec.md
│  └─ execution-policy.md
├─ schemas/
│  ├─ json/
│  │  ├─ agent_task_request.schema.json
│  │  ├─ agent_task_result.schema.json
│  │  ├─ macro_definition.schema.json
│  │  ├─ macro_run_request.schema.json
│  │  ├─ macro_run_result.schema.json
│  │  ├─ mcp_tool_request.schema.json
│  │  ├─ mcp_tool_result.schema.json
│  │  ├─ server_manifest.schema.json
│  │  ├─ execution_policy.schema.json
│  │  ├─ mutation_policy.schema.json
│  │  ├─ selection_policy.schema.json
│  │  ├─ redaction_policy.schema.json
│  │  ├─ approval_policy.schema.json
│  │  ├─ ownership_policy.schema.json
│  │  └─ artifact_policy.schema.json
│  └─ examples/
│     ├─ fetch_document.request.json
│     ├─ run_premerge_checks.request.json
│     └─ server_manifest.example.json
├─ src/
│  ├─ python/
│  │  ├─ __init__.py
│  │  ├─ contracts.py
│  │  ├─ macros.py
│  │  ├─ policies.py
│  │  ├─ mcp_models.py
│  │  ├─ manifests.py
│  │  ├─ errors.py
│  │  ├─ enums.py
│  │  ├─ cli/
│  │  │  ├─ discover_tools.py
│  │  │  ├─ describe_server.py
│  │  │  ├─ create_task_stub.py
│  │  │  ├─ validate_task.py
│  │  │  ├─ run_task.py
│  │  │  ├─ run_macro.py
│  │  │  ├─ explain_error.py
│  │  │  ├─ validate_manifest.py
│  │  │  ├─ export_json_schemas.py
│  │  │  └─ summarize_ci.py
│  │  ├─ runtime/
│  │  │  ├─ executor.py
│  │  │  ├─ policy_engine.py
│  │  │  ├─ macro_engine.py
│  │  │  ├─ manifest_loader.py
│  │  │  └─ redactor.py
│  │  └─ helper_scripts/
│  │     ├─ discover_tools.py
│  │     ├─ validate_task.py
│  │     ├─ run_task.py
│  │     ├─ run_macro.py
│  │     └─ explain_error.py
│  └─ typescript/
│     ├─ contracts.ts
│     ├─ macros.ts
│     ├─ policies.ts
│     ├─ mcp-models.ts
│     ├─ manifests.ts
│     └─ cli/
│        ├─ discover-tools.ts
│        ├─ describe-server.ts
│        ├─ create-task-stub.ts
│        ├─ validate-task.ts
│        ├─ run-task.ts
│        ├─ run-macro.ts
│        └─ explain-error.ts
├─ macros/
│  ├─ fetch_document.yaml
│  ├─ search_documents.yaml
│  ├─ sync_meeting_notes_to_tasks.yaml
│  ├─ deploy_container_with_redaction.yaml
│  ├─ extract_action_items_from_sources.yaml
│  ├─ recommend_tools.yaml
│  ├─ transform_file_safely.yaml
│  ├─ scaffold_from_contract.yaml
│  ├─ promote_artifact.yaml
│  └─ run_premerge_checks.yaml
├─ manifests/
│  ├─ servers/
│  │  ├─ google_drive.server.json
│  │  ├─ salesforce.server.json
│  │  ├─ docker.server.json
│  │  └─ filesystem.server.json
│  └─ policies/
│     ├─ default.execution.json
│     ├─ default.mutation.json
│     ├─ default.selection.json
│     ├─ default.redaction.json
│     ├─ default.approval.json
│     ├─ default.ownership.json
│     └─ default.artifact.json
├─ tests/
│  ├─ unit/
│  │  ├─ test_contracts.py
│  │  ├─ test_macros.py
│  │  ├─ test_policies.py
│  │  ├─ test_mcp_models.py
│  │  └─ test_manifests.py
│  ├─ integration/
│  │  ├─ test_run_task.py
│  │  ├─ test_run_macro.py
│  │  └─ test_policy_engine.py
│  ├─ schemas/
│  │  └─ test_json_schema_exports.py
│  ├─ fixtures/
│  │  ├─ macros/
│  │  ├─ manifests/
│  │  └─ requests/
│  └─ golden/
│     ├─ macro_results/
│     └─ ci_reports/
└─ .github/
   ├─ workflows/
   │  ├─ ci.yml
   │  ├─ schemas.yml
   │  ├─ macros.yml
   │  ├─ policies.yml
   │  ├─ manifests.yml
   │  ├─ smoke.yml
   │  ├─ release.yml
   │  └─ docs.yml
   └─ pull_request_template.md
```

---

## 4. Exact Pydantic Model List

### Core contracts
- `ToolRef`
- `TaskConstraint`
- `AgentTaskRequest`
- `AgentTaskResult`
- `CodegenPlan`
- `ExecutionArtifact`
- `ExecutionSummary`
- `ServerManifest`
- `ServerCapability`
- `ServerToolManifest`

### Macro models
- `MacroDefinition`
- `MacroStep`
- `MacroStepToolCall`
- `MacroStepTransform`
- `MacroStepForEach`
- `MacroRunRequest`
- `MacroRunResult`

### Policy models
- `ExecutionPolicy`
- `MutationPolicy`
- `SelectionPolicy`
- `RedactionPolicy`
- `ApprovalPolicy`
- `OwnershipPolicy`
- `ArtifactPolicy`

### MCP request/response models
- `MCPToolRequest`
- `MCPToolResult`
- `MCPToolError`
- `MCPServerSelection`
- `MCPExecutionEnvelope`

### CI/reporting models
- `CheckResult`
- `CIGateReport`
- `PremergeReport`
- `PolicyViolation`
- `ValidationErrorReport`

---

## 5. Concrete Pydantic Models

```python
# src/python/enums.py
from typing import Literal

RuntimeName = Literal["python", "node", "deno", "bun"]
RiskLevel = Literal["low", "medium", "high"]
ExecutionMode = Literal["read_only", "workspace_write", "tool_call_only"]
ArtifactKind = Literal["stdout", "stderr", "json", "file", "report", "screenshot"]
ApprovalLevel = Literal["none", "human_required", "maintainer_required"]
StepKind = Literal["tool_call", "transform", "foreach"]
PolicyDecision = Literal["allow", "warn", "deny"]
```

```python
# src/python/contracts.py
from pydantic import BaseModel, Field, ConfigDict
from .enums import RuntimeName, RiskLevel, ExecutionMode, ArtifactKind

class ToolRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    server_name: str
    tool_name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = "low"

class TaskConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    value: str

class AgentTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_name: str
    objective: str
    runtime: RuntimeName
    execution_mode: ExecutionMode = "tool_call_only"
    allowed_tools: list[ToolRef] = Field(default_factory=list)
    constraints: list[TaskConstraint] = Field(default_factory=list)
    timeout_seconds: int = Field(default=60, ge=1, le=1800)
    require_redaction: bool = True
    workspace_root: str | None = None

class ExecutionArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: ArtifactKind
    path: str | None = None
    content_preview: str | None = None

class CodegenPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    imports: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = "low"

class ExecutionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: bool
    task_name: str
    tool_calls: list[str] = Field(default_factory=list)
    artifacts: list[ExecutionArtifact] = Field(default_factory=list)
    redacted: bool = True
    final_summary: str

class AgentTaskResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request: AgentTaskRequest
    plan: CodegenPlan | None = None
    summary: ExecutionSummary
```

```python
# src/python/manifests.py
from pydantic import BaseModel, Field, ConfigDict
from .enums import RuntimeName, RiskLevel

class ServerCapability(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str

class ServerToolManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = "low"
    input_schema: str
    output_schema: str
    examples: list[str] = Field(default_factory=list)

class ServerManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    server_name: str
    version: str
    runtime: RuntimeName
    capabilities: list[ServerCapability] = Field(default_factory=list)
    tools: list[ServerToolManifest] = Field(default_factory=list)
```

```python
# src/python/macros.py
from pydantic import BaseModel, Field, ConfigDict
from .enums import StepKind, RuntimeName, RiskLevel

class MacroStepToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    server_name: str
    tool_name: str
    args: dict[str, str] = Field(default_factory=dict)

class MacroStepTransform(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transform_name: str
    args: dict[str, str] = Field(default_factory=dict)

class MacroStepForEach(BaseModel):
    model_config = ConfigDict(extra="forbid")
    collection_name: str
    loop_var: str = "item"
    server_name: str
    tool_name: str
    args: dict[str, str] = Field(default_factory=dict)

class MacroStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: str
    kind: StepKind
    tool_call: MacroStepToolCall | None = None
    transform: MacroStepTransform | None = None
    foreach: MacroStepForEach | None = None

class MacroDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str
    runtime: RuntimeName
    risk_level: RiskLevel = "low"
    input_schema_ref: str
    output_schema_ref: str
    tags: list[str] = Field(default_factory=list)
    steps: list[MacroStep] = Field(default_factory=list)
    when_not_to_use: list[str] = Field(default_factory=list)

class MacroRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    macro_name: str
    args: dict[str, str] = Field(default_factory=dict)
    workspace_root: str | None = None
    require_approval: bool = False

class MacroRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    macro_name: str
    success: bool
    artifacts: list[str] = Field(default_factory=list)
    final_summary: str
```

```python
# src/python/policies.py
from pydantic import BaseModel, Field, ConfigDict
from .enums import ApprovalLevel, PolicyDecision

class ExecutionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    allow_network: bool = False
    allow_subprocess: bool = False
    allow_filesystem_write: bool = True
    allowed_write_roots: list[str] = Field(default_factory=list)
    blocked_imports: list[str] = Field(default_factory=lambda: ["subprocess", "os.system"])
    max_tool_calls: int = Field(default=5, ge=1, le=100)
    max_runtime_seconds: int = Field(default=60, ge=1, le=3600)

class MutationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    allow_create: bool = True
    allow_update: bool = True
    allow_delete: bool = False
    allowed_write_roots: list[str] = Field(default_factory=list)
    forbidden_write_roots: list[str] = Field(default_factory=list)
    require_contract_for_new_objects: bool = True
    require_validation_before_promotion: bool = True
    max_files_changed: int = Field(default=20, ge=1, le=1000)
    max_manifest_entries_changed: int = Field(default=5, ge=1, le=500)

class SelectionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    allowed_servers: list[str] = Field(default_factory=list)
    blocked_servers: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    blocked_tools: list[str] = Field(default_factory=list)
    allowed_macros: list[str] = Field(default_factory=list)
    blocked_macros: list[str] = Field(default_factory=list)
    default_decision: PolicyDecision = "warn"

class RedactionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    redact_pii: bool = True
    redact_secrets: bool = True
    redact_tokens: bool = True
    redact_email_addresses: bool = True
    redact_account_ids: bool = False
    replacement_text: str = "[REDACTED]"

class ApprovalPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_level: ApprovalLevel = "none"
    require_approval_for_high_risk: bool = True
    require_approval_for_delete: bool = True
    require_approval_for_deploy: bool = True
    require_approval_for_bulk_changes: bool = True

class OwnershipPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role_name: str
    allowed_write_roots: list[str] = Field(default_factory=list)
    forbidden_write_roots: list[str] = Field(default_factory=list)
    can_promote_artifacts: bool = False
    can_run_deploy_macros: bool = False

class ArtifactPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    require_logs: bool = True
    require_diff_report: bool = True
    require_summary_report: bool = True
    require_screenshots_for_visual_changes: bool = False
    required_artifact_kinds: list[str] = Field(default_factory=lambda: ["report"])
```

```python
# src/python/mcp_models.py
from pydantic import BaseModel, Field, ConfigDict

class MCPToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    server_name: str
    tool_name: str
    args: dict[str, str] = Field(default_factory=dict)
    request_id: str

class MCPToolError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    remediation: str | None = None

class MCPToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str
    success: bool
    data: dict[str, str] = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list)
    error: MCPToolError | None = None

class MCPServerSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str
    selected_servers: list[str] = Field(default_factory=list)
    selected_tools: list[str] = Field(default_factory=list)
    rationale: str

class MCPExecutionEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_name: str
    requests: list[MCPToolRequest] = Field(default_factory=list)
```

```python
# src/python/errors.py
from pydantic import BaseModel, Field, ConfigDict

class PolicyViolation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    policy_name: str
    rule_name: str
    message: str
    severity: str

class ValidationErrorReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    object_name: str
    success: bool
    violations: list[PolicyViolation] = Field(default_factory=list)

class CheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    check_name: str
    success: bool
    details: str

class CIGateReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workflow_name: str
    checks: list[CheckResult] = Field(default_factory=list)
    overall_success: bool

class PremergeReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    branch_name: str
    reports: list[CIGateReport] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    final_decision: str
```

---

## 6. Typed Macro Catalog (10)

### Design rules
Each macro must have:
- one primary purpose
- typed inputs
- typed outputs
- bounded side effects
- explicit risk level
- a fixture test
- a `when_not_to_use` note

### Catalog

#### 1. `fetch_document`
**Purpose:** retrieve a single document by identifier.  
**Risk:** low  
**Inputs:** `document_id`, `server_name`  
**Outputs:** document payload, metadata artifact  
**When not to use:** when you need discovery or search first.

#### 2. `search_documents`
**Purpose:** search indexed documents by keyword or filter.  
**Risk:** low  
**Inputs:** `query`, `limit`, `server_name`  
**Outputs:** ranked result list  
**When not to use:** when the exact document ID is already known.

#### 3. `sync_meeting_notes_to_tasks`
**Purpose:** read meeting notes and create downstream task objects.  
**Risk:** medium  
**Inputs:** `document_id`, `account_id`, `destination_server`  
**Outputs:** task creation report  
**When not to use:** when no action-item extraction rule exists.

#### 4. `deploy_container_with_redaction`
**Purpose:** deploy containerized artifacts with redacted logs and summaries.  
**Risk:** high  
**Inputs:** `compose_path`, `environment`, `service_name`  
**Outputs:** deployment report, redacted logs  
**When not to use:** when deploy approval is not granted.

#### 5. `extract_action_items_from_sources`
**Purpose:** read one or more sources and extract action items into structured output.  
**Risk:** medium  
**Inputs:** `source_ids`, `source_server`, `output_path`  
**Outputs:** action-item JSON artifact  
**When not to use:** when source quality is too poor for reliable extraction.

#### 6. `recommend_tools`
**Purpose:** discover and rank candidate tools for a task.  
**Risk:** low  
**Inputs:** `query`, `server_scope`  
**Outputs:** ranked tool recommendation set  
**When not to use:** when the exact tool is already known.

#### 7. `transform_file_safely`
**Purpose:** read, transform, validate, and write output to an approved path.  
**Risk:** medium  
**Inputs:** `input_path`, `transform_name`, `output_path`  
**Outputs:** transformed file, diff report  
**When not to use:** when the transform is undefined or unvalidated.

#### 8. `scaffold_from_contract`
**Purpose:** generate a bounded file/code scaffold from a validated contract.  
**Risk:** medium  
**Inputs:** `contract_path`, `template_name`, `target_root`  
**Outputs:** scaffold report, created files  
**When not to use:** when no contract exists.

#### 9. `promote_artifact`
**Purpose:** validate and promote a draft artifact to the next allowed state.  
**Risk:** medium  
**Inputs:** `artifact_path`, `current_state`, `target_state`  
**Outputs:** promotion report  
**When not to use:** when validation or approval prerequisites are unmet.

#### 10. `run_premerge_checks`
**Purpose:** execute the full pre-merge guardrail suite and emit a go/no-go report.  
**Risk:** low  
**Inputs:** `branch_name`, `workspace_root`  
**Outputs:** `PremergeReport`  
**When not to use:** never before merge.

---

## 7. Macro Schema

```yaml
name: string
description: string
runtime: python|node|deno|bun
risk_level: low|medium|high
input_schema_ref: string
output_schema_ref: string
tags:
  - string
when_not_to_use:
  - string
steps:
  - step_id: string
    kind: tool_call|transform|foreach
    tool_call:
      server_name: string
      tool_name: string
      args: { key: value }
    transform:
      transform_name: string
      args: { key: value }
    foreach:
      collection_name: string
      loop_var: string
      server_name: string
      tool_name: string
      args: { key: value }
```

### Example: `fetch_document.yaml`
```yaml
name: fetch_document
description: Retrieve a single document by identifier
runtime: python
risk_level: low
input_schema_ref: schemas/json/macro_run_request.schema.json
output_schema_ref: schemas/json/macro_run_result.schema.json
tags: [document, read, lookup]
when_not_to_use:
  - when a search is required first
steps:
  - step_id: fetch_doc
    kind: tool_call
    tool_call:
      server_name: google_drive
      tool_name: get_document
      args:
        document_id: "${document_id}"
```

---

## 8. Helper Script CLI Signatures

### `discover_tools`
```bash
python -m src.python.cli.discover_tools \
  --query "search google docs for meeting notes" \
  --server-scope google_drive,salesforce \
  --output json
```

### `describe_server`
```bash
python -m src.python.cli.describe_server \
  --server-name google_drive \
  --output json
```

### `create_task_stub`
```bash
python -m src.python.cli.create_task_stub \
  --task-name fetch-q1-notes \
  --objective "Read Q1 meeting notes and summarize action items" \
  --runtime python \
  --output-file tmp/fetch-q1-notes.request.json
```

### `validate_task`
```bash
python -m src.python.cli.validate_task \
  --request-file tmp/fetch-q1-notes.request.json \
  --execution-policy manifests/policies/default.execution.json \
  --mutation-policy manifests/policies/default.mutation.json \
  --selection-policy manifests/policies/default.selection.json
```

### `run_task`
```bash
python -m src.python.cli.run_task \
  --request-file tmp/fetch-q1-notes.request.json \
  --workspace-root . \
  --output-file reports/fetch-q1-notes.result.json
```

### `run_macro`
```bash
python -m src.python.cli.run_macro \
  --macro-file macros/fetch_document.yaml \
  --args-file schemas/examples/fetch_document.request.json \
  --workspace-root . \
  --output-file reports/fetch_document.result.json
```

### `explain_error`
```bash
python -m src.python.cli.explain_error \
  --error-file reports/fetch_document.result.json \
  --output markdown
```

### `validate_manifest`
```bash
python -m src.python.cli.validate_manifest \
  --manifest-file manifests/servers/google_drive.server.json
```

### `export_json_schemas`
```bash
python -m src.python.cli.export_json_schemas \
  --output-dir schemas/json
```

### `summarize_ci`
```bash
python -m src.python.cli.summarize_ci \
  --reports-dir reports/ci \
  --output-file reports/ci/premerge-summary.json
```

---

## 9. MCP Request/Response Schema Set

### Request layer
- `MCPToolRequest`
- `MCPExecutionEnvelope`
- `AgentTaskRequest`
- `MacroRunRequest`

### Response layer
- `MCPToolResult`
- `MCPToolError`
- `AgentTaskResult`
- `MacroRunResult`
- `ExecutionSummary`
- `ValidationErrorReport`
- `PremergeReport`

### JSON schemas exported
- `agent_task_request.schema.json`
- `agent_task_result.schema.json`
- `macro_definition.schema.json`
- `macro_run_request.schema.json`
- `macro_run_result.schema.json`
- `mcp_tool_request.schema.json`
- `mcp_tool_result.schema.json`
- `server_manifest.schema.json`
- `execution_policy.schema.json`
- `mutation_policy.schema.json`
- `selection_policy.schema.json`
- `redaction_policy.schema.json`
- `approval_policy.schema.json`
- `ownership_policy.schema.json`
- `artifact_policy.schema.json`

---

## 10. 7-Policy Schema Pack

### 1. `ExecutionPolicy`
Controls runtime behavior:
- network access
- subprocess use
- write permissions
- blocked imports
- runtime limits
- tool-call limits

### 2. `MutationPolicy`
Controls what may change:
- create/update/delete permissions
- write roots
- forbidden roots
- contract requirements
- promotion prerequisites
- bulk-change caps

### 3. `SelectionPolicy`
Controls what may be chosen:
- allowed/blocked servers
- allowed/blocked tools
- allowed/blocked macros
- default policy decision

### 4. `RedactionPolicy`
Controls output safety:
- redact PII
- redact secrets/tokens
- redact emails
- account-id handling
- replacement text

### 5. `ApprovalPolicy`
Controls human gatekeeping:
- default approval level
- high-risk approval
- delete approval
- deploy approval
- bulk-change approval

### 6. `OwnershipPolicy`
Controls write authority:
- role name
- allowed roots
- forbidden roots
- promotion rights
- deploy rights

### 7. `ArtifactPolicy`
Controls required evidence:
- logs
- diff reports
- summary reports
- screenshots for visual changes
- required artifact kinds

---

## 11. GitHub Actions Workflow Map

### `ci.yml`
Runs the baseline repo checks:
- install dependencies
- lint
- type check
- unit tests

### `schemas.yml`
Runs schema-specific checks:
- export JSON schemas
- compare committed vs generated schemas
- validate schema examples

### `macros.yml`
Runs macro-specific checks:
- validate all macro YAML files
- run macro fixture tests
- compare macro outputs to golden files

### `policies.yml`
Runs policy-specific checks:
- validate policy JSON files
- enforce policy example coverage
- run policy-engine tests

### `manifests.yml`
Runs manifest checks:
- validate all server manifests
- enforce tool schema references exist
- ensure example coverage

### `smoke.yml`
Runs integration/smoke checks:
- run task execution fixture
- run macro execution fixture
- emit smoke artifacts

### `docs.yml`
Runs docs checks:
- markdown lint
- validate CLI snippets against help output
- ensure docs reference existing files

### `release.yml`
Runs release packaging:
- tag validation
- changelog presence
- build Python and TS packages
- upload release artifacts

---

## 12. CI Checks for Each New Layer

### Contracts layer
- Pydantic model import test
- JSON schema export test
- strict example validation
- mypy/pyright coverage

### Macro layer
- YAML schema validation
- macro fixture execution
- golden-file comparison
- duplicate-name check
- forbidden-step-pattern check

### Policy layer
- default policy files validate
- policy-engine rule tests
- deny/warn/allow branch coverage
- approval escalation tests

### MCP schema layer
- request/response validation
- round-trip serialization test
- error envelope coverage
- tool manifest reference checks

### Helper CLI layer
- `--help` output test
- exit code behavior test
- invalid-input behavior test
- output file emission test

### Manifest layer
- schema validation
- tool uniqueness check
- broken schema reference check
- tag presence check

### Docs layer
- snippet/file existence check
- stale path detection
- naming standard conformance check

---

## 13. CI Gate Order

### Recommended gate order
1. **lint + formatting**
2. **type checking**
3. **Pydantic model import tests**
4. **JSON schema export + diff check**
5. **manifest validation**
6. **policy validation**
7. **macro validation**
8. **unit tests**
9. **integration tests**
10. **smoke execution**
11. **artifact verification**
12. **docs checks**
13. **premerge summary generation**

### Premerge blocker rules
Block merge if any of these fail:
- type check
- schema drift check
- manifest validation
- macro validation
- policy validation
- integration/smoke
- artifact presence for required workflows

---

## 14. GitHub Actions Branch and PR Strategy

### Required status checks
Require these checks on protected branches:
- `ci / lint-and-types`
- `schemas / validate`
- `manifests / validate`
- `policies / validate`
- `macros / validate`
- `smoke / integration`
- `docs / validate`

### PR template sections
- summary
- changed layers
- policy impact
- macro impact
- schema impact
- artifacts attached
- premerge report link

### Merge discipline
No merge without:
- passing required checks
- generated premerge summary
- no unresolved high-severity policy violations

---

## 15. Example GitHub Actions Map

### `ci.yml`
```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]
jobs:
  lint-and-types:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: ruff check .
      - run: mypy src/python
```

### `schemas.yml`
```yaml
name: schemas
on:
  pull_request:
  push:
    branches: [main]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: python -m src.python.cli.export_json_schemas --output-dir schemas/json
      - run: git diff --exit-code schemas/json
```

### `macros.yml`
```yaml
name: macros
on:
  pull_request:
  push:
    branches: [main]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pytest tests/unit/test_macros.py tests/integration/test_run_macro.py
```

---

## 16. RepoReady v1.1 Patch Plan

### Phase 1 — Model foundation
**Add:**
- `contracts.py`
- `macros.py`
- `policies.py`
- `mcp_models.py`
- `manifests.py`
- `enums.py`
- `errors.py`

**Exit criteria:**
- all models import cleanly
- mypy passes
- JSON schemas export cleanly

### Phase 2 — CLI and helper layer
**Add:**
- `discover_tools`
- `describe_server`
- `create_task_stub`
- `validate_task`
- `run_task`
- `run_macro`
- `explain_error`
- `validate_manifest`
- `export_json_schemas`
- `summarize_ci`

**Exit criteria:**
- every CLI has `--help`
- invalid input exits non-zero
- output artifacts created where required

### Phase 3 — Macro catalog
**Add:**
- 10 macro YAML files
- macro schema docs
- macro tests
- macro fixtures

**Exit criteria:**
- all macros validate
- fixtures pass
- no duplicate names

### Phase 4 — Policy pack
**Add:**
- 7 policy JSON defaults
- policy-engine tests
- policy docs

**Exit criteria:**
- policy JSON validates
- deny/warn/allow logic covered by tests

### Phase 5 — CI/CD guardrails
**Add:**
- 8 GitHub Actions workflows
- PR template
- premerge summary generation
- release packaging checks

**Exit criteria:**
- required checks green
- premerge report generated on PRs

### Phase 6 — Docs and examples
**Add:**
- agent quickstart
- helper CLI docs
- naming standard
- schema examples
- server manifest spec

**Exit criteria:**
- doc paths valid
- snippets align with CLI help

---

## 17. Macro Catalog Summary Table

| Macro | Purpose | Risk | Primary Output |
|---|---|---:|---|
| `fetch_document` | Retrieve one document | low | document payload |
| `search_documents` | Search document corpus | low | ranked search result |
| `sync_meeting_notes_to_tasks` | Convert notes to tasks | medium | task creation report |
| `deploy_container_with_redaction` | Deploy with safe logs | high | deployment report |
| `extract_action_items_from_sources` | Extract actions from inputs | medium | action-items JSON |
| `recommend_tools` | Rank candidate tools | low | recommendation report |
| `transform_file_safely` | Read-transform-write safely | medium | transformed file + diff |
| `scaffold_from_contract` | Build scaffold from spec | medium | scaffold report |
| `promote_artifact` | Move artifact to next state | medium | promotion report |
| `run_premerge_checks` | Run all merge gates | low | `PremergeReport` |

---

## 18. Makefile Command Map

```make
.PHONY: validate typecheck schemas manifests macros policies smoke premerge

validate:
	python -m src.python.cli.validate_manifest --manifest-file manifests/servers/google_drive.server.json

typecheck:
	mypy src/python

schemas:
	python -m src.python.cli.export_json_schemas --output-dir schemas/json

manifests:
	pytest tests/unit/test_manifests.py

macros:
	pytest tests/unit/test_macros.py tests/integration/test_run_macro.py

policies:
	pytest tests/unit/test_policies.py tests/integration/test_policy_engine.py

smoke:
	pytest tests/integration/test_run_task.py tests/integration/test_run_macro.py

premerge:
	python -m src.python.cli.summarize_ci --reports-dir reports/ci --output-file reports/ci/premerge-summary.json
```

---

## 19. Final Assessment

This v1.1 patch is meaningful because it does not add random abstractions. It adds:

- typed contracts
- typed macros
- typed policies
- typed MCP envelopes
- obvious helper CLIs
- schema export and validation
- CI gates for each layer

That is the correct shape for an agent-usable filesystem-MCP workflow.

The stack becomes easier for both humans and models because the interaction surface is now:
- named consistently
- validated explicitly
- documented concretely
- enforced automatically

That is the high-VCR path.

