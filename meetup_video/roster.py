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
COUNTRIES = {"usa": "United States", "uk": "United Kingdom", "uae": "United Arab Emirates",
             "korea": "South Korea"}
CITY_ALIASES = {"sao paulo": "São Paulo", "nyc": "New York City", "new york": "New York City",
                "bangalore": "Bengaluru", "i̇stanbul": "Istanbul",
                "ottowa": "Ottawa", "deleware": "Delaware", "cancun": "Cancún",
                "auckland city": "Auckland", "iasi": "Iași",
                "waterford ny": "Waterford", "ithaca, new york": "Ithaca", "miami, florida": "Miami",
                "washington, dc": "Washington DC", "atlanta, ga": "Atlanta", "chicago, il": "Chicago",
                "greenville, sc": "Greenville", "west lafayette, in": "West Lafayette",
                "stanford, ca": "Stanford", "kirkland (montreal)": "Kirkland"}
CITY_COORDINATES = Path(__file__).resolve().parent.parent / "assets" / "ambassador-city-coordinates.json"


def country_name(country):
    country = unicodedata.normalize("NFC", " ".join(country.split()))
    return COUNTRIES.get(country.casefold(), country)


def country_key(country):
    return country_name(country).casefold()


def city_key(country, city):
    city = unicodedata.normalize("NFC", " ".join(city.split())).casefold()
    return country_key(country), CITY_ALIASES.get(city, city).casefold()


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
        yield region, country_name(country), CITY_ALIASES.get(city.casefold(), city)


def globe_project(lines, existing_regions=()):
    counts = {region: Counter() for region in REGIONS}
    city_counts = {region: Counter() for region in REGIONS}
    coordinates = json.loads(CITY_COORDINATES.read_text(encoding="utf-8"))
    country_names = {country_key(name): name for name in (*coordinates, *COUNTRIES.values())}
    for region, name, city in read_roster(lines):
        country = country_key(name)
        country_names.setdefault(country, name)
        counts[region][country] += 1
        if city:
            city_counts[region][city_key(country, city)] += 1
    cities_by_key = {
        city_key(country, city): {"name": city, "country": country, "lat": lat, "lon": lon}
        for country, known in coordinates.items() for city, (lat, lon) in known.items()
    }
    cities_by_key.update(
        (city_key(city["country"], city.get("roster_city", city["name"])), city)
        for region in existing_regions for city in region.get("cities", [])
    )
    featured = {country_key(row["country"]): row["featured_names"]
                for region in existing_regions for row in region["countries"] if "featured_names" in row}
    regions = []
    for key, (name, lat, lon) in REGIONS.items():
        if counts[key]:
            countries = []
            for country, count in sorted(counts[key].items(), key=lambda row: (-row[1], country_names[row[0]])):
                row = {"country": country_names[country], "count": count}
                if country in featured:
                    row["featured_names"] = featured[country]
                countries.append(row)
            cities = [{**cities_by_key[city], "count": n}
                      for city, n in city_counts[key].items() if city in cities_by_key]
            region = {"name": name, "lat": lat, "lon": lon, "countries": countries}
            if cities:
                region["cities"] = sorted(cities, key=lambda city: (-city["count"], city["name"]))
            regions.append(region)
    if not regions:
        raise ValueError("Roster has no ambassador rows")
    return {"scenes": [{"id": "ambassador-globe", "type": "globe", "duration": 2 * (len(regions) + 1),
                        "globe": {"regions": regions}}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tsv", type=Path)
    parser.add_argument("--existing-project", type=Path, help="preserve saved city display names and coordinates")
    args = parser.parse_args()
    existing_regions = ()
    if args.existing_project:
        project = json.loads(args.existing_project.read_text(encoding="utf-8"))
        orbit = next((scene for scene in project["scenes"] if scene.get("type") == "globe"), None)
        if orbit is None:
            parser.error("--existing-project must contain an Orbit scene")
        existing_regions = orbit["globe"]["regions"]
    with args.tsv.open(encoding="utf-8-sig", newline="") as source:
        print(json.dumps(globe_project(source, existing_regions), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
