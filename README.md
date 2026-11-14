# Honey Chain — Traceability & Smart Beekeeping MVP

**Problem statement:** Honey Chain is a prototype for blockchain-inspired honey traceability and smart beekeeping management. It provides batch-level provenance, consumer verification, a tamper-evident hash-linked event log, and a starter environmental-monitoring insight.

> **Honest scope note:** This is a runnable MVP, not a production blockchain network, certified food-safety system, or trained disease-detection model. It uses a local SQLite database and a SHA-256 hash chain to demonstrate verifiable record linking. The smart-beekeeping indicator is a transparent rule-based heuristic. These boundaries are intentional and documented.

## What is included

- Beekeeper dashboard and batch registration.
- Batch profile with floral source, origin/apiary, harvest date, quantity and optional moisture reading.
- Traceability events for quality checks, packing, dispatch, retail receipt and storage inspections.
- Consumer-facing verification page at `/verify/<BATCH_CODE>`.
- Append-only-style event history with SHA-256 hashes linked to the previous event.
- Integrity-check endpoint that recomputes the chain and flags changed or broken links.
- Telemetry API for temperature, humidity and hive-weight readings.
- Transparent rule-based environment indicator and JSON API.
- CSV export of the event ledger.
- Seed data to make the demo usable immediately.
- Detailed architecture, API, security, testing and deployment documentation.

## Quick start

Requires Python 3.10+.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the app
python app.py
```

Open **http://127.0.0.1:5000**. The first run creates `honeychain.db` and seeds three demo batches and sample telemetry. Demo data is clearly fictional and should be replaced before any real deployment.

Optional environment variables:
- `HONEYCHAIN_DB`: custom SQLite database path.
- `SECRET_KEY`: strong random secret for Flask sessions.
- `PORT`: port (default `5000`).
- `DEBUG=1`: enable Flask debug mode for local development only. Never enable debug mode in production.

## User journeys

### 1. Register a honey batch
Use the dashboard form to provide a unique batch code, beekeeper, apiary/cluster, floral source, harvest date and quantity. An initial traceability event is added automatically.

### 2. Record custody and quality events
Open a batch and add a quality check, packing, dispatch, retail receipt or storage inspection. Each event records the actor, location, timestamp, notes and cryptographic link to the preceding ledger event.

### 3. Consumer verification
Open `/verify/HC-2026-001` (or another batch code). A QR label can point to this URL. The page displays the recorded origin details, status and journey history. The QR image endpoint is `/batch/<BATCH_CODE>/qr.png`. It uses the request host to create the verification URL, so use the public HTTPS domain when deployed. Print a tamper-evident seal alongside the QR.

### 4. Submit hive sensor data
Send a JSON POST to `/api/telemetry`:

```bash
curl -X POST http://127.0.0.1:5000/api/telemetry \
  -H "Content-Type: application/json" \
  -d '{"apiary":"Sirmaur Cluster A","temperature_c":33.2,"humidity_pct":67,"hive_weight_kg":19.4}'
```

Read latest sensor records at `GET /api/telemetry` and the basic indicator at `GET /api/insights`.

### 5. Check ledger integrity
Open `/admin/verify-chain`. It returns `valid: true` when the event hashes and previous-hash links all match.

### 6. Export the ledger
Click **Export ledger** or request `/export/events.csv`.

## API reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Dashboard, batches, monitoring summary |
| POST | `/batch/new` | Create batch and initial event |
| GET | `/batch/<batch_code>` | Internal batch details and event history |
| POST | `/batch/<batch_code>/event` | Append a custody/quality event |
| GET | `/verify/<batch_code>` | Consumer verification page |
| GET | `/api/telemetry` | Latest 100 sensor records as JSON |
| POST | `/api/telemetry` | Ingest one sensor reading |
| GET | `/api/insights` | Rule-based environmental indicator |
| GET | `/admin/verify-chain` | Verify ledger links and event hashes |
| GET | `/export/events.csv` | Download event ledger as CSV |
| GET | `/health` | Lightweight health check |

### Telemetry request schema

```json
{
  "apiary": "Sirmaur Cluster A",
  "temperature_c": 33.2,
  "humidity_pct": 67,
  "hive_weight_kg": 19.4
}
```

Validation bounds are deliberately broad sanity checks: temperature -20..70 °C, relative humidity 0..100%, and non-negative hive weight. They are not biological safety thresholds.

## Architecture

```text
Beekeeper / Admin browser        Consumer browser / QR scan
            |                               |
            +----------- Flask web app ------+
                            |
             +--------------+---------------+
             |              |               |
          Batches       Event ledger     Telemetry
          (SQLite)    (SHA-256 chain)     (SQLite)
             |              |               |
             +------ Dashboard / APIs ------+
                            |
                 Rule-based environment
                     indicator (demo)
