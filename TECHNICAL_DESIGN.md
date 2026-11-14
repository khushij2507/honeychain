# Technical Design Document

## 1. Purpose
Deliver a working demonstration of honey batch provenance and smart-apiary monitoring aligned to the Honey Chain problem statement. The system is designed to demonstrate a credible end-to-end workflow without misrepresenting prototype features as production-grade blockchain or AI.

## 2. Requirements traceability

| Problem-statement requirement | MVP implementation | Status / caveat |
|---|---|---|
| Honey batch traceability | Batch records and timeline | Implemented |
| QR consumer authentication | QR PNG endpoint points to public verification route | Label printing and anti-counterfeit seal are future work |
| Secure batch tracking | Hash-linked ledger and integrity API | Tamper-evident only; no distributed consensus |
| IoT live monitoring | Sensor ingestion API and telemetry page/API | API implemented; no physical hardware integration |
| Disease detection | Environmental heuristic flags unusual averages | Not disease detection; requires labelled field data |
| Productivity prediction | Hive weight is captured | Prediction model not included pending dataset |
| Scalable deployment | Separation of Flask routes, SQLite schema, APIs | Prototype only; production architecture described in roadmap |
| Rural beekeeper access | Responsive, low-complexity interface | Localization/offline support future work |

## 3. Roles
- **Beekeeper:** register harvest batches and record origin details.
- **Cooperative/quality operator:** add quality, packing, storage and dispatch events.
- **Consumer:** read batch provenance without editing records.
- **Device/gateway:** submit authenticated telemetry in a future deployment.
- **Platform administrator:** manage users and infrastructure (RBAC not yet implemented).

## 4. Functional requirements
1. Create a batch with unique code and required origin fields.
2. Automatically add a “Batch created” event.
3. Add approved event types with actor, location, notes and timestamp.
4. Display current batch status and chronological event history.
5. Render a read-only consumer verification page.
6. Recalculate and verify the hash chain.
7. Accept telemetry with basic range validation.
8. Summarize recent sensor readings using an explicitly labelled heuristic.
9. Export ledger events to CSV.
10. Expose a health endpoint for simple uptime checks.

## 5. Non-functional requirements
- **Usability:** responsive layouts, plain labels and simple forms.
- **Integrity:** canonical serialization and SHA-256 event hashes.
- **Maintainability:** small Flask application and standard-library SQLite.
- **Portability:** Python 3.10+ and one dependency.
- **Transparency:** demo data and heuristic limits are disclosed in the UI/docs.
- **Security:** prototype limitations are explicit; production controls are a release gate.

## 6. Data model
### batches
`id` primary key; `batch_code` unique; beekeeper, apiary, floral source, harvest date, quantity, optional moisture, status, created timestamp.

### events
`id` primary key; foreign key batch code; event type; actor; location; JSON details; UTC timestamp; previous hash; event hash unique.

### telemetry
`id` primary key; apiary; temperature °C; humidity percent; hive weight kg; recorded timestamp.

## 7. Integrity design
The event hash is computed as:
`SHA256(canonical_json(batch_code, event_type, actor, location, details, created_at, prev_hash))`.

`prev_hash` points to the preceding event in global ledger order. Integrity verification checks both the previous pointer and the recalculated hash. Changing a record should cause verification to fail unless all subsequent records are rewritten. Since this is one SQLite database, a privileged attacker can rewrite all records and hashes; external anchoring or signed events are required for stronger trust.

## 8. Environmental indicator
The demo calculates the mean of up to 20 most recent telemetry rows. It raises an “Elevated” indicator if mean temperature is outside 20–36 °C or mean humidity outside 35–80%. These are placeholder demo thresholds, not species-specific validated thresholds. The result is advisory only and is not a disease classifier.

## 9. Error handling
- Duplicate batch code: SQLite uniqueness constraint and user-facing message.
- Invalid batch form: redirect with validation message.
- Unknown batch: HTTP 404 page.
- Invalid telemetry payload: HTTP 400 JSON error.
- Hash-chain mismatch: API/UI reports the first broken event.
- Missing telemetry: neutral “No data” indicator.

## 10. Deployment target
For a pilot, use a managed Linux service, Gunicorn or another production WSGI server, PostgreSQL, TLS termination, environment-managed secrets, backups, monitoring and a migration system. Add authentication and authorization before exposing write routes publicly. Do not run Flask's development server or debug mode in production.
