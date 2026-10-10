import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "votos_Bueno"
OUTPUT = ROOT / "data.js"

CANDIDATES = {
    "andre": {
        "name": "André Bueno",
        "number": "15777",
        "party": "MDB",
        "years": [2022, 2026],
        "offices": {"2022": "Deputado estadual", "2026": "Deputado estadual"},
        "prefix": "comparacao_andre_2022_2026",
        "expected": {"rows": 790, "2022": 61953, "2026": 71664},
    },
    "sandra": {
        "name": "Sandra Santana",
        "number": "15456",
        "party": "MDB",
        "years": [2024, 2026],
        "offices": {"2024": "Vereadora", "2026": "Deputada estadual"},
        "prefix": "comparacao_sandra_2024_2026",
        "expected": {"rows": 780, "2024": 38326, "2026": 44406},
    },
}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source, delimiter=";"))


def optional_int(value):
    return int(value) if value else None


def load_candidate(config):
    first, second = map(str, config["years"])
    prefix = config["prefix"]
    summary_rows = read_csv(SOURCE_DIR / f"{prefix}_resumo.csv")
    summary = {row["METRICA"]: row for row in summary_rows}
    zone_rows = read_csv(SOURCE_DIR / f"{prefix}_todas_zonas.csv")
    region_rows = read_csv(SOURCE_DIR / f"{prefix}_regioes.csv")
    municipality_rows = read_csv(SOURCE_DIR / f"{prefix}_municipios.csv")

    zones = [{
        "id": f"{row['MUNICIPIO']}|{row['ZONA']}",
        "municipality": row["MUNICIPIO"],
        "zone": int(row["ZONA"]),
        "place": row["ZONA_BAIRRO_REFERENCIA"],
        "region": row["REGIAO"],
        "votes": {first: int(row[f"VOTOS_{first}"]), second: int(row[f"VOTOS_{second}"])},
        "ranks": {first: optional_int(row[f"RANK_{first}"]), second: optional_int(row[f"RANK_{second}"])},
        "difference": int(row["DIFERENCA"]),
        "variationPercent": row["VARIACAO_PERCENTUAL"] or None,
        "status": row["STATUS"],
        "comparability": row["COMPARABILIDADE"],
    } for row in zone_rows]
    for zone in zones:
        if not zone["municipality"].strip() or not zone["place"].strip() or not zone["region"].strip():
            raise ValueError(f"Territorial metadata missing for {zone['municipality']} ZE {zone['zone']}")
        zone["territoryStatus"] = "historical/redistributed" if zone["municipality"] == "SAO PAULO" and zone["zone"] == 398 else "current"

    def convert_aggregate(row, name_field):
        return {
            "name": row[name_field],
            "votes": {first: int(row[f"VOTOS_{first}"]), second: int(row[f"VOTOS_{second}"])},
            "ranks": {first: optional_int(row[f"RANK_{first}"]), second: optional_int(row[f"RANK_{second}"])},
            "difference": int(row["DIFERENCA"]),
            "variationPercent": row["VARIACAO_PERCENTUAL"] or None,
            "status": row["STATUS"],
        }

    totals = {year: int(summary["TOTAL_ESTADUAL"][year]) for year in (first, second)}
    records = {year: int(summary["REGISTROS"][year]) for year in (first, second)}
    keys = {(row["municipality"], row["zone"]) for row in zones}
    sums = {year: sum(row["votes"][year] for row in zones) for year in (first, second)}
    expected = config["expected"]
    assert len(zones) == expected["rows"] == len(keys), "Missing or duplicate municipality-zone rows"
    for year in (first, second):
        assert sums[year] == totals[year] == expected[year], f"Vote reconciliation failed for {year}"

    return {
        "name": config["name"], "number": config["number"], "party": config["party"],
        "years": config["years"], "offices": config["offices"], "totals": totals, "records": records,
        "regions": [convert_aggregate(row, "REGIAO") for row in region_rows],
        "municipalities": [convert_aggregate(row, "MUNICIPIO") for row in municipality_rows],
        "zones": zones,
        "audit": {"sourceRows": len(zones), "uniqueMunicipalityZones": len(keys), "reconciledVotes": sums},
    }


def build():
    candidates = {key: load_candidate(config) for key, config in CANDIDATES.items()}
    geography = {}
    for candidate in candidates.values():
        for zone in candidate["zones"]:
            geography[f"{zone['municipality']}|{zone['zone']}"] = {
                "municipality": zone["municipality"],
                "zone": zone["zone"],
                "place": zone["place"],
                "region": zone["region"],
            }
    payload = {"schemaVersion": 3, "geography": geography, "candidates": candidates}
    OUTPUT.write_text("window.ELECTION_DATA=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    for key, candidate in payload["candidates"].items():
        print(f"{key}: rows={candidate['audit']['sourceRows']} votes={candidate['audit']['reconciledVotes']}")


if __name__ == "__main__":
    build()
