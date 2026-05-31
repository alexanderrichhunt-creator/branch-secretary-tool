"""Download public-domain Carl Bloch baptism cover art for Word programs."""
from __future__ import annotations

import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "app" / "static" / "images" / "baptism_cover.jpg"
URLS = (
    "https://commons.wikimedia.org/wiki/Special:FilePath/The-Baptism-Of-Christ.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1f/The-Baptism-Of-Christ.jpg/480px-The-Baptism-Of-Christ.jpg",
)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "branch-secretary-tool/1.0 (cover fetch)"}
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers=headers)
            data = urllib.request.urlopen(req, timeout=30).read()
            if len(data) < 1000:
                continue
            OUT.write_bytes(data)
            print(f"Saved {len(data)} bytes to {OUT}")
            return
        except Exception as exc:
            print(f"Failed {url}: {exc}")
    raise SystemExit("Could not download cover image")


if __name__ == "__main__":
    main()
