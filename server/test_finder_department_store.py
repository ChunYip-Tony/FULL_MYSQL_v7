import hashlib
import json
import threading
import unittest
from unittest.mock import patch

from fastapi import HTTPException
import asyncio
import httpx

class TestClient:
    def __init__(self, app):
        self.app = app
    def request(self, method, path, **kwargs):
        async def send():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test") as client:
                return await client.request(method, path, **kwargs)
        return asyncio.run(send())
    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)
    def put(self, path, **kwargs):
        return self.request("PUT", path, **kwargs)
from finder_department_store import create_app, validate_state, install_department_store
from fastapi import FastAPI


class MemoryStore:
    """API contract fixture; does not stand in for a real MySQL integration test."""
    def __init__(self):
        self.values = {}
        self.lock = threading.Lock()
        self.commits = 0

    def get(self, department):
        if department not in self.values:
            raise HTTPException(404, "not imported")
        return self.values[department]

    def put(self, department, raw, data, expected):
        with self.lock:
            digest = hashlib.sha256(raw).hexdigest()
            previous = self.values.get(department, (None, None))[1]
            if previous == digest:
                return digest, True
            if previous != expected:
                raise HTTPException(409, "conflict")
            self.values[department] = raw, digest
            self.commits += 1
            return digest, False


def state(revision="r1", **extra):
    return {"revision": revision, "items": [{"upc": "000012345678", "cost": None, "name": "海鮮"}],
            "files": [], "movements": [], "posEvents": [], "priceEvents": [], "ohSnapshots": [], **extra}


class DepartmentStateAPI(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict("os.environ", {"FINDER_STORE_TOKEN_MEAT": "m" * 48,
                                            "FINDER_STORE_TOKEN_PRODUCE": "p" * 48})
        self.env.start()
        self.store = MemoryStore()
        self.client = TestClient(create_app(self.store))

    def tearDown(self):
        self.env.stop()

    def write(self, payload, department="meat", etag=None, **headers):
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        h = {"Authorization": "Bearer " + ("m" if department == "meat" else "p") * 48,
             "Content-Type": "application/json", "X-Content-SHA256": hashlib.sha256(raw).hexdigest(),
             **({"If-Match": etag} if etag else {"If-None-Match": "*"}), **headers}
        return self.client.put(f"/v1/departments/{department}/state", content=raw, headers=h)

    def test_liveness_does_not_touch_database(self):
        with patch.object(self.store, "get", side_effect=RuntimeError("offline")):
            self.assertEqual(self.client.get("/healthz").status_code, 200)

    def test_production_install_is_disabled_without_explicit_flag(self):
        parent = FastAPI()
        with patch.dict("os.environ", {"FINDER_DEPARTMENT_STORE_ENABLED": "0"}):
            self.assertFalse(install_department_store(parent, self.store))
        self.assertEqual(TestClient(parent).get("/v1/departments/meat/state").status_code, 404)

    def test_enabled_install_is_idempotent_and_preserves_existing_liveness(self):
        parent = FastAPI()
        parent.add_api_route("/healthz", lambda: {"service": "seafood"})
        with patch.dict("os.environ", {"FINDER_DEPARTMENT_STORE_ENABLED": "1"}):
            self.assertTrue(install_department_store(parent, self.store))
            count = len(parent.routes)
            self.assertTrue(install_department_store(parent, self.store))
            self.assertEqual(len(parent.routes), count)
        client = TestClient(parent)
        self.assertEqual(client.get("/healthz").json(), {"service": "seafood"})
        self.assertEqual(client.get("/v1/departments/meat/state").status_code, 401)

    def test_department_credentials_are_isolated(self):
        self.write(state())
        response = self.client.get("/v1/departments/meat/state", headers={"Authorization": "Bearer " + "p" * 48})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get("/v1/departments/seafood/state").status_code, 404)

    def test_full_state_preserves_unknown_history_null_zero_and_leading_zeros(self):
        value = state(customHistory=[{"quantity": 0, "missing": None}], department="meat")
        saved = self.write(value)
        self.assertEqual(saved.status_code, 200)
        got = self.client.get("/v1/departments/meat/state", headers={"Authorization": "Bearer " + "m" * 48})
        self.assertEqual(got.json(), value)
        self.assertEqual(got.headers["etag"], '"' + hashlib.sha256(got.content).hexdigest() + '"')

    def test_lost_commit_reply_is_idempotent(self):
        self.write(state())
        replay = self.write(state())
        self.assertTrue(replay.json()["duplicate"])
        self.assertEqual(self.store.commits, 1)

    def test_stale_writer_cannot_replace_newer_state(self):
        initial = self.write(state()).headers["etag"]
        self.assertEqual(self.write(state("r2"), etag=initial).status_code, 200)
        self.assertEqual(self.write(state("r3"), etag=initial).status_code, 409)
        self.assertEqual(json.loads(self.store.get("meat")[0])["revision"], "r2")

    def test_initial_import_cannot_overwrite_existing_department(self):
        self.write(state())
        self.assertEqual(self.write(state("r2")).status_code, 409)

    def test_same_business_revision_still_protects_changed_sync_metadata(self):
        initial = self.write(state()).headers["etag"]
        updated = self.write(state(sync={"status": "verified"}), etag=initial)
        self.assertNotEqual(updated.headers["etag"], initial)
        self.assertEqual(self.write(state(sync={"status": "older"}), etag=initial).status_code, 409)

    def test_bad_checksum_and_missing_records_do_not_commit(self):
        self.assertEqual(self.write(state(), **{"X-Content-SHA256": "0" * 64}).status_code, 422)
        self.assertEqual(self.write({"revision": "r1", "items": []}).status_code, 422)
        self.assertEqual(self.store.commits, 0)

    def test_mismatched_department_is_rejected(self):
        self.assertEqual(self.write(state(department="produce")).status_code, 422)

    def test_unavailable_database_does_not_report_saved(self):
        with patch.object(self.store, "put", side_effect=RuntimeError("private connection details")):
            response = self.write(state())
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("private connection", response.text)
            self.assertNotIn('"saved":true', response.text)

    def test_empty_oversized_and_ambiguous_json_are_rejected(self):
        for raw in (b"", b"x" * (16 * 1024 * 1024 + 1), b'{"revision":"a","revision":"b"}', b'{"bad":NaN}',
                    json.dumps(state(overflow=1)).replace('"overflow": 1', '"overflow": 1e999').encode()):
            with self.assertRaises(HTTPException):
                validate_state(raw, "meat")

    def test_precondition_required(self):
        response = self.client.put("/v1/departments/meat/state", content=b"{}", headers={"Authorization": "Bearer " + "m" * 48})
        self.assertEqual(response.status_code, 428)


if __name__ == "__main__":
    unittest.main()
