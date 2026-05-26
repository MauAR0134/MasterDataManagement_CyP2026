"""Utilidades comunes para ingesta, estandarizacion y entity resolution."""

from __future__ import annotations

import csv
import itertools
import re
import shutil
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

import mdm_config as cfg


FILE_RE = re.compile(
    r"^(transacciones|clinica|prescripciones)_(mexico|estados_unidos|espana)_(2023|2024|2025)\.csv$"
)


def ensure_dirs() -> None:
    for folder in [
        cfg.RAW_COPY_DIR,
        cfg.STAGING_DIR,
        cfg.STANDARDIZED_DIR,
        cfg.PROFILING_DIR,
        cfg.LINKAGE_DIR,
        cfg.MASTER_INDEX_DIR,
        cfg.RELATIONAL_DIR,
        cfg.MANUAL_REVIEW_DIR,
        cfg.SQL_DIR,
    ]:
        folder.mkdir(parents=True, exist_ok=True)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_rows(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and not fieldnames:
        path.write_text("", encoding="utf-8")
        return
    columns = fieldnames or list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def discover_files() -> list[dict[str, object]]:
    metadata = []
    for counter, path in enumerate(sorted(cfg.RAW_DIR.glob("*.csv")), start=1):
        match = FILE_RE.match(path.name)
        if not match:
            continue
        system, country, year = match.groups()
        metadata.append(
            {
                "file_id": f"FILE_{counter:03d}",
                "source_file": path.name,
                "source_system": system,
                "source_country": country,
                "source_year": int(year),
                "source_path": str(path),
            }
        )
    return metadata


def copy_raw(metadata: list[dict[str, object]]) -> None:
    for record in metadata:
        shutil.copy2(Path(str(record["source_path"])), cfg.RAW_COPY_DIR / str(record["source_file"]))


def normalize_text(value: object, letters_only: bool = False) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value).strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    pattern = r"[^a-zñ\s]" if letters_only else r"[^a-z0-9ñ\s]"
    return re.sub(r"\s+", " ", re.sub(pattern, " ", text)).strip()


def normalize_name(value: object) -> str:
    return normalize_text(value, letters_only=True)


def name_tokens(value: str) -> tuple[str, str, str]:
    tokens = value.split()
    if len(tokens) >= 3:
        return " ".join(tokens[:-2]), tokens[-2], tokens[-1]
    if len(tokens) == 2:
        return tokens[0], tokens[1], ""
    return (tokens[0], "", "") if tokens else ("", "", "")


def soundex(value: object) -> str:
    text = normalize_name(value).upper()
    if not text:
        return ""
    mapping = {
        **dict.fromkeys("BFPV", "1"),
        **dict.fromkeys("CGJKQSXZ", "2"),
        **dict.fromkeys("DT", "3"),
        "L": "4",
        **dict.fromkeys("MN", "5"),
        "R": "6",
    }
    result = [text[0]]
    previous = mapping.get(text[0], "")
    for char in text[1:]:
        digit = mapping.get(char, "")
        if digit and digit != previous:
            result.append(digit)
        previous = digit
    return ("".join(result) + "000")[:4]


def parse_date(value: object, country: str) -> str:
    if value is None or not str(value).strip():
        return ""
    text = str(value).strip()
    formats = [cfg.DATE_FORMATS_BY_SITE[country], "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]
    for date_format in formats:
        try:
            return datetime.strptime(text, date_format).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def days_between(later_iso: str, earlier_iso: str) -> int | None:
    if not later_iso or not earlier_iso:
        return None
    later = datetime.strptime(later_iso, "%Y-%m-%d")
    earlier = datetime.strptime(earlier_iso, "%Y-%m-%d")
    return (later - earlier).days


def normalize_phone(value: object) -> str:
    return re.sub(r"\D", "", str(value)) if value is not None and str(value).strip() else ""


def normalize_email(value: object) -> str:
    email = str(value).strip().lower() if value is not None else ""
    return email if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) else ""


def jaro_winkler(left: object, right: object) -> float:
    s1, s2 = str(left or ""), str(right or "")
    if s1 == s2:
        return 1.0 if s1 else 0.0
    if not s1 or not s2:
        return 0.0
    match_distance = max(len(s1), len(s2)) // 2 - 1
    s1_matches = [False] * len(s1)
    s2_matches = [False] * len(s2)
    matches = 0
    transpositions = 0
    for i, char in enumerate(s1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len(s2))
        for j in range(start, end):
            if s2_matches[j] or char != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break
    if not matches:
        return 0.0
    comparable1 = [s1[i] for i in range(len(s1)) if s1_matches[i]]
    comparable2 = [s2[i] for i in range(len(s2)) if s2_matches[i]]
    transpositions = sum(a != b for a, b in zip(comparable1, comparable2)) // 2
    jaro = (matches / len(s1) + matches / len(s2) + (matches - transpositions) / matches) / 3
    prefix = 0
    for a, b in zip(s1, s2):
        if a != b or prefix == 4:
            break
        prefix += 1
    return jaro + prefix * 0.1 * (1 - jaro)


def exact_score(left: object, right: object) -> float:
    return 1.0 if str(left or "") and str(left or "") == str(right or "") else 0.0


def mode(values: list[str]) -> str:
    clean = [value for value in values if value]
    if not clean:
        return ""
    return Counter(clean).most_common(1)[0][0]


def pairs_in_group(indexes: list[int]) -> set[tuple[int, int]]:
    return set(itertools.combinations(sorted(indexes), 2))


class UnionFind:
    def __init__(self, indexes: list[int]) -> None:
        self.parent = {index: index for index in indexes}

    def find(self, index: int) -> int:
        while self.parent[index] != index:
            self.parent[index] = self.parent[self.parent[index]]
            index = self.parent[index]
        return index

    def union(self, left: int, right: int) -> None:
        root_left, root_right = self.find(left), self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left
