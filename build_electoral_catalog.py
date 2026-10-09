"""Build a privacy-preserving São Paulo candidate catalog from official TSE files.

The generated catalog is sharded by candidate-number prefix so the static site
does not need to download the complete statewide registry during login.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
import os
import unicodedata
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "votos_Bueno"
CANDIDATE_DIR = SOURCE_DIR / "candidatos"
OUTPUT_DIR = ROOT / "electoral-data"
YEARS = (2020, 2022, 2024, 2026)
ALLOWED_OFFICES = {"VEREADOR", "DEPUTADO ESTADUAL", "DEPUTADO FEDERAL"}


def normalized(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", " ", ascii_value.upper()).strip()


def person_id(full_name: str, birth_date: str) -> str:
    # Only the irreversible identifier is published; birth date and CPF never leave the build.
    identity = f"{normalized(full_name)}|{birth_date.strip()}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def read_candidate_rows():
    for year in YEARS:
        archive = CANDIDATE_DIR / f"consulta_cand_{year}.zip"
        member = f"consulta_cand_{year}_SP.csv"
        with zipfile.ZipFile(archive) as zipped, zipped.open(member) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="latin-1", newline=""), delimiter=";")
            for row in reader:
                if normalized(row["DS_CARGO"]) in ALLOWED_OFFICES:
                    yield year, row


def bweb_archives() -> dict[int, Path]:
    result = {}
    for path in SOURCE_DIR.glob("bweb_1t_SP_*.zip"):
        match = re.search(r"(2020|2022|2024|2026)", path.name)
        if match:
            result[int(match.group(1))] = path
    return result


def vote_key(year: int, municipality: str, office: str, number: str) -> str:
    normalized_office = normalized(office)
    scope = normalized(municipality) if normalized_office == "VEREADOR" else "SP"
    return "|".join((str(year), scope, normalized_office, number.lstrip("0") or "0"))


def load_votes(valid_keys: set[str]) -> tuple[dict[str, dict[str, int]], dict[str, int]]:
    by_zone: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    totals: dict[str, int] = defaultdict(int)
    for year, archive in sorted(bweb_archives().items()):
        with zipfile.ZipFile(archive) as zipped:
            member = next(name for name in zipped.namelist() if name.lower().endswith(".csv"))
            with zipped.open(member) as raw:
                reader = csv.DictReader(io.TextIOWrapper(raw, encoding="latin-1", newline=""), delimiter=";")
                for row in reader:
                    if row["CD_TIPO_VOTAVEL"] != "1":
                        continue
                    key = vote_key(year, row["NM_MUNICIPIO"], row["DS_CARGO_PERGUNTA"], row["NR_VOTAVEL"])
                    if key not in valid_keys:
                        continue
                    votes = int(row["QT_VOTOS"] or 0)
                    zone = str(int(row["NR_ZONA"]))
                    territory = f'{row["NM_MUNICIPIO"].strip().title()}|{zone}'
                    by_zone[key][territory] += votes
                    totals[key] += votes
    return by_zone, totals


def build() -> None:
    people: dict[str, dict] = {}
    valid_keys: set[str] = set()
    candidacy_refs: list[tuple[str, dict, str]] = []
    year_counts: dict[int, int] = defaultdict(int)

    for year, row in read_candidate_rows():
        pid = person_id(row["NM_CANDIDATO"], row["DT_NASCIMENTO"])
        person = people.setdefault(pid, {
            "id": pid,
            "name": row["NM_URNA_CANDIDATO"].strip().title(),
            "normalizedNames": set(),
            "candidacies": [],
        })
        person["normalizedNames"].update({normalized(row["NM_URNA_CANDIDATO"]), normalized(row["NM_CANDIDATO"])})
        municipality = row["NM_UE"].strip().title() if normalized(row["DS_CARGO"]) == "VEREADOR" else "São Paulo"
        candidacy = {
            "year": year,
            "sequence": row["SQ_CANDIDATO"],
            "number": row["NR_CANDIDATO"].lstrip("0") or "0",
            "ballotName": row["NM_URNA_CANDIDATO"].strip().title(),
            "office": row["DS_CARGO"].strip().title(),
            "municipality": municipality,
            "party": row["SG_PARTIDO"].strip(),
            "registrationStatus": row["DS_SITUACAO_CANDIDATURA"].strip(),
            "resultStatus": row["DS_SIT_TOT_TURNO"].strip(),
            "votes": 0,
            "zones": [],
        }
        key = vote_key(year, row["NM_UE"], row["DS_CARGO"], row["NR_CANDIDATO"])
        valid_keys.add(key)
        candidacy_refs.append((pid, candidacy, key))
        person["candidacies"].append(candidacy)
        year_counts[year] += 1

    by_zone, totals = load_votes(valid_keys)
    for _, candidacy, key in candidacy_refs:
        candidacy["votes"] = totals.get(key, 0)
        candidacy["zones"] = [
            {"municipality": territory.rsplit("|", 1)[0], "zone": territory.rsplit("|", 1)[1], "votes": votes}
            for territory, votes in sorted(by_zone.get(key, {}).items())
        ]

    for person in people.values():
        person["normalizedNames"] = sorted(person["normalizedNames"])
        person["candidacies"].sort(key=lambda item: (item["year"], item["office"], item["municipality"]))

    shards: dict[str, list[dict]] = defaultdict(list)
    for person in people.values():
        prefixes = {candidacy["number"].zfill(5)[:2] for candidacy in person["candidacies"]}
        for prefix in prefixes:
            shards[prefix].append(person)

    temporary = OUTPUT_DIR.with_name(OUTPUT_DIR.name + ".tmp")
    if temporary.exists():
        shutil.rmtree(temporary)
    (temporary / "number").mkdir(parents=True)
    for prefix, entries in sorted(shards.items()):
        entries.sort(key=lambda item: (item["name"], item["id"]))
        (temporary / "number" / f"{prefix}.json").write_text(
            json.dumps({"schemaVersion": 1, "candidates": entries}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
    manifest = {
        "schemaVersion": 1,
        "source": "Tribunal Superior Eleitoral - Dados Abertos",
        "generatedYears": list(YEARS),
        "candidateCount": len(people),
        "candidacyCount": sum(year_counts.values()),
        "candidaciesByYear": {str(year): year_counts[year] for year in YEARS},
        "shards": sorted(shards),
    }
    (temporary / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    backup = OUTPUT_DIR.with_name(OUTPUT_DIR.name + ".previous")
    if backup.exists():
        shutil.rmtree(backup)
    if OUTPUT_DIR.exists():
        try:
            OUTPUT_DIR.replace(backup)
        except OSError:
            shutil.copytree(temporary, OUTPUT_DIR, dirs_exist_ok=True)
            shutil.rmtree(temporary)
            print(json.dumps(manifest, ensure_ascii=False))
            compress_existing_catalog()
            return
    try:
        os.replace(temporary, OUTPUT_DIR)
    except OSError:
        if backup.exists() and not OUTPUT_DIR.exists():
            backup.replace(OUTPUT_DIR)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copytree(temporary, OUTPUT_DIR, dirs_exist_ok=True)
        shutil.rmtree(temporary)
    if backup.exists():
        shutil.rmtree(backup)
    print(json.dumps(manifest, ensure_ascii=False))


def compress_existing_catalog() -> None:
    """Create static gzip shards from the verified full-history candidate catalog."""
    for source in sorted((OUTPUT_DIR / "number").glob("*.json")):
        target = source.with_suffix(source.suffix + ".gz")
        with source.open("rb") as input_stream, target.open("wb") as output_stream:
            import gzip
            with gzip.GzipFile(filename="", mode="wb", fileobj=output_stream, compresslevel=9, mtime=0) as compressed:
                shutil.copyfileobj(input_stream, compressed, length=1024 * 1024)
        print(f"{source.name}: {target.stat().st_size} bytes")


if __name__ == "__main__":
    import sys
    if "--compress-existing" in sys.argv:
        compress_existing_catalog()
    else:
        build()
        compress_existing_catalog()
