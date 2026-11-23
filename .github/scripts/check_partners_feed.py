#!/usr/bin/env python3
"""Check the public dealer export used by the directory."""
import csv
import io
from collections import Counter
from urllib.request import Request, urlopen

URL = ("https://docs.google.com/spreadsheets/d/1zzypRi-wST20xu0rns-uSnGk7NmikkW2kw44jvsDgBY"
       "/export?format=csv&gid=24681103&range=A%3AN")


def active_partners():
    request = Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=35) as response:
        rows = csv.DictReader(io.StringIO(response.read().decode("utf-8-sig"), newline=""))
        required = {"partner_id", "sort_order", "city", "district", "name", "website", "phone",
                    "address", "hours", "latitude", "longitude", "active", "demo", "Сайт дилера"}
        assert required <= set(rows.fieldnames or []), "Partner export is missing public columns"
        available = [row for row in rows if row["partner_id"].strip()]
    assert len({row["partner_id"].strip() for row in available}) == len(available), "Duplicate dealer ID"
    active = [row for row in available if row["active"].strip().lower() not in {"false", "0", "нет", "no"}]
    assert active and all(row["city"].strip() and row["name"].strip() for row in active), "Missing dealer name or city"
    return active


def has_pin(row):
    try:
        lat = float(row["latitude"].strip().replace(",", "."))
        lng = float(row["longitude"].strip().replace(",", "."))
        return 51 <= lat <= 57 and 23 <= lng <= 33.5
    except ValueError:
        return False


if __name__ == "__main__":
    dealers = active_partners()
    cities = Counter(row["city"].strip() for row in dealers)
    print(f"Public directory: {len(dealers)} active shops in {len(cities)} cities, "
          f"{cities['Минск']} in Minsk, {sum(map(has_pin, dealers))} map pins.")
