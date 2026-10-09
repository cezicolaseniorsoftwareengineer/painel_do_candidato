"""Build a privacy-preserving São Paulo candidate catalog from official TSE files.

The generated catalog is sharded by candidate-number prefix so the static site
does not need to download the complete statewide registry during login.
"""

from __future__ import annotations

import csv
import gzip
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


def name_shard(value: str) -> str:
    """Return a stable shard for exact, accent-insensitive candidate-name lookup."""
    key = normalized(value).replace(" ", "")
    return (key[:2] or "__").ljust(2, "_")


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


def assign_competitive_metrics(candidacy_refs: list[tuple[str, dict, str]], people: dict[str, dict]) -> None:
    groups: dict[tuple[int, str, str], list[tuple[dict, str]]] = defaultdict(list)
    for person_id_value, candidacy, _ in candidacy_refs:
        office = normalized(candidacy["office"])
        territory = normalized(candidacy["municipality"]) if office == "VEREADOR" else "SP"
        groups[(candidacy["year"], office, territory)].append((candidacy, person_id_value))
    for entries in groups.values():
        total_nominal_votes = sum(candidacy["votes"] for candidacy, _ in entries)
        leader_votes = max((candidacy["votes"] for candidacy, _ in entries), default=0)
        leader_id = next((person_id_value for candidacy, person_id_value in entries if candidacy["votes"] == leader_votes), "")
        leader_name = people.get(leader_id, {}).get("name", "")
        candidate_count = len(entries)
        for candidacy, _ in entries:
            candidacy["rank"] = 1 + sum(other["votes"] > candidacy["votes"] for other, _ in entries)
            candidacy["candidateCount"] = candidate_count
            candidacy["nominalVotes"] = total_nominal_votes
            candidacy["voteSharePct"] = round(100 * candidacy["votes"] / total_nominal_votes, 4) if total_nominal_votes else 0
            candidacy["leaderName"] = leader_name
            candidacy["leaderVotes"] = leader_votes
            candidacy["gapToLeaderVotes"] = leader_votes - candidacy["votes"]


