"""Orthographic globe and roster typography for the ambassador introduction."""
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import fonts

LAND = Path(__file__).resolve().parent.parent / "assets" / "ambassador-land.png"
OCEAN, LAND_COLOR, GRID_COLOR = map(np.array, ((10, 31, 54), (46, 143, 146), (75, 186, 179)))


@lru_cache(maxsize=1)
def land_mask():
    with Image.open(LAND) as im:
        return np.array(im, dtype=bool)


@lru_cache(maxsize=4)
def disc(diameter):
    axis = (np.arange(diameter, dtype="float32") + 0.5) * (2 / diameter) - 1
    x, y = np.meshgrid(axis, -axis)
    r2 = x * x + y * y
    z = np.sqrt(np.maximum(0, 1 - r2))
    light = np.clip(-0.24 * x + 0.33 * y + 0.72 * z, 0, 1)
    edge = np.clip((1 - np.sqrt(r2)) * (diameter / 2), 0, 1)
    return x, y, z, (0.54 + 0.52 * light)[..., None], (255 * edge).astype("uint8")


@lru_cache(maxsize=12)
def globe_image(diameter, lat, lon):
    x, y, z, light, alpha = disc(diameter)
    phi = math.radians(lat)
    latitudes = np.degrees(np.arcsin(np.clip(y * math.cos(phi) + z * math.sin(phi), -1, 1)))
    longitudes = np.degrees(np.arctan2(x, z * math.cos(phi) - y * math.sin(phi))) + lon
    mask = land_mask()
    col = (((longitudes + 180) % 360) * mask.shape[1] / 360).astype(int) % mask.shape[1]
    row = np.clip(((90 - latitudes) * mask.shape[0] / 180).astype(int), 0, mask.shape[0] - 1)
    rgb = np.where(mask[row, col, None], LAND_COLOR, OCEAN).astype("float32")
    geo_grid = np.minimum(abs((latitudes + 15) % 30 - 15), abs((longitudes + 15) % 30 - 15))
    grid = np.clip(1 - geo_grid / 0.56, 0, 1)[..., None] * 0.35
    rgb = ((1 - grid) * rgb + grid * GRID_COLOR) * light
    return Image.fromarray(np.dstack((np.clip(rgb, 0, 255).astype("uint8"), alpha)))


def view_at(scene, t):
    regions = scene.globe["regions"]
    i, phase = divmod(max(0, t) * (len(regions) + 1) / scene.duration, 1)
    i = min(int(i), len(regions))
    stops = [*regions, {"lat": 37.57, "lon": 126.98}]
    stop, prev = stops[i], stops[max(i - 1, 0)]
    f = min(1, phase / 0.34)
    f = f * f * (3 - 2 * f)
    if t >= scene.duration:
        f = 1
    lat = prev["lat"] + (stop["lat"] - prev["lat"]) * f
    delta = (stop["lon"] - prev["lon"] + 180) % 360 - 180
    lon = (prev["lon"] + delta * f + 180) % 360 - 180
    return i, lat, lon


def frame(scene, t, width, height):
    regions = scene.globe["regions"]
    totals = [sum(row["count"] for row in region["countries"]) for region in regions]
    i, lat, lon = view_at(scene, t)
    worldwide = i == len(regions)
    name = "전 세계" if worldwide else regions[i]["name"]
    count = sum(totals) if worldwide else totals[i]
    rows = ([(r["name"], n) for r, n in zip(regions, totals)] if worldwide else
            [(row["country"], row["count"]) for row in regions[i]["countries"]])
    k = min(width / 1920, height / 1080)
    x0, y0 = (width - 1920 * k) / 2, (height - 1080 * k) / 2
    xy = lambda x, y: (round(x0 + x * k), round(y0 + y * k))
    rect = lambda x1, y1, x2, y2: (*xy(x1, y1), *xy(x2, y2))
    bg, fg, muted, accent, line = "#0a1424", "#f0faf8", "#a9c9d0", "#76f7ce", "#314d5d"
    image = Image.new("RGBA", (width, height), bg)
    d = ImageDraw.Draw(image)

    def label(x, y, value, size, fill=fg, anchor="lm", mono=False, max_width=None):
        font = fonts.mono if mono else fonts.kr
        px = max(1, round(size * k))
        if max_width:
            while px > 1 and d.textlength(str(value), font=font(px)) > max_width * k:
                px -= 1
        d.text(xy(x, y), str(value), font=font(px), fill=fill, anchor=anchor)

    def globe(cx, cy, r):
        for gap in (16, 43, 74):
            d.ellipse(rect(cx - r - gap, cy - r - gap, cx + r + gap, cy + r + gap),
                      outline=line, width=max(1, round(k)))
        sphere = globe_image(max(2, round(2 * r * k)), lat, lon)
        image.alpha_composite(sphere, xy(cx - r, cy - r))
        d.ellipse(rect(cx - 12, cy - 12, cx + 12, cy + 12), outline="#ffffff", width=max(1, round(2 * k)))
        d.ellipse(rect(cx - 4, cy - 4, cx + 4, cy + 4), fill="#ffffff")

    def roster(x, y, columns, col_width, row_height):
        per_col = math.ceil(len(rows) / columns)
        for j, (country, number) in enumerate(rows):
            xx, yy = x + (j // per_col) * col_width, y + (j % per_col) * row_height
            d.line((*xy(xx, yy - row_height / 2), *xy(xx + col_width - 24, yy - row_height / 2)), fill=line)
            label(xx, yy, country, 26, max_width=col_width - 106)
            label(xx + col_width - 24, yy, number, 26, accent, "rm", mono=True, max_width=72)

    globe(1385, 512, 355)
    label(100, 88, "DEVIN MEETUP SEOUL  /  AMBASSADOR NETWORK", 25, accent, mono=True)
    label(100, 209, name, 71, max_width=800)
    label(100, 346, count, 149, accent, mono=True, max_width=440)
    label(100, 445, "활동 중인 앰버서더  /  ACTIVE AMBASSADORS", 27, muted)
    roster(100, 525, 2, 408, min(53, 420 / math.ceil(len(rows) / 2)))
    label(1820, 940, f"{abs(lat):05.1f}° {'N' if lat >= 0 else 'S'}  /  {abs(lon):05.1f}° {'E' if lon >= 0 else 'W'}",
          22, muted, "rm", mono=True)

    d.line((*xy(100, 1004), *xy(1820, 1004)), fill=line, width=max(1, round(k)))
    label(100, 1040, f"{len(regions):02d} REGIONS  /  {sum(len(r['countries']) for r in regions):02d} COUNTRIES", 21, muted, mono=True)
    label(1820, 1040, f"{i + 1:02d} / {len(regions) + 1:02d}", 21, accent, "rm", mono=True)
    return image
