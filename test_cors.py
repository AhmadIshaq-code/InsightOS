import unittest
import os

# Disable HuggingFace Hub network checks during testing if not already disabled
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from fastapi.testclient import TestClient
from server import app


class TestProductionCORS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_production_vercel_cors_preflight(self):
        """Verify OPTIONS preflight request from production Vercel origin."""
        headers = {
            "Origin": "https://insight-os-taupe.vercel.app",
            "Access-Control-Request-Method": "GET",
        }
        res = self.client.options("/api/health", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.headers.get("access-control-allow-origin"),
            "https://insight-os-taupe.vercel.app"
        )
        self.assertEqual(
            res.headers.get("access-control-allow-credentials"),
            "true"
        )

    def test_production_vercel_cors_get_request(self):
        """Verify GET request from production Vercel origin receives Access-Control-Allow-Origin."""
        headers = {
            "Origin": "https://insight-os-taupe.vercel.app",
        }
        res = self.client.get("/api/health", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.headers.get("access-control-allow-origin"),
            "https://insight-os-taupe.vercel.app"
        )
        self.assertEqual(
            res.headers.get("access-control-allow-credentials"),
            "true"
        )

    def test_localhost_dev_origins_preserved(self):
        """Verify localhost development origins are preserved."""
        dev_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
        for origin in dev_origins:
            res = self.client.get("/api/health", headers={"Origin": origin})
            self.assertEqual(res.status_code, 200)
            self.assertEqual(
                res.headers.get("access-control-allow-origin"),
                origin,
                f"Expected origin {origin} to be allowed"
            )

    def test_disallowed_origin_rejected(self):
        """Verify arbitrary origins do NOT receive Access-Control-Allow-Origin (no wildcard)."""
        res = self.client.get("/api/health", headers={"Origin": "https://unauthorized-origin.example.com"})
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("access-control-allow-origin", res.headers)


if __name__ == "__main__":
    unittest.main()
