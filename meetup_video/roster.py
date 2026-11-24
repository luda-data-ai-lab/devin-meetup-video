"""Convert a Region / Country / City TSV into an ambassador editor project."""
import argparse
import csv
import json
import unicodedata
from collections import Counter
from pathlib import Path

REGIONS = {
    "N.A.": ("North America", 36, -103),
    "LATAM": ("Latin America", -13, -62),
    "Europe": ("Europe", 49, 13),
    "Africa": ("Africa", 0, 21),
    "Middle East": ("Middle East", 25, 48),
    "Asia-Pacific": ("Asia-Pacific", 26, 115),
}
COUNTRIES = {"USA": "United States", "UK": "United Kingdom", "UAE": "United Arab Emirates",
             "Korea": "South Korea"}
CITY_ALIASES = {"sao paulo": "São Paulo", "nyc": "New York City", "new york": "New York City",
                "bangalore": "Bengaluru", "i̇stanbul": "Istanbul",
                "ottowa": "Ottawa", "deleware": "Delaware", "cancun": "Cancún",
                "auckland city": "Auckland", "iasi": "Iași"}


def read_roster(lines):
    rows = csv.reader(lines, delimiter="\t")
    header = next(rows, [])
    if [x.strip().removeprefix("\ufeff") for x in header] != ["Region", "Country", "City"]:
        raise ValueError("Expected a Region, Country, City TSV header")
    region = ""
    for line, row in enumerate(rows, start=2):
        row = [" ".join(unicodedata.normalize("NFC", x).split()) for x in row]
        if not any(row):
            continue
        if len(row) != 3 or not row[1]:
            raise ValueError(f"Roster line {line}: expected a country and three TSV columns")
        raw_region, country, city = row
        region = raw_region or region
        if region not in REGIONS:
            raise ValueError(f"Roster line {line}: unknown region {region!r}")
        yield region, COUNTRIES.get(country, country), CITY_ALIASES.get(city.casefold(), city)


def globe_project(lines):
    counts = {region: Counter() for region in REGIONS}
    for region, country, _city in read_roster(lines):
        counts[region][country] += 1
    regions = []
    for key, (name, lat, lon) in REGIONS.items():
        if counts[key]:
            countries = [{"country": c, "count": n} for c, n in
                         sorted(counts[key].items(), key=lambda row: (-row[1], row[0]))]
            regions.append({"name": name, "lat": lat, "lon": lon, "countries": countries})
    if not regions:
        raise ValueError("Roster has no ambassador rows")
    return {"scenes": [{"id": "ambassador-globe", "type": "globe", "duration": 2 * (len(regions) + 1),
                        "globe": {"regions": regions}}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tsv", type=Path)
    args = parser.parse_args()
    with args.tsv.open(encoding="utf-8-sig", newline="") as source:
        print(json.dumps(globe_project(source), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
