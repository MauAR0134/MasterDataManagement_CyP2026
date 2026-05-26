"""Multipass record linkage, scoring, clustering y Master Patient Index."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime

import mdm_config as cfg
from mdm_utils import UnionFind, exact_score, jaro_winkler, mode, pairs_in_group, read_rows, write_rows


def generate_candidates(records: list[dict[str, str]]) -> dict[tuple[int, int], set[str]]:
    candidates: dict[tuple[int, int], set[str]] = defaultdict(set)
    for blocking_pass in cfg.BLOCKING_PASSES:
        grouped: dict[tuple[str, ...], list[int]] = defaultdict(list)
        columns = blocking_pass["columns"]
        required = blocking_pass.get("require_non_null", columns)
        for index, row in enumerate(records):
            if any(not row.get(column, "") for column in required):
                continue
            key = tuple(row.get(column, "") for column in columns)
            grouped[key].append(index)
        for indexes in grouped.values():
            for pair in pairs_in_group(indexes):
                candidates[pair].add(blocking_pass["name"])

    if cfg.SORTED_NEIGHBORHOOD["enabled"]:
        partitioned: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for index, row in enumerate(records):
            partitioned[row[cfg.SORTED_NEIGHBORHOOD["partition"]]].append(
                (row[cfg.SORTED_NEIGHBORHOOD["sort_key"]], index)
            )
        window = cfg.SORTED_NEIGHBORHOOD["window"]
        for sorted_rows in partitioned.values():
            sorted_rows.sort()
            for position, (_, left_index) in enumerate(sorted_rows):
                for _, right_index in sorted_rows[position + 1 : position + window]:
                    pair = tuple(sorted((left_index, right_index)))
                    candidates[pair].add("sorted_neighborhood_full_name")
    return candidates


def contact_score(left: dict[str, str], right: dict[str, str]) -> float:
    same_phone = bool(left["phone_std"] and left["phone_std"] == right["phone_std"])
    same_email = bool(left["email_std"] and left["email_std"] == right["email_std"])
    return 1.0 if same_phone or same_email else 0.0


def evaluate_pair(left_index: int, right_index: int, records: list[dict[str, str]], passes: set[str]) -> dict[str, object]:
    left, right = records[left_index], records[right_index]
    full_name_score = jaro_winkler(left["full_name_std"], right["full_name_std"])
    birth_date_score = exact_score(left["birth_date_iso"], right["birth_date_iso"])
    sex_score = exact_score(left["sex"], right["sex"])
    last_names_score = (
        jaro_winkler(left["apellido1_std"], right["apellido1_std"])
        + jaro_winkler(left["apellido2_std"], right["apellido2_std"])
    ) / 2
    contacts_score = contact_score(left, right)
    score = (
        full_name_score * cfg.MATCH_WEIGHTS["full_name"]
        + birth_date_score * cfg.MATCH_WEIGHTS["birth_date"]
        + sex_score * cfg.MATCH_WEIGHTS["sex"]
        + last_names_score * cfg.MATCH_WEIGHTS["last_names"]
        + contacts_score * cfg.MATCH_WEIGHTS["contact"]
    )
    dob_conflict = bool(left["birth_date_iso"] and right["birth_date_iso"] and left["birth_date_iso"] != right["birth_date_iso"])
    sex_conflict = bool(left["sex"] and right["sex"] and left["sex"] != right["sex"])
    other_elements_pass = birth_date_score == 1 and full_name_score >= 0.95 and last_names_score >= 0.95
    supported_same_dob_surnames = (
        birth_date_score == 1
        and sex_score == 1
        and last_names_score == 1
        and full_name_score >= cfg.SUPPORTED_MATCH_RULES["same_dob_last_names_min_name"]
    )
    supported_same_dob_contact = birth_date_score == 1 and sex_score == 1 and contacts_score == 1
    supported_dob_conflict = (
        dob_conflict
        and sex_score == 1
        and contacts_score == 1
        and full_name_score >= cfg.SUPPORTED_MATCH_RULES["dob_conflict_min_name"]
        and last_names_score >= cfg.SUPPORTED_MATCH_RULES["dob_conflict_min_last_names"]
    )
    incompatible_dob_conflict = (
        dob_conflict
        and contacts_score == 1
        and (sex_score == 0 or (full_name_score < 0.70 and last_names_score < 0.70))
    )

    if supported_dob_conflict:
        classification = "auto_match_dob_conflict"
    elif incompatible_dob_conflict:
        classification = "no_match_dob_conflict_name_incompatible"
    elif dob_conflict and contacts_score == 1.0:
        classification = "manual_review_dob_conflict"
    elif dob_conflict:
        classification = "no_match_dob_conflict_not_plausible"
    elif sex_conflict and other_elements_pass and score >= cfg.LINKAGE_THRESHOLDS["auto_match"]:
        classification = "auto_match_sex_error"
    elif supported_same_dob_surnames:
        classification = "auto_match_supported_dob_surnames"
    elif supported_same_dob_contact:
        classification = "auto_match_supported_dob_contact"
    elif score >= cfg.LINKAGE_THRESHOLDS["auto_match"]:
        classification = "auto_match"
    elif score >= cfg.LINKAGE_THRESHOLDS["manual_review_min"]:
        classification = "manual_review_score"
    else:
        classification = "no_match"

    return {
        "left_index": left_index,
        "right_index": right_index,
        "left_id_consulta": left["id_consulta"],
        "right_id_consulta": right["id_consulta"],
        "left_id_consulta_original": left["id_consulta_original"],
        "right_id_consulta_original": right["id_consulta_original"],
        "left_record_key": left["consultation_record_key"],
        "right_record_key": right["consultation_record_key"],
        "left_name": left["full_name_std"],
        "right_name": right["full_name_std"],
        "left_dob": left["birth_date_iso"],
        "right_dob": right["birth_date_iso"],
        "left_sex": left["sex"],
        "right_sex": right["sex"],
        "blocking_passes": " | ".join(sorted(passes)),
        "full_name_score": round(full_name_score, 4),
        "birth_date_score": round(birth_date_score, 4),
        "sex_score": round(sex_score, 4),
        "last_names_score": round(last_names_score, 4),
        "contact_score": round(contacts_score, 4),
        "total_score": round(score, 4),
        "classification": classification,
    }


def dob_survivorship(cluster_rows: list[dict[str, str]]) -> tuple[str, str, str]:
    observed = sorted(set(row["birth_date_iso"] for row in cluster_rows if row["birth_date_iso"]))
    if not observed:
        return "", "MISSING", ""
    if len(observed) == 1:
        return observed[0], "VALID", observed[0]
    counts = Counter(row["birth_date_iso"] for row in cluster_rows if row["birth_date_iso"])
    most_common = counts.most_common()
    canonical = most_common[0][0] if len(most_common) == 1 or most_common[0][1] > most_common[1][1] else ""
    return canonical, "DOB_CONFLICT", " | ".join(observed)


def build_master_id(cluster_rows: list[dict[str, str]], canonical_dob: str) -> str:
    canonical_name = max((row["full_name_std"] for row in cluster_rows), key=lambda value: (len(value), value))
    canonical_record = next(row for row in cluster_rows if row["full_name_std"] == canonical_name)
    first = canonical_record["nombre_std"][:2].upper().ljust(2, "X")
    paternal = canonical_record["apellido1_std"][:2].upper().ljust(2, "X")
    maternal = canonical_record["apellido2_std"][:2].upper().ljust(2, "X")
    sex = mode([row["sex"] for row in cluster_rows]) or "X"
    valid_registrations = sorted(row["fecha_primer_registro_iso"] for row in cluster_rows if row["fecha_primer_registro_iso"])
    first_registration = valid_registrations[0] if valid_registrations else "1900-01-01"
    dob_part = datetime.strptime(canonical_dob, "%Y-%m-%d").strftime("%d%m%Y") if canonical_dob else "00000000"
    reg_part = datetime.strptime(first_registration, "%Y-%m-%d").strftime("%m%Y")
    return f"{first}{paternal}{maternal}_{dob_part}{sex}_{reg_part}"


def main() -> None:
    records = read_rows(cfg.LINKAGE_DIR / "consultation_identity_records.csv")
    candidates = generate_candidates(records)
    scores = [evaluate_pair(left, right, records, passes) for (left, right), passes in candidates.items()]
    write_rows(cfg.LINKAGE_DIR / "patient_candidate_pairs_scored.csv", scores)

    blocking_summary = []
    for blocking_pass in [entry["name"] for entry in cfg.BLOCKING_PASSES] + ["sorted_neighborhood_full_name"]:
        pass_scores = [row for row in scores if blocking_pass in str(row["blocking_passes"]).split(" | ")]
        blocking_summary.append(
            {
                "blocking_pass": blocking_pass,
                "candidate_pairs": len(pass_scores),
                "auto_matches": sum(str(row["classification"]).startswith("auto_match") for row in pass_scores),
                "manual_review": sum(str(row["classification"]).startswith("manual_review") for row in pass_scores),
                "no_matches": sum(str(row["classification"]).startswith("no_match") for row in pass_scores),
            }
        )
    write_rows(cfg.LINKAGE_DIR / "blocking_pass_summary.csv", blocking_summary)

    manual = [row for row in scores if str(row["classification"]).startswith("manual_review")]
    sex_errors = [row for row in scores if row["classification"] == "auto_match_sex_error"]
    dob_errors = [row for row in scores if row["classification"] == "auto_match_dob_conflict"]
    dob_rejected = [row for row in scores if row["classification"] == "no_match_dob_conflict_name_incompatible"]
    write_rows(cfg.MANUAL_REVIEW_DIR / "posibles_matches_revision_manual.csv", manual)
    write_rows(cfg.MANUAL_REVIEW_DIR / "conflictos_dob.csv", [row for row in manual if row["classification"] == "manual_review_dob_conflict"])
    write_rows(cfg.MANUAL_REVIEW_DIR / "dob_conflictos_auto_resueltos.csv", dob_errors)
    write_rows(cfg.MANUAL_REVIEW_DIR / "dob_conflictos_descartados_por_nombre.csv", dob_rejected)
    write_rows(cfg.MANUAL_REVIEW_DIR / "errores_sexo_auto_resueltos.csv", sex_errors)

    union_find = UnionFind(list(range(len(records))))
    for score in scores:
        if str(score["classification"]).startswith("auto_match"):
            union_find.union(int(score["left_index"]), int(score["right_index"]))
    clusters: dict[int, list[dict[str, str]]] = defaultdict(list)
    for index, record in enumerate(records):
        clusters[union_find.find(index)].append(record)

    master_rows = []
    consultation_mapping = []
    used_master_ids: dict[str, int] = defaultdict(int)
    collisions = []
    for cluster_number, cluster_rows in enumerate(clusters.values(), start=1):
        canonical_dob, dob_status, dob_values_observed = dob_survivorship(cluster_rows)
        base_id = build_master_id(cluster_rows, canonical_dob)
        used_master_ids[base_id] += 1
        id_master = base_id if used_master_ids[base_id] == 1 else f"{base_id}_{used_master_ids[base_id]:02d}"
        if id_master != base_id:
            collisions.append({"base_id_master": base_id, "assigned_id_master": id_master, "cluster_number": cluster_number})
        canonical_name = max((row["full_name_std"] for row in cluster_rows), key=lambda value: (len(value), value))
        master_rows.append(
            {
                "id_master": id_master,
                "nombre_completo": canonical_name,
                "birth_date": canonical_dob,
                "dob_conflict": int(dob_status == "DOB_CONFLICT"),
                "birth_date_status": dob_status,
                "birth_dates_observed": dob_values_observed,
                "sex": mode([row["sex"] for row in cluster_rows]),
                "country_observed": " | ".join(sorted(set(row["source_country"] for row in cluster_rows))),
                "consultation_records": len(cluster_rows),
                "fhir_equivalent": "Patient",
            }
        )
        for row in cluster_rows:
            consultation_mapping.append(
                {
                    "id_consulta": row["id_consulta"],
                    "consultation_record_key": row["consultation_record_key"],
                    "id_master": id_master,
                    "cluster_number": cluster_number,
                }
            )
    write_rows(cfg.MASTER_INDEX_DIR / "Clientes_Patient.csv", master_rows)
    write_rows(cfg.MASTER_INDEX_DIR / "consultation_to_master_mapping.csv", consultation_mapping)
    write_rows(cfg.MANUAL_REVIEW_DIR / "id_master_collisions.csv", collisions)
    (cfg.MASTER_INDEX_DIR / "README.md").write_text(
        "# Master Patient Index\n\n"
        "Contiene la entidad `Clientes_Patient` y el mapeo de consultas hacia `id_master`. "
        "El identificador sigue `NoApAp_ddmmyyyyS_mmyyyy`. Las reglas de matching y sus "
        "umbrales estan centralizadas en `05_Scripts_MDM/mdm_config.py`.\n\n"
        "Survivorship aplicado: nombre estandarizado mas largo; DOB y sexo por valor mas "
        "frecuente. Cuando DOB tiene empate conflictivo, queda vacia en Patient, se marca "
        "`DOB_CONFLICT` y se conservan sus valores observados. Conflictos no concluyentes "
        "y scores intermedios permanecen en `manual_review`.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
