# 데이터 정제 리포트 — live_demo_input.csv

- 입력 5건 → 정제 후 4건

## 완전 중복 제거
- id 204 → id 201와 완전 중복(모든 컬럼 동일)이라 제거

## tone_hint 정규화
- 없음

## detail 결측 보완
- id 205: detail 비어 있어 type·keyword 기반 추론 문구로 대체 (`[추론: ...]` 표시)

## type 분포
- 신기능: 1건
- 이벤트: 2건
- 후기: 1건

정제된 데이터: `live_demo_input.cleaned.csv` — 이어서 `/insight` → `/generate` → `/review` 순으로 실행하세요.