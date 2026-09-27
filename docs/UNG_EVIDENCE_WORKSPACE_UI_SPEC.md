# UNG Case / Evidence Workspace — implementation specification

Integrate into the existing UNG interface and JANUS identity model.

Views: Case Overview; Evidence Inventory + hash/integrity status; Artifact Browser; Search/Filters; Timeline; Message/Thread Viewer; Media Browser; Relationship Graph; Correlations/Anomalies; Sensitive Data Review; Audit Trail; Reports/Exports.

Every finding must link back to source_ref and show whether it is observed evidence, parser interpretation, or derived analysis. Default previews redact verification codes, recovery codes, passwords, tokens and keys. Privileged reveal/export actions require JANUS authorization and generate audit/event records.

NEXUS/PULSAR event contracts use the allowlisted evidence events in cad_core/evidence_access.py. Source evidence is read-only; previews, thumbnails, indexes, reports and graph products are derivatives. The UI must show parser failures and limitations rather than silently hiding unsupported artifacts.

The workspace analyzes already-authorized evidence and does not implement device-lock bypass, credential interception, encryption defeat or covert acquisition.
