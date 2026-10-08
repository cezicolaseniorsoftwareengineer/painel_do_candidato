import csv
import io
import json
import os
import time
import unicodedata
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "votos_Bueno"
OUTPUT_DIR = SOURCE_DIR / "registros_completos"

ELECTIONS = {
    2022: {
        "zip": "bweb_1t_SP_051020221321.zip",
        "candidates": {
            "andre_bueno": {"number": "22010", "party": "PL", "office": "DEPUTADO ESTADUAL", "tokens": ("ANDRE", "BUENO"), "expected_records": 23779, "expected_votes": 61953},
        },
    },
    2024: {
        "zip": "bweb_1t_SP_091020241636.zip",
        "candidates": {
            "sandra_santana": {"number": "15456", "party": "MDB", "office": "VEREADOR", "tokens": ("SANDRA", "SANTANA"), "expected_records": 7123, "expected_votes": 38326},
        },
    },
    2026: {
        "zip": "bweb_1t_SP_051020261403(1).zip",
        "candidates": {
            "andre_bueno": {"number": "15777", "party": "MDB", "office": "DEPUTADO ESTADUAL", "tokens": ("ANDRE", "BUENO"), "expected_records": 31987, "expected_votes": 71664},
            "sandra_santana": {"number": "15456", "party": "MDB", "office": "DEPUTADO ESTADUAL", "tokens": ("SANDRA", "SANTANA"), "expected_records": 11846, "expected_votes": 44406},
        },
    },
}


def normalize(value):
    text = unicodedata.normalize("NFD", str(value).strip().upper())
    return "".join(char for char in text if unicodedata.category(char) != "Mn")


def open_csv_from_zip(path):
    archive = zipfile.ZipFile(path)
    member = next(info for info in archive.infolist() if info.filename.lower().endswith(".csv"))
    stream = io.TextIOWrapper(archive.open(member), encoding="latin1", errors="strict", newline="")
    return archive, stream


def extract_election(year, config):
    source_path = SOURCE_DIR / config["zip"]
    archive, stream = open_csv_from_zip(source_path)
    reader = csv.reader(stream, delimiter=";", quotechar='"')
    header = [column.strip().replace("\ufeff", "") for column in next(reader)]
    required = {"NR_VOTAVEL", "NM_VOTAVEL", "SG_PARTIDO", "DS_CARGO_PERGUNTA", "QT_VOTOS", "NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO"}
    missing = required.difference(header)
    if missing:
        raise RuntimeError(f"{source_path.name}: missing columns {sorted(missing)}")
    indexes = {column: header.index(column) for column in required}
    outputs = {}
    counters = {}
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        for slug, candidate in config["candidates"].items():
            final_path = OUTPUT_DIR / f"{slug}_{year}_registros_completos.csv"
            temp_path = final_path.with_suffix(".csv.tmp")
            handle = temp_path.open("w", encoding="utf-8-sig", newline="")
            writer = csv.writer(handle, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(header)
            outputs[slug] = (handle, writer, temp_path, final_path)
            counters[slug] = {"records": 0, "votes": 0}

        started = time.time()
        for line_number, row in enumerate(reader, start=1):
            if len(row) != len(header):
                raise RuntimeError(f"{source_path.name}: malformed row {line_number}")
            number = row[indexes["NR_VOTAVEL"]].strip()
            for slug, candidate in config["candidates"].items():
                if number != candidate["number"]:
                    continue
                if normalize(row[indexes["SG_PARTIDO"]]) != candidate["party"]:
                    continue
                if candidate["office"] not in normalize(row[indexes["DS_CARGO_PERGUNTA"]]):
                    continue
                name = normalize(row[indexes["NM_VOTAVEL"]])
                if not all(token in name for token in candidate["tokens"]):
                    continue
                outputs[slug][1].writerow(row)
                counters[slug]["records"] += 1
                counters[slug]["votes"] += int(row[indexes["QT_VOTOS"]])
            if line_number % 2_000_000 == 0:
                print(f"{year}: scanned={line_number:,} elapsed={(time.time()-started)/60:.1f} min", flush=True)
    except Exception:
        for handle, _, temp_path, _ in outputs.values():
            handle.close()
            temp_path.unlink(missing_ok=True)
        raise
    finally:
        stream.close()
        archive.close()

    audit = {}
    for slug, candidate in config["candidates"].items():
        handle, _, temp_path, final_path = outputs[slug]
        handle.close()
        actual = counters[slug]
        if actual["records"] != candidate["expected_records"] or actual["votes"] != candidate["expected_votes"]:
            temp_path.unlink(missing_ok=True)
            raise RuntimeError(f"{slug} {year}: reconciliation failed: {actual}")
        os.replace(temp_path, final_path)
        audit[slug] = {**actual, "columns": len(header), "file": final_path.name}
        print(f"{slug} {year}: records={actual['records']:,} votes={actual['votes']:,}", flush=True)
    return audit


def main():
    complete_audit = {}
    for year, config in ELECTIONS.items():
        complete_audit[str(year)] = extract_election(year, config)
    audit_path = OUTPUT_DIR / "audit.json"
    audit_path.write_text(json.dumps(complete_audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(audit_path)


if __name__ == "__main__":
    main()