```

### Core entities

- **Batch:** unique batch code, beekeeper, apiary, floral source, harvest date, quantity, moisture (optional), current status.
- **Event:** batch code, event type, actor, location, details, UTC timestamp, previous hash and event hash.
- **Telemetry:** apiary, temperature, humidity, hive weight and timestamp.

### Hash-chain model

Each event hash is SHA-256 over a canonical JSON representation of its fields, including the `prev_hash`. The first event points to `GENESIS`; each subsequent event points to the previous ledger event's hash. Verification recomputes every hash and checks every link.

This is **tamper-evident, not tamper-proof**. A database administrator who can rewrite the entire database can recompute the chain. A production design should anchor periodic ledger roots outside the application database, use role-based signing keys, and/or replicate events to an independently operated permissioned blockchain.

## Smart beekeeping: current and future model

The current environment indicator averages the latest 20 sensor readings. It flags the readings as elevated if average temperature falls outside the demo range 20–36 °C or average humidity falls outside 35–80%. The UI explicitly labels this as a rule-based demo. The ranges are placeholders, not veterinary advice or validated colony-health thresholds.

A genuine disease-detection or productivity-prediction module needs:
1. A labelled dataset from the target region and species/management system.
2. Features such as time-series temperature/humidity, hive-weight trend, acoustic data, inspection findings, season, forage availability and treatment history.
3. A target label defined with an apiculture expert (e.g. confirmed disease class, colony loss, or measured yield).
4. Train/validation/test split by hive or beekeeper—not random rows from the same hive—to avoid leakage.
5. Baseline comparisons, class-imbalance handling, calibration, uncertainty and field validation.
6. Human review and clear “decision support, not diagnosis” wording.

Do not present the current heuristic as AI or use it to prescribe treatment.

## QR consumer verification

The consumer page is designed to be the destination for a batch QR code. In production:
- Deploy behind HTTPS on a stable domain.
- Generate one QR per batch containing the full public URL, e.g. `https://example.org/verify/HC-2026-001`.
- Print the batch code and a tamper-evident seal alongside the QR.
- Avoid exposing personal phone numbers, precise private apiary coordinates or sensitive commercial data.
- Add revocation and reprint controls so counterfeit labels can be investigated.

## Security and privacy checklist before deployment

This prototype is for local demonstration. Before real-world use:
- Add authentication, roles and organization-level authorization.
- Add CSRF protection to forms, rate limits, secure cookie settings and server-side input validation.
- Use HTTPS, production WSGI server, secret management and backups.
- Use database migrations, audit logging, monitoring and restore drills.
- Sign events with organization-held keys and anchor ledger checkpoints externally.
- Restrict telemetry ingestion to authenticated devices, with per-device credentials and replay protection.
- Minimize personal data and document consent/retention policy.
- Conduct security review and field testing with beekeeper groups.
- Treat all seed records as synthetic; do not use for product claims or regulatory certification.

## Known limitations

- Single-server SQLite; not designed for concurrent large-scale deployments.
- No login/roles or permissioned blockchain consensus.
- No built-in QR image generation or label printing.
- No lab certificate integration, batch recall workflow, or offline-first mobile mode.
- Rule-based indicator only; no trained disease or yield model.
- No IoT hardware driver; sensor values are posted through the documented API.
- No claim of compliance with any specific food, export, or traceability standard.

## Suggested production roadmap

**Phase 1 — Pilot readiness:** authentication/RBAC, QR generation, form validation, audit log, PostgreSQL, tests and HTTPS deployment.

**Phase 2 — Trust layer:** event signatures, externally anchored daily Merkle roots, partner onboarding, lab certificates and recall workflow.

**Phase 3 — IoT:** ESP32/LoRaWAN gateway, device registry, authenticated ingestion, offline buffering, sensor calibration and alerts.

**Phase 4 — AI validation:** collect expert-labelled longitudinal data, establish baselines, train/evaluate models, field trial and human-in-the-loop review.

**Phase 5 — Scale:** multi-language consumer page, low-bandwidth mode, cooperative analytics, export integrations and operational monitoring.

## Demo acceptance checklist

- [ ] Dashboard opens and shows three sample batches.
- [ ] New batch can be created with a unique code.
- [ ] Duplicate batch codes are rejected.
- [ ] Batch event can be appended and status updated.
- [ ] Consumer verification page shows the recorded journey.
- [ ] `/admin/verify-chain` returns valid on untouched data.
- [ ] Valid telemetry POST returns HTTP 201.
- [ ] Invalid telemetry is rejected with HTTP 400.
- [ ] CSV export downloads event rows.
- [ ] Production deployment has authentication and HTTPS (not included in MVP).

## License and use

Educational demonstration scaffold. Review, test and adapt it before production or commercial use.
