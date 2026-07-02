"""
새 keywords_input.csv를 넣고 실행하면 결측·중복·표기 흔들림을 정리한 cleaned CSV와
정제 리포트를 만들어 준다. /generate 실행 전 전처리 단계.

사용법:
    python scripts/clean_keywords.py data/keywords_input.csv

출력:
    data/keywords_input.cleaned.csv
    data/cleaning_report.md
"""
import csv
import sys
import re
from pathlib import Path
from collections import Counter

# 표기가 흔들릴 수 있는 tone_hint 값을 표준 톤으로 정규화하는 표
# "긴박" 같이 어미가 빠진 표기, 유사어를 표준형으로 매핑한다.
TONE_CANON = {
    "전문적인": "전문적인", "전문적": "전문적인",
    "따뜻한": "따뜻한", "따뜻": "따뜻한",
    "긴급한": "긴급한", "긴급": "긴급한", "긴박": "긴급한", "긴박한": "긴급한",
    "자랑스러운": "자랑스러운", "자랑스런": "자랑스러운",
    "밝은": "밝은",
    "친근한": "친근한", "친근": "친근한",
}

REQUIRED_COLUMNS = ["id", "type", "keyword", "tone_hint", "brand_name", "detail"]


def normalize_tone(raw: str) -> tuple[str, bool]:
    """(정규화된 tone, 원본과 달랐는지 여부)를 반환한다."""
    raw = raw.strip()
    if raw in TONE_CANON:
        canon = TONE_CANON[raw]
        return canon, canon != raw
    # 사전에 없는 값은 어미(-한/-운 등)를 뗀 어간으로 재시도
    stem = re.sub(r"(한|운|런|스러운)$", "", raw)
    for known, canon in TONE_CANON.items():
        if known.startswith(stem) and stem:
            return canon, canon != raw
    return raw, False  # 알 수 없는 톤은 그대로 두되 원본 유지


def infer_detail(row: dict) -> str:
    """detail이 비어 있을 때 type·keyword로 대체 문구를 생성한다."""
    return f"[추론: {row['type']} 콘텐츠 — 핵심 키워드({row['keyword']}) 기반으로 자동 보완, 원본 detail 없음]"


def clean(input_path: Path):
    with input_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"필수 컬럼 누락: {missing}")
        rows = list(reader)

    seen_signatures = {}
    duplicates_removed = []
    tone_normalized = []
    detail_filled = []
    cleaned_rows = []

    for row in rows:
        signature = tuple(row[c].strip() for c in ["type", "keyword", "tone_hint", "brand_name", "detail"])
        if signature in seen_signatures:
            duplicates_removed.append((row["id"], seen_signatures[signature]))
            continue
        seen_signatures[signature] = row["id"]

        canon_tone, changed = normalize_tone(row["tone_hint"])
        if changed:
            tone_normalized.append((row["id"], row["tone_hint"], canon_tone))
        row["tone_hint"] = canon_tone

        if not row["detail"].strip():
            detail_filled.append(row["id"])
            row["detail"] = infer_detail(row)

        cleaned_rows.append(row)

    type_counts = Counter(r["type"].strip() for r in cleaned_rows)

    return cleaned_rows, {
        "total_input": len(rows),
        "total_cleaned": len(cleaned_rows),
        "duplicates_removed": duplicates_removed,
        "tone_normalized": tone_normalized,
        "detail_filled": detail_filled,
        "type_counts": type_counts,
    }


def write_outputs(input_path: Path, cleaned_rows, report):
    out_csv = input_path.with_name(input_path.stem + ".cleaned.csv")
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(cleaned_rows)

    out_report = input_path.parent / "cleaning_report.md"
    lines = [
        f"# 데이터 정제 리포트 — {input_path.name}",
        "",
        f"- 입력 {report['total_input']}건 → 정제 후 {report['total_cleaned']}건",
        "",
        "## 완전 중복 제거",
    ]
    if report["duplicates_removed"]:
        for dup_id, kept_id in report["duplicates_removed"]:
            lines.append(f"- id {dup_id} → id {kept_id}와 완전 중복(모든 컬럼 동일)이라 제거")
    else:
        lines.append("- 없음")

    lines += ["", "## tone_hint 정규화"]
    if report["tone_normalized"]:
        for rid, before, after in report["tone_normalized"]:
            lines.append(f"- id {rid}: \"{before}\" → \"{after}\"")
    else:
        lines.append("- 없음")

    lines += ["", "## detail 결측 보완"]
    if report["detail_filled"]:
        for rid in report["detail_filled"]:
            lines.append(f"- id {rid}: detail 비어 있어 type·keyword 기반 추론 문구로 대체 (`[추론: ...]` 표시)")
    else:
        lines.append("- 없음")

    lines += ["", "## type 분포"]
    for t, n in report["type_counts"].items():
        lines.append(f"- {t}: {n}건")

    lines += ["", f"정제된 데이터: `{out_csv.name}` — 이어서 `/insight` → `/generate` → `/review` 순으로 실행하세요."]

    out_report.write_text("\n".join(lines), encoding="utf-8")
    return out_csv, out_report


def main():
    if len(sys.argv) != 2:
        print("사용법: python scripts/clean_keywords.py <keywords_input.csv 경로>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    cleaned_rows, report = clean(input_path)
    out_csv, out_report = write_outputs(input_path, cleaned_rows, report)

    print(f"입력 {report['total_input']}건 → 정제 후 {report['total_cleaned']}건")
    print(f"중복 제거: {len(report['duplicates_removed'])}건")
    print(f"tone_hint 정규화: {len(report['tone_normalized'])}건")
    print(f"detail 보완: {len(report['detail_filled'])}건")
    print(f"→ {out_csv}")
    print(f"→ {out_report}")


if __name__ == "__main__":
    main()
