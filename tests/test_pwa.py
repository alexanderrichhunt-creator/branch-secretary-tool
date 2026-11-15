"""Installable web app: manifest, service worker, and icons."""

from __future__ import annotations

import json
import os
import struct
import tempfile
import unittest


def _png_size(data: bytes) -> tuple[int, int]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("not a png")
    length, tag = struct.unpack(">I4s", data[8:16])
    if tag != b"IHDR" or length < 8:
        raise AssertionError("missing IHDR")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


class PwaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_file.close()
        cls._prev_db = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = "sqlite:///" + db_file.name
        os.environ["SECRET_KEY"] = "test-secret"
        os.environ["INIT_ADMIN_EMAIL"] = "admin@example.com"
        os.environ["INIT_ADMIN_PASSWORD"] = "test-password-123"
        from app import create_app

        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        if cls._prev_db is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = cls._prev_db

    def test_manifest_is_installable(self):
        response = self.client.get("/manifest.webmanifest")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/manifest+json", response.content_type)
        self.assertIn("no-cache", response.headers.get("Cache-Control", ""))
        manifest = json.loads(response.data)
        self.assertEqual(manifest["name"], "Branch Secretary")
        self.assertEqual(manifest["short_name"], "Branch Secretary")
        self.assertEqual(manifest["start_url"], "/")
        self.assertEqual(manifest["scope"], "/")
        self.assertEqual(manifest["display"], "standalone")
        self.assertTrue(manifest["theme_color"])
        self.assertTrue(manifest["background_color"])
        purposes = {}
        for icon in manifest["icons"]:
            purposes.setdefault(icon["purpose"], set()).add(icon["sizes"])
            icon_response = self.client.get(icon["src"])
            self.assertEqual(icon_response.status_code, 200, icon["src"])
            self.assertIn("image/png", icon_response.content_type)
            self.assertEqual(_png_size(icon_response.data), tuple(int(part) for part in icon["sizes"].split("x")))
        self.assertIn("192x192", purposes["any"])
        self.assertIn("512x512", purposes["any"])
        self.assertIn("192x192", purposes["maskable"])
        self.assertIn("512x512", purposes["maskable"])

    def test_service_worker_covers_the_app_and_skips_dynamic_data(self):
        response = self.client.get("/sw.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("javascript", response.content_type)
        self.assertEqual(response.headers.get("Service-Worker-Allowed"), "/")
        self.assertIn("no-cache", response.headers.get("Cache-Control", ""))
        source = response.get_data(as_text=True)
        self.assertIn('addEventListener("fetch"', source)
        navigate = source.split("async function networkOrOffline")[1].split("async function")[0]
        self.assertNotIn("cache.put", navigate)
        self.assertIn("/offline.html", navigate)
        guard = source.split("function isCacheableAsset")[1].split("async function")[0]
        self.assertIn('startsWith("/api/")', guard)
        self.assertIn('startsWith("/auth/")', guard)
        self.assertIn('startsWith("/static/")', guard)

    def test_offline_page_is_static(self):
        response = self.client.get("/offline.html")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.content_type)
        body = response.get_data(as_text=True)
        self.assertIn("You're offline", body)
        self.assertNotIn("current_user", body)
        self.assertNotIn("{{", body)

    def test_every_public_shell_links_the_manifest(self):
        login = self.client.get("/auth/login")
        self.assertEqual(login.status_code, 200)
        html = login.get_data(as_text=True)
        self.assertIn('rel="manifest"', html)
        self.assertIn('href="/manifest.webmanifest"', html)
        self.assertIn('name="theme-color"', html)
        self.assertIn('rel="apple-touch-icon"', html)
        self.assertIn('width=device-width', html)
        self.assertIn('serviceWorker.register("/sw.js"', html)
        self.assertIn('scope: "/"', html)

        self.client.post(
            "/auth/login",
            data={"email": "admin@example.com", "password": "test-password-123"},
        )
        for path in ("/calendar/print", "/cleaning/print"):
            page = self.client.get(path)
            self.assertEqual(page.status_code, 200, path)
            page_html = page.get_data(as_text=True)
            self.assertIn('href="/manifest.webmanifest"', page_html, path)
            self.assertIn('rel="apple-touch-icon"', page_html, path)
            self.assertIn('serviceWorker.register("/sw.js"', page_html, path)

    def test_apple_touch_icon(self):
        response = self.client.get("/static/icons/apple-touch-icon.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(_png_size(response.data), (180, 180))
