# Security & Trust Threat Model

## Assets
Batch identity and provenance, event history, beekeeper identity, sensor readings, consumer confidence, platform credentials.

## Threats and mitigations
- **Forged batch/label:** unique batch codes, QR destination and event history help verification; production needs tamper-evident packaging, code revocation and duplicate-scan monitoring.
- **Edited event row:** hash recalculation detects ordinary row edits; production needs signed events and external ledger-root anchoring.
- **Whole-database rewrite:** not prevented by local hash chain; mitigate with independent backups, externally published signed checkpoints or a permissioned multi-organization ledger.
- **Fake sensor data:** prototype API is unauthenticated; production needs per-device credentials, signatures, sequence numbers, replay defense and anomaly checks.
- **Unauthorized batch updates:** no login/roles in MVP; do not expose write routes publicly until authentication and authorization are implemented.
- **Personal data exposure:** public verification should disclose only necessary batch-level details; do not publish private contact details or exact sensitive apiary coordinates.
- **Web attacks:** add CSRF protection, rate limiting, secure cookies, dependency scanning and HTTPS before deployment.
- **False AI claims:** current insight is rule-based only; clearly label it and require field validation before using predictive outputs.

## Release blockers for public deployment
1. Authentication and role-based authorization.
2. CSRF protection and secure cookie configuration.
3. Authenticated telemetry ingestion.
4. HTTPS and production WSGI hosting.
5. Backup/restore test and external ledger anchoring.
6. Privacy notice, data retention policy and operational owner.
7. Field validation and review of all agricultural thresholds.
