# UNG Authorized Device Forensics & Evidence Analysis

Status: approved shared capability. Integrate into the existing UNG security/data fabric and analytics stack; do not create a duplicate standalone system.

## Scope and authorization boundary
- Analyze only devices, backups, exports, images, archives, or account data the operator is authorized to possess and examine.
- Do not implement lock bypass, credential theft, covert collection, authentication-code interception, or encryption defeat.
- Require case/work-order identity, operator identity, source identity, acquisition timestamp, and authorization basis before ingestion.
- Preserve original evidence read-only; derived artifacts are versioned separately.
- Sensitive secrets (verification codes, recovery codes, tokens, passwords, private keys) are classified and redacted from ordinary dashboards by default.

## Ingestion and normalization
Support authorized forensic exports/backups and structured evidence packages containing:
- messages and message metadata
- call records
- contacts/account records
- photos/video and metadata
- application artifacts
- Wi-Fi/network records
- browser/history artifacts when present
- files/documents
- system/device events
- location metadata when legitimately present in the source
- deleted/recovered records only when actually present in the acquired evidence

Normalize into the shared UNG data model with immutable source references and confidence/provenance fields. Never infer that a missing artifact was deleted or that an unsupported tool recovered it.

## Evidence integrity and chain of custody
- Cryptographic hashes for source evidence and every derived export.
- Immutable append-only audit events for acquisition, import, parsing, transformation, review, export, and access.
- Case ID / evidence ID / source ID / examiner ID / timestamps.
- Original-file metadata preservation.
- Hash verification on open, transfer, and export.
- Tamper-evident manifest and signed evidence package support where infrastructure permits.
- Complete provenance from dashboard finding back to source artifact and parser/version.
- Reproducible transformation logs.

## Analytics
Use the existing shared analytics core for:
- event/timeline reconstruction
- cross-artifact correlation
- full-text and fielded search
- duplicate/near-duplicate detection
- cryptographic/media hashing
- metadata extraction
- relationship/contact/event graphs
- clustering and anomaly/outlier detection
- conversation/thread reconstruction
- attachment-to-message linkage
- device/account/network correlation
- geotemporal correlation where authorized data supports it
- deleted-record identification when explicitly marked by the source parser
- confidence scoring and contradiction flags
- visual timelines, graphs, heatmaps and evidence dashboards

Separate observed facts from derived analysis. Every analytical conclusion must retain source links and method metadata.

## Media handling
- Hash originals before processing.
- Extract EXIF/container metadata without altering source files.
- Generate thumbnails/previews as derived data.
- Detect exact duplicates and optional perceptual near-duplicates.
- Maintain parent/derivative relationships.
- Record parser/codec failures rather than silently dropping media.

## Sensitive-data controls
- Automatic detection/redaction classes for OTP/verification codes, recovery codes, passwords, tokens, keys, payment data and other designated secrets.
- Role-based reveal workflow for authorized reviewers.
- Export policies that can omit or mask sensitive values.
- Audit every reveal/export of sensitive material.
- Retention/deletion controls must follow the parent case/work-order policy.

## JANUS integration
JANUS owns:
- examiner identity
- MFA
- role/attribute-based access
- case membership
- privileged reveal/export approvals
- session/audit attribution

## NEXUS / PULSAR integration
Publish normalized evidence and analysis events through existing event/streaming infrastructure:
- evidence imported
- hash verified/failed
- parser completed/failed
- sensitive artifact detected
- timeline updated
- correlation created
- report/export generated
- access/reveal events

## Shared analytics/data-fabric integration
Store normalized artifacts in the existing UNG data fabric rather than a new silo. Use existing graph, anomaly, clustering, search, timeline, model-validation and visualization capabilities. Preserve source-level provenance through all transforms.

## Reporting
Generate reproducible reports containing:
- case/evidence identifiers
- source hashes
- acquisition/import metadata
- parser/tool versions
- findings with source references
- timeline excerpts
- graph/correlation summaries
- redaction state
- limitations/failed parsers/missing fields
- report hash and export timestamp

Reports must distinguish direct evidence, parser interpretation, and analyst/algorithmic inference.

## Operational safeguards
- Default read-only source handling.
- Sandbox parsers for untrusted evidence files.
- File-size/type limits and resource quotas.
- Malware scanning hooks where supported.
- No automatic execution of extracted binaries/scripts.
- Parser fuzz/error logging.
- Quarantine malformed/corrupt artifacts without discarding originals.

## Mobile-device context
This capability may process authorized mobile-device evidence from iOS/Android forensic exports or backups, but the platform does not claim that all phones expose the same artifacts. Availability depends on device state, OS version, acquisition method, tool capability, encryption state and source permissions.

## UI
Add a case/evidence workspace inside the existing UNG interface:
- evidence inventory
- integrity/hash status
- artifact browser
- timeline
- message/thread viewer
- media browser
- graph/correlation view
- search/filter
- sensitive-data/redaction controls
- audit trail
- report/export panel

Do not expose authentication secrets in default previews.
