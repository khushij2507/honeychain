import os, tempfile, unittest
from app import app, init_db

class HoneyChainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        os.environ["HONEYCHAIN_DB"] = self.tmp.name
        # app.DB_PATH is resolved at import; patch it for this isolated test.
        import app as honey_app
        self.old_path = honey_app.DB_PATH
        honey_app.DB_PATH = self.tmp.name
        with honey_app.db() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS batches(id INTEGER PRIMARY KEY AUTOINCREMENT,batch_code TEXT UNIQUE NOT NULL,
            beekeeper TEXT NOT NULL,apiary TEXT NOT NULL,floral_source TEXT NOT NULL,harvest_date TEXT NOT NULL,
            quantity_kg REAL NOT NULL,moisture_pct REAL,status TEXT NOT NULL DEFAULT 'Harvested',created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,batch_code TEXT NOT NULL,event_type TEXT NOT NULL,
            actor TEXT NOT NULL,location TEXT NOT NULL,details TEXT NOT NULL,created_at TEXT NOT NULL,prev_hash TEXT NOT NULL,
            event_hash TEXT UNIQUE NOT NULL,FOREIGN KEY(batch_code) REFERENCES batches(batch_code));
            CREATE TABLE IF NOT EXISTS telemetry(id INTEGER PRIMARY KEY AUTOINCREMENT,apiary TEXT NOT NULL,temperature_c REAL NOT NULL,
            humidity_pct REAL NOT NULL,hive_weight_kg REAL NOT NULL,recorded_at TEXT NOT NULL);
            """)
        self.client = app.test_client()

    def tearDown(self):
        import app as honey_app
        honey_app.DB_PATH = self.old_path
        try: os.unlink(self.tmp.name)
        except OSError: pass

    def test_health(self):
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_create_batch_and_verify(self):
        response = self.client.post("/batch/new", data={
            "batch_code":"TEST-001","beekeeper":"Test Keeper","apiary":"Test Apiary",
            "floral_source":"Mustard","harvest_date":"2026-10-28","quantity_kg":"10","moisture_pct":"17.5"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"TEST-001", response.data)
        self.assertEqual(self.client.get("/admin/verify-chain").json["valid"], True)

    def test_telemetry_validation(self):
        bad = self.client.post("/api/telemetry", json={"apiary":"X","temperature_c":999,"humidity_pct":50,"hive_weight_kg":1})
        self.assertEqual(bad.status_code, 400)
        good = self.client.post("/api/telemetry", json={"apiary":"X","temperature_c":31,"humidity_pct":50,"hive_weight_kg":1})
        self.assertEqual(good.status_code, 201)

if __name__ == "__main__":
    unittest.main()
