# 데이터 정제 리포트 — dummy_keywords_input.csv

- 입력 8건 → 정제 후 7건

## 완전 중복 제거
- id 105 → id 101와 완전 중복(모든 컬럼 동일)이라 제거

## tone_hint 정규화
- id 102: "친근스러운" → "친근한"
- id 106: "긴박" → "긴급한"
- id 108: "자랑스런" → "자랑스러운"

## detail 결측 보완
- id 104: detail 비어 있어 type·keyword 기반 추론 문구로 대체 (`[추론: ...]` 표시)
- id 107: detail 비어 있어 type·keyword 기반 추론 문구로 대체 (`[추론: ...]` 표시)

## type 분포
- 신기능: 2건
- 이벤트: 3건
- 후기: 2건

정제된 데이터: `dummy_keywords_input.cleaned.csv` — 이어서 `/insight` → `/generate` → `/review` 순으로 실행하세요.