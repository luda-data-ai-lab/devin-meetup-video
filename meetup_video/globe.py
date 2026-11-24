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


def korea_names(regions):
    return next((row.get("featured_names", []) for region in regions for row in region["countries"]
                 if row["country"] == "South Korea"), [])


def view_at(scene, t):
    regions = scene.globe["regions"]
    stops = [{"lat": 18, "lon": -28}, *regions]
    if korea_names(regions):
        stops.append({"lat": 37.57, "lon": 126.98})
    i, phase = divmod(max(0, t) * len(stops) / scene.duration, 1)
    i = min(int(i), len(stops) - 1)
    stop, prev = stops[i], stops[max(i - 1, 0)]
    f = min(1, phase / 0.34)
    f = f * f * (3 - 2 * f)
    if t >= scene.duration:
        f = 1
    lat = prev["lat"] + (stop["lat"] - prev["lat"]) * f
    delta = (stop["lon"] - prev["lon"] + 180) % 360 - 180
    lon = (prev["lon"] + delta * f + 180) % 360 - 180
    return i, lat, lon


def project_pin(lat, lon, view_lat, view_lon):
    lat, view_lat, delta = map(math.radians, (lat, view_lat, lon - view_lon))
    cos_lat, sin_lat = math.cos(lat), math.sin(lat)
    near = math.sin(view_lat) * sin_lat + math.cos(view_lat) * cos_lat * math.cos(delta)
    if near >= -1e-12:
        return (cos_lat * math.sin(delta),
                math.sin(view_lat) * cos_lat * math.cos(delta) - math.cos(view_lat) * sin_lat)
    return None


def opening_views(regions):
    coords = [(region["lat"], region["lon"]) for region in regions]
    west = [i for i, (_, lon) in enumerate(coords) if lon < -24]
    east = [i for i, (_, lon) in enumerate(coords) if lon >= -24]
    views = [(20, -91, "AMERICAS", west), (20, 66, "EUROPE · AFRICA · ASIA", east)]
    if all(project_pin(*coords[i], lat, lon) is not None
           for lat, lon, _, indices in views for i in indices):
        return views

    east_lat, east_lon, _, _ = views[1]
    opposite = (-east_lat, east_lon - 180)
    west = [i for i, coord in enumerate(coords) if project_pin(*coord, *opposite) is not None]
    east = [i for i in range(len(coords)) if i not in west]
    return [(*opposite, "WORLD VIEW 01", west), (east_lat, east_lon, "WORLD VIEW 02", east)]


