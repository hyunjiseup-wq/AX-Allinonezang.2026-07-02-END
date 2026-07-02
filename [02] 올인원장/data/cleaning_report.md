# 데이터 정제 리포트 — keywords_input.csv

- 입력 25건 → 정제 후 24건

## 완전 중복 제거
- id 025 → id 001와 완전 중복(모든 컬럼 동일)이라 제거

## tone_hint 정규화
- id 017: "긴박" → "긴급한"

## detail 결측 보완
- id 012: detail 비어 있어 type·keyword 기반 추론 문구로 대체 (`[추론: ...]` 표시)
- id 020: detail 비어 있어 type·keyword 기반 추론 문구로 대체 (`[추론: ...]` 표시)

## type 분포
- 신기능: 8건
- 이벤트: 8건
- 후기: 8건

정제된 데이터: `keywords_input.cleaned.csv` — 이어서 `/insight` → `/generate` → `/review` 순으로 실행하세요.