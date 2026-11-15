"""Progressive web app routes.

The service worker has to be served from the site root. A file under
/static/ would only be allowed to control /static/, which would not
cover the app.
"""

from __future__ import annotations

import os

from flask import Blueprint, send_from_directory

pwa_bp = Blueprint("pwa", __name__)

_ASSETS = os.path.join(os.path.dirname(__file__), "pwa_assets")


def _asset(filename: str, mimetype: str):
    response = send_from_directory(_ASSETS, filename, mimetype=mimetype)
    # Revalidate so a new deploy replaces the manifest and worker promptly.
    response.headers["Cache-Control"] = "no-cache"
    return response


@pwa_bp.get("/manifest.webmanifest")
def manifest():
    return _asset("manifest.webmanifest", "application/manifest+json")


@pwa_bp.get("/sw.js")
def service_worker():
    response = _asset("sw.js", "application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@pwa_bp.get("/offline.html")
def offline():
    return _asset("offline.html", "text/html; charset=utf-8")