def build() -> None:
    people: dict[str, dict] = {}
    valid_keys: set[str] = set()
    candidacy_refs: list[tuple[str, dict, str]] = []
    year_counts: dict[int, int] = defaultdict(int)
    office_counts: dict[tuple[int, str], int] = defaultdict(int)

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
        office_counts[(year, normalized(row["DS_CARGO"]))] += 1

    by_zone, totals = load_votes(valid_keys)
    for _, candidacy, key in candidacy_refs:
        candidacy["votes"] = totals.get(key, 0)
        candidacy["zones"] = [
            {"municipality": territory.rsplit("|", 1)[0], "zone": territory.rsplit("|", 1)[1], "votes": votes}
            for territory, votes in sorted(by_zone.get(key, {}).items())
        ]
    assign_competitive_metrics(candidacy_refs, people)

    for person in people.values():
        person["normalizedNames"] = sorted(person["normalizedNames"])
        person["candidacies"].sort(key=lambda item: (item["year"], item["office"], item["municipality"]))

    shards: dict[str, list[dict]] = defaultdict(list)
    for person in people.values():
        prefixes = {candidacy["number"].zfill(5)[:2] for candidacy in person["candidacies"]}
        for prefix in prefixes:
            shards[prefix].append(person)

    name_shards: dict[str, list[dict]] = defaultdict(list)
    for person in people.values():
        prefixes = sorted({item["number"].zfill(5)[:2] for item in person["candidacies"]})
        for alias in sorted(set(person["normalizedNames"])):
            name_shards[name_shard(alias)].append({
                "normalizedName": alias,
                "id": person["id"],
                "name": person["name"],
                "numberPrefixes": prefixes,
            })

    temporary = OUTPUT_DIR.with_name(OUTPUT_DIR.name + ".tmp")
    if temporary.exists():
        shutil.rmtree(temporary)
    (temporary / "number").mkdir(parents=True)
    (temporary / "name").mkdir(parents=True)
    for prefix, entries in sorted(shards.items()):
        entries.sort(key=lambda item: (item["name"], item["id"]))
        (temporary / "number" / f"{prefix}.json").write_text(
            json.dumps({"schemaVersion": 2, "candidates": entries}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
    for prefix, entries in sorted(name_shards.items()):
        entries.sort(key=lambda item: (item["normalizedName"], item["id"]))
        (temporary / "name" / f"{prefix}.json").write_text(
            json.dumps({"schemaVersion": 2, "entries": entries}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
    coverage = {
        str(year): {office.title(): office_counts[(year, office)] for office in sorted(ALLOWED_OFFICES)}
        for year in YEARS
    }
    manifest = {
        "schemaVersion": 2,
        "source": "Tribunal Superior Eleitoral - Dados Abertos",
        "scope": {"country": "BR", "state": "SP"},
        "generatedYears": list(YEARS),
        "offices": sorted(ALLOWED_OFFICES),
        "candidateCount": len(people),
        "candidacyCount": sum(year_counts.values()),
        "candidaciesByYear": {str(year): year_counts[year] for year in YEARS},
        "candidaciesByYearAndOffice": coverage,
        "shards": sorted(shards),
        "nameShards": sorted(name_shards),
        "identityRule": "normalized legal name plus birth date; exact legal and ballot names are searchable",
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
    sources = list((OUTPUT_DIR / "number").glob("*.json")) + list((OUTPUT_DIR / "name").glob("*.json"))
    for source in sorted(sources):
        target = source.with_suffix(source.suffix + ".gz")
        with source.open("rb") as input_stream, target.open("wb") as output_stream:
            with gzip.GzipFile(filename="", mode="wb", fileobj=output_stream, compresslevel=9, mtime=0) as compressed:
                shutil.copyfileobj(input_stream, compressed, length=1024 * 1024)
        print(f"{source.name}: {target.stat().st_size} bytes")


def enrich_existing_catalog() -> None:
    people: dict[str, dict] = {}
    for source in sorted((OUTPUT_DIR / "number").glob("*.json")):
        payload = json.loads(source.read_text(encoding="utf-8"))
        for person in payload["candidates"]:
            people.setdefault(person["id"], person)
    refs = [(person["id"], candidacy, "") for person in people.values() for candidacy in person["candidacies"]]
    assign_competitive_metrics(refs, people)
    prefixes: dict[str, list[dict]] = defaultdict(list)
    for person in people.values():
        for prefix in {item["number"].zfill(5)[:2] for item in person["candidacies"]}:
            prefixes[prefix].append(person)
    for prefix, entries in sorted(prefixes.items()):
        target = OUTPUT_DIR / "number" / f"{prefix}.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps({"schemaVersion": 1, "candidates": entries}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        os.replace(temporary, target)
    compress_existing_catalog()


def reindex_existing_catalog() -> None:
    """Add the exact-name index and auditable coverage metadata without rereading vote archives."""
    people: dict[str, dict] = {}
    for source in sorted((OUTPUT_DIR / "number").glob("*.json")):
        payload = json.loads(source.read_text(encoding="utf-8"))
        for person in payload["candidates"]:
            people.setdefault(person["id"], person)

    target_dir = OUTPUT_DIR / "name"
    temporary_dir = OUTPUT_DIR / "name.tmp"
    if temporary_dir.exists():
        shutil.rmtree(temporary_dir)
    temporary_dir.mkdir(parents=True)
    index: dict[str, list[dict]] = defaultdict(list)
    for person in people.values():
        prefixes = sorted({item["number"].zfill(5)[:2] for item in person["candidacies"]})
        for alias in sorted(set(person["normalizedNames"])):
            index[name_shard(alias)].append({
                "normalizedName": alias,
                "id": person["id"],
                "name": person["name"],
                "numberPrefixes": prefixes,
            })
    for prefix, entries in sorted(index.items()):
        entries.sort(key=lambda item: (item["normalizedName"], item["id"]))
        source = temporary_dir / f"{prefix}.json"
        source.write_text(
            json.dumps({"schemaVersion": 2, "entries": entries}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        with source.open("rb") as input_stream, source.with_suffix(".json.gz").open("wb") as output_stream:
            with gzip.GzipFile(filename="", mode="wb", fileobj=output_stream, compresslevel=9, mtime=0) as compressed:
                shutil.copyfileobj(input_stream, compressed, length=1024 * 1024)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    try:
        os.replace(temporary_dir, target_dir)
    except OSError:
        shutil.copytree(temporary_dir, target_dir)
        shutil.rmtree(temporary_dir)

    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    coverage: dict[str, dict[str, int]] = {str(year): {office.title(): 0 for office in sorted(ALLOWED_OFFICES)} for year in YEARS}
    seen_candidacies: set[tuple[str, int, str]] = set()
    for person in people.values():
        for candidacy in person["candidacies"]:
            key = (person["id"], int(candidacy["year"]), str(candidacy["sequence"]))
            if key in seen_candidacies:
                continue
            seen_candidacies.add(key)
            coverage[str(candidacy["year"])][normalized(candidacy["office"]).title()] += 1
    manifest.update({
        "schemaVersion": 2,
        "scope": {"country": "BR", "state": "SP"},
        "offices": sorted(ALLOWED_OFFICES),
        "candidaciesByYearAndOffice": coverage,
        "nameShards": sorted(index),
        "identityRule": "normalized legal name plus birth date; exact legal and ballot names are searchable",
    })
    temporary_manifest = manifest_path.with_suffix(".json.tmp")
    temporary_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary_manifest, manifest_path)
    print(json.dumps({"candidateCount": len(people), "candidacyCount": len(seen_candidacies), "nameShards": len(index)}, ensure_ascii=False))


if __name__ == "__main__":
    import sys
    if "--compress-existing" in sys.argv:
        compress_existing_catalog()
    elif "--enrich-existing" in sys.argv:
        enrich_existing_catalog()
    elif "--reindex-existing" in sys.argv:
        reindex_existing_catalog()
    else:
        build()
        compress_existing_catalog()