def frame(scene, t, width, height):
    regions = scene.globe["regions"]
    totals = [sum(row["count"] for row in region["countries"]) for region in regions]
    i, lat, lon = view_at(scene, t)
    worldwide = i == 0
    featured_names = korea_names(regions)
    korea = i > len(regions)
    zoom = 0
    if korea:
        phase = t * (len(regions) + 2) / scene.duration - i
        p = max(0, min(1, phase / 0.72))
        zoom = p * p * (3 - 2 * p)
    if worldwide:
        name, count = "전 세계", sum(totals)
        rows = [(r["name"], n) for r, n in zip(regions, totals)]
    elif not korea:
        region = regions[i - 1]
        name, count = region["name"], totals[i - 1]
        rows = [(row["country"], row["count"]) for row in region["countries"]]
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

    def globe(cx, cy, r, view_lat, view_lon, gaps=(16, 43, 74)):
        for gap in gaps:
            d.ellipse(rect(cx - r - gap, cy - r - gap, cx + r + gap, cy + r + gap),
                      outline=line, width=max(1, round(k)))
        sphere = globe_image(max(2, round(2 * r * k)), view_lat, view_lon)
        image.alpha_composite(sphere, xy(cx - r, cy - r))

    def dot(x, y, active):
        color = accent if active else fg
        radius = 15 if active else 9
        d.ellipse(rect(x - radius, y - radius, x + radius, y + radius), fill=bg, outline=color,
                  width=max(1, round((3 if active else 2) * k)))
        d.ellipse(rect(x - 4, y - 4, x + 4, y + 4), fill=color)

    def region_pins(cx, cy, r, view_lat, view_lon, region_indices):
        pins = []
        for index in region_indices:
            region = regions[index]
            pos = project_pin(region["lat"], region["lon"], view_lat, view_lon)
            if pos is not None:
                pins.append((index, cx + r * pos[0], cy + r * pos[1]))
        occupied = [(x - 11, y - 11, x + 11, y + 11) for _, x, y in pins]
        pins.sort(key=lambda pin: pin[0] != i - 1)

        def place_badge(index, x, y, alternate):
            badge_w, badge_h = 33 + 18 * len(str(totals[index])), 40
            if alternate:
                options = [(dx, dy) for dy in (-31 - badge_h, 31 + badge_h)
                           for dx in (31, -31 - badge_w)]
            else:
                options = [(31, -31), (-31 - badge_w, -31), (31, 31), (-31 - badge_w, 31),
                           (-badge_w / 2, -55), (-badge_w / 2, 55)]
            for dx, dy in options:
                left, top = x + dx, y + dy - badge_h / 2
                box = (left, top, left + badge_w, top + badge_h)
                if not (924 <= left and box[2] <= 1870 and 84 <= top and box[3] <= 934):
                    continue
                if any(left < right and box[2] > bx and top < bottom and box[3] > by
                       for bx, by, right, bottom in occupied):
                    continue
                occupied.append(box)
                return box
            return None

        badges = {index: place_badge(index, x, y, False) for index, x, y in pins}
        if worldwide:
            for index, x, y in pins:
                if badges[index] is None:
                    badges[index] = place_badge(index, x, y, True)

        for index, x, y in pins:
            active = index == i - 1
            color = accent if active else fg
            box = badges[index]
            if box is not None:
                left, top, right, bottom = box
                end_x = min(max(x, left), box[2])
                end_y = min(max(y, top), box[3])
                d.line((*xy(x, y), *xy(end_x, end_y)), fill=color, width=max(1, round(2 * k)))
                d.rounded_rectangle(rect(*box), radius=max(1, round(9 * k)), fill=bg, outline=color,
                                    width=max(1, round(2 * k)))
                label((left + right) / 2, (top + bottom) / 2, totals[index], 27, color, "mm", mono=True)
            dot(x, y, active)

    def roster(x, y, columns, col_width, row_height):
        per_col = math.ceil(len(rows) / columns)
        for j, (country, number) in enumerate(rows):
            xx, yy = x + (j // per_col) * col_width, y + (j % per_col) * row_height
            d.line((*xy(xx, yy - row_height / 2), *xy(xx + col_width - 24, yy - row_height / 2)), fill=line)
            label(xx, yy, country, 26, max_width=col_width - 106)
            label(xx + col_width - 24, yy, number, 26, accent, "rm", mono=True, max_width=72)

    cx, cy, radius = 1385, 512, 355
    if worldwide:
        for x, (view_lat, view_lon, side, indices) in zip((1125, 1625), opening_views(regions)):
            globe(x, cy, 203, view_lat, view_lon, (12, 26))
            region_pins(x, cy, 203, view_lat, view_lon, indices)
            label(x, 790, side, 17, muted, "mm", mono=True)
    elif korea:
        radius += 78 * zoom
        cy -= 29 * zoom
        globe(cx, cy, radius, lat, lon, (13, 28, 45))
        pos = project_pin(37.57, 126.98, lat, lon)
        if pos is not None:
            dot(cx + radius * pos[0], cy + radius * pos[1], True)
    else:
        globe(cx, cy, radius, lat, lon)
        region_pins(cx, cy, radius, lat, lon, range(len(regions)))
    label(100, 88, "DEVIN MEETUP SEOUL  /  AMBASSADOR NETWORK", 25, accent, mono=True)
    if korea:
        label(100, 209, "대한민국", 71, max_width=800)
        label(100, 305, "서울  /  SEOUL, SOUTH KOREA", 27, accent)
        spacing = min(93 + 32 * zoom, 500 / len(featured_names))
        size = 54 + 35 * zoom
        for j, featured_name in enumerate(featured_names):
            label(100, 428 + j * spacing, featured_name, min(size, spacing * 0.85), max_width=800)
    else:
        label(100, 209, name, 71, max_width=800)
        label(100, 346, count, 149, accent, mono=True, max_width=440)
        label(100, 445, "활동 중인 앰버서더  /  ACTIVE AMBASSADORS", 27, muted)
        roster(100, 525, 2, 408, min(53, 420 / math.ceil(len(rows) / 2)))
    if not worldwide:
        label(1820, 940, f"{abs(lat):05.1f}° {'N' if lat >= 0 else 'S'}  /  {abs(lon):05.1f}° {'E' if lon >= 0 else 'W'}",
              22, muted, "rm", mono=True)

    d.line((*xy(100, 1004), *xy(1820, 1004)), fill=line, width=max(1, round(k)))
    label(100, 1040, f"{len(regions):02d} REGIONS  /  {sum(len(r['countries']) for r in regions):02d} COUNTRIES", 21, muted, mono=True)
    label(1820, 1040, f"{i + 1:02d} / {len(regions) + 1 + bool(featured_names):02d}", 21, accent, "rm", mono=True)
    return image
