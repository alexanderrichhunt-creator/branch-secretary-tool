"""Draw the Branch Secretary home-screen icons.

Stdlib only. Run from the repo root:

    python scripts/generate_pwa_icons.py

The mark is a white list card with a check, on the app blue. Maskable
icons keep that mark inside the center 80% safe zone and bleed the blue
background to the edges so Android can crop them.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

BLUE = (26, 115, 232)
BLUE_DARK = (23, 78, 166)
WHITE = (255, 255, 255)
LINE = (210, 227, 252)

OUT_DIR = Path(__file__).resolve().parents[1] / "app" / "static" / "icons"


def _inside_round_rect(x: float, y: float, left: float, top: float, right: float, bottom: float, radius: float) -> bool:
    cx = min(max(x, left + radius), right - radius)
    cy = min(max(y, top + radius), bottom - radius)
    dx = x - cx
    dy = y - cy
    return dx * dx + dy * dy <= radius * radius


def _dist_to_segment(x: float, y: float, x1: float, y1: float, x2: float, y2: float) -> float:
    vx = x2 - x1
    vy = y2 - y1
    length_sq = vx * vx + vy * vy
    if length_sq <= 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((x - x1) * vx + (y - y1) * vy) / length_sq))
    px = x1 + t * vx
    py = y1 + t * vy
    return ((x - px) ** 2 + (y - py) ** 2) ** 0.5


def _mix(dst: tuple[int, int, int], src: tuple[int, int, int], alpha: float) -> tuple[int, int, int]:
    if alpha <= 0:
        return dst
    if alpha >= 1:
        return src
    inv = 1 - alpha
    return (
        int(dst[0] * inv + src[0] * alpha + 0.5),
        int(dst[1] * inv + src[1] * alpha + 0.5),
        int(dst[2] * inv + src[2] * alpha + 0.5),
    )


def _coverage(distance: float, radius: float) -> float:
    # Soft edge about 0.75px wide so scaled icons stay crisp.
    edge = 0.75
    return max(0.0, min(1.0, (radius + edge / 2 - distance) / edge))


def render(size: int, card_scale: float) -> bytes:
    pixels = bytearray(size * size * 3)
    card = size * card_scale
    left = (size - card) / 2
    top = (size - card) / 2
    right = left + card
    bottom = top + card
    radius = card * 0.14
    header_bottom = top + card * 0.28
    pad_x = card * 0.14
    line_h = max(2.0, card * 0.055)
    line_gap = card * 0.09
    line_top = header_bottom + card * 0.12
    line_widths = (0.72, 0.48, 0.60)
    badge_r = card * 0.16
    badge_cx = right - card * 0.22
    badge_cy = bottom - card * 0.22
    check_stroke = max(2.0, card * 0.045)
    check = (
        (badge_cx - badge_r * 0.42, badge_cy + badge_r * 0.02),
        (badge_cx - badge_r * 0.08, badge_cy + badge_r * 0.38),
        (badge_cx + badge_r * 0.48, badge_cy - badge_r * 0.36),
    )

    for y in range(size):
        py = y + 0.5
        row = y * size * 3
        for x in range(size):
            px = x + 0.5
            color = BLUE
            on_card = _inside_round_rect(px, py, left, top, right, bottom, radius)
            if on_card:
                color = BLUE_DARK if py < header_bottom else WHITE
                if py >= line_top:
                    for index, width_frac in enumerate(line_widths):
                        ly = line_top + index * (line_h + line_gap)
                        if ly <= py <= ly + line_h and left + pad_x <= px <= left + pad_x + card * width_frac:
                            # Keep the lines off the badge.
                            if (px - badge_cx) ** 2 + (py - badge_cy) ** 2 > (badge_r + 2) ** 2:
                                color = LINE
            badge_d = ((px - badge_cx) ** 2 + (py - badge_cy) ** 2) ** 0.5
            badge_alpha = _coverage(badge_d, badge_r)
            if badge_alpha > 0:
                color = _mix(color, BLUE_DARK, badge_alpha)
                stroke = min(
                    _dist_to_segment(px, py, *check[0], *check[1]),
                    _dist_to_segment(px, py, *check[1], *check[2]),
                )
                check_alpha = _coverage(stroke, check_stroke / 2) * badge_alpha
                if check_alpha > 0:
                    color = _mix(color, WHITE, check_alpha)
            offset = row + x * 3
            pixels[offset] = color[0]
            pixels[offset + 1] = color[1]
            pixels[offset + 2] = color[2]
    return bytes(pixels)


def _box_downscale(src: bytes, src_size: int, dst_size: int) -> bytes:
    if src_size == dst_size:
        return src
    if src_size % dst_size != 0:
        raise ValueError(f"Cannot evenly scale {src_size} to {dst_size}")
    factor = src_size // dst_size
    area = factor * factor
    out = bytearray(dst_size * dst_size * 3)
    for y in range(dst_size):
        for x in range(dst_size):
            totals = [0, 0, 0]
            for sy in range(factor):
                src_y = y * factor + sy
                row = src_y * src_size * 3
                for sx in range(factor):
                    src_x = x * factor + sx
                    offset = row + src_x * 3
                    totals[0] += src[offset]
                    totals[1] += src[offset + 1]
                    totals[2] += src[offset + 2]
            base = (y * dst_size + x) * 3
            out[base] = totals[0] // area
            out[base + 1] = totals[1] // area
            out[base + 2] = totals[2] // area
    return bytes(out)


def write_png(path: Path, size: int, rgb: bytes) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + rgb[y * size * 3 : (y + 1) * size * 3] for y in range(size))
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Render at 4x and box-scale so 512, 192, and 180 all come from one pass
    # per variant. 720 is divisible by 180 and 512* something... 512 and 192
    # share a factor of 64. 180 does not. Render the master at 5760? Too big.
    # 512 and 192: master 1536 (3x512, 8x192). Apple touch is rendered at 180x3.
    any_master = render(1536, 0.66)
    mask_master = render(1536, 0.52)
    jobs = {
        "icon-512.png": _box_downscale(any_master, 1536, 512),
        "icon-192.png": _box_downscale(any_master, 1536, 192),
        "icon-maskable-512.png": _box_downscale(mask_master, 1536, 512),
        "icon-maskable-192.png": _box_downscale(mask_master, 1536, 192),
    }
    sizes = {
        "icon-512.png": 512,
        "icon-192.png": 192,
        "icon-maskable-512.png": 512,
        "icon-maskable-192.png": 192,
    }
    for name, rgb in jobs.items():
        write_png(OUT_DIR / name, sizes[name], rgb)
        print(f"wrote {OUT_DIR / name}")

    apple = render(540, 0.66)
    write_png(OUT_DIR / "apple-touch-icon.png", 180, _box_downscale(apple, 540, 180))
    print(f"wrote {OUT_DIR / 'apple-touch-icon.png'}")


if __name__ == "__main__":
    main()
