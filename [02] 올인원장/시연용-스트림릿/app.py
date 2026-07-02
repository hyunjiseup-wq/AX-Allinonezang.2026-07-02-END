"""
올인원장 홍보 파이프라인 — 시연용 Streamlit 앱 (제출 저장소 제외 대상)

정제(clean_keywords.py)는 이 앱 안에서 실시간으로 직접 실행한다 (결정론적 스크립트, AI 호출 없음).
3채널 초안 생성은 Anthropic API(Claude)를 실시간으로 호출한다 — 현장 매니저 확인 하에,
시연 목적으로 실행 중 AI 호출을 사용한다. 규칙은 output/channel-strategy.md를 시스템 프롬프트로 그대로 사용한다.

과제 제출 규정(CLAUDE.md: "실행 중 외부 AI 호출 앱 금지", "대시보드·웹 UI 구현 제외")과 충돌하지 않도록,
이 폴더(시연용-스트림릿/)는 .gitignore에 의해 제출 저장소에서 자동 제외된다. 시연 전용 도구로만 사용할 것.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

import anthropic
import streamlit as st

APP_DIR = Path(__file__).parent
PROJECT_DIR = APP_DIR.parent
sys.path.insert(0, str(PROJECT_DIR / "scripts"))
from clean_keywords import clean  # noqa: E402  (실제 정제 스크립트 재사용)

st.set_page_config(page_title="올인원장 홍보 파이프라인", layout="wide")

CHANNEL_RULES = (PROJECT_DIR / "output" / "channel-strategy.md").read_text(encoding="utf-8")

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "blog_title": {"type": "string", "description": "블로그 제목"},
        "blog_body": {"type": "string", "description": "블로그 본문. 500자 이상, 소제목(H2) 2개 포함, 이모지·해시태그 없음"},
        "instagram": {"type": "string", "description": "150자 이내 캡션 + 해시태그 5개(#올인원장 #학원관리 고정 2개 + 연관 3개)"},
        "kakao": {"type": "string", "description": "180자 이내, 이모지 1~2개, 링크 포함"},
        "tone_note": {
            "type": "string",
            "description": "tone_hint가 규칙표(전문적인/따뜻한·친근한/밝은/긴급한/자랑스러운)에 없는 값일 경우, "
            "어떤 계열로 판단해 적용했는지 그 근거를 한 문장으로. 규칙표에 있는 값이면 빈 문자열.",
        },
    },
    "required": ["blog_title", "blog_body", "instagram", "kakao", "tone_note"],
    "additionalProperties": False,
}

DEMO_PRESETS = {
    "라이브 데모용 (5건 → 4건, live_demo_input.csv)": PROJECT_DIR / "demo" / "live_demo_input.csv",
    "Q&A 백업용 (8건 → 7건, dummy_keywords_input.csv)": PROJECT_DIR / "demo" / "dummy_keywords_input.csv",
}


@st.cache_resource
def get_client():
    api_key = None
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        pass  # secrets.toml이 아예 없으면 st.secrets 접근 자체가 예외를 던짐
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        st.error(
            "ANTHROPIC_API_KEY가 설정되어 있지 않습니다. "
            "`.streamlit/secrets.toml`에 `ANTHROPIC_API_KEY = \"...\"`를 추가하거나 "
            "환경변수로 설정해주세요."
        )
        st.stop()
    return anthropic.Anthropic(api_key=api_key)


def generate_channel_copy(client, row):
    """정제된 한 행(row)으로 3채널 초안을 실시간 생성한다. 실패 시 {'error': ...} 반환."""
    user_prompt = (
        f"id: {row['id']}\n"
        f"type: {row['type']}\n"
        f"keyword: {row['keyword']}\n"
        f"tone_hint: {row['tone_hint']}\n"
        f"brand_name: {row['brand_name']}\n"
        f"detail: {row['detail']}\n\n"
        "위 케이스로 블로그·인스타그램·카카오채널 3채널 홍보 초안을 채널별 규칙에 맞게 생성해줘."
    )
    try:
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=2000,
            system=[{"type": "text", "text": CHANNEL_RULES, "cache_control": {"type": "ephemeral"}}],
            output_config={"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.RateLimitError:
        return {"error": "API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요."}
    except anthropic.AuthenticationError:
        return {"error": "API 키가 유효하지 않습니다."}
    except anthropic.APIConnectionError:
        return {"error": "네트워크 연결 오류입니다. 인터넷 연결을 확인해주세요."}
    except anthropic.APIStatusError as e:
        return {"error": f"API 오류 ({e.status_code}): {e.message}"}

    if response.stop_reason == "refusal":
        return {"error": "모델이 이 요청을 거부했습니다 (안전 정책)."}

    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        return {"error": "생성 결과가 비어 있습니다."}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": "생성 결과를 파싱하지 못했습니다."}


st.title("키워드 → 채널별 홍보 초안 자동 생성")
st.caption(
    "정제는 이 화면에서 실시간으로 직접 실행됩니다 (AI 호출 없음). "
    "3채널 초안은 Claude API(claude-opus-4-8)를 실시간으로 호출해 생성합니다."
)

col_a, col_b = st.columns([2, 1])
with col_a:
    preset_label = st.radio("데모용 CSV 선택", list(DEMO_PRESETS.keys()), index=0)
    input_path = DEMO_PRESETS[preset_label]
with col_b:
    uploaded = st.file_uploader("또는 새 CSV 업로드", type="csv")
    if uploaded is not None:
        tmp = Path(tempfile.gettempdir()) / uploaded.name
        tmp.write_bytes(uploaded.getvalue())
        input_path = tmp

if st.button("① 정제 실행", type="primary"):
    st.session_state["cleaned_rows"], st.session_state["report"] = clean(input_path)
    st.session_state.pop("generated", None)

if "cleaned_rows" in st.session_state:
    rows = st.session_state["cleaned_rows"]
    report = st.session_state["report"]

    st.subheader("정제 결과 (실시간 실행)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("입력 → 정제", f"{report['total_input']} → {report['total_cleaned']}")
    m2.metric("중복 제거", f"{len(report['duplicates_removed'])}건")
    m3.metric("tone 정규화", f"{len(report['tone_normalized'])}건")
    m4.metric("결측 보완", f"{len(report['detail_filled'])}건")

    with st.expander("정제 상세 로그"):
        for dup_id, kept_id in report["duplicates_removed"]:
            st.write(f"- id {dup_id} → id {kept_id}와 완전 중복이라 제거")
        for rid, before, after in report["tone_normalized"]:
            st.write(f"- id {rid}: tone_hint \"{before}\" → \"{after}\" 정규화")
        for rid in report["detail_filled"]:
            st.write(f"- id {rid}: detail 결측 → 자동 보완")

    st.dataframe(rows, use_container_width=True)

    st.divider()
    if st.button("② 3채널 초안 생성 (Claude API 실시간 호출)"):
        client = get_client()
        st.session_state.setdefault("generated", {})
        progress = st.progress(0.0, text="생성 준비 중...")
        for i, row in enumerate(rows):
            progress.progress((i) / len(rows), text=f"#{row['id']} 생성 중...")
            st.session_state["generated"][row["id"]] = generate_channel_copy(client, row)
        progress.progress(1.0, text="완료")

    if st.session_state.get("generated"):
        st.subheader("채널별 홍보 초안")
        st.caption("🔴 Claude API 실시간 생성 결과 — 매 실행마다 새로 호출됩니다.")

        for row in rows:
            rid = row["id"]
            result = st.session_state["generated"].get(rid)
            st.markdown(
                f"### #{rid} · {row['type']} · {row['keyword']} · {row['brand_name']} "
                f"(tone: {row['tone_hint']})"
            )
            if not result:
                st.info("아직 생성되지 않았습니다.")
                st.divider()
                continue
            if "error" in result:
                st.error(result["error"])
                st.divider()
                continue

            if result.get("tone_note"):
                st.info(f"🧠 판단 포인트: {result['tone_note']}")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"**블로그 · 신뢰** ({len(result['blog_body'])}자)")
                st.markdown(f"**{result['blog_title']}**")
                st.text(result["blog_body"])
            with c2:
                st.markdown(f"**인스타그램 · 공감** ({len(result['instagram'])}자)")
                st.text(result["instagram"])
            with c3:
                st.markdown(f"**카카오채널 · 행동** ({len(result['kakao'])}자)")
                st.text(result["kakao"])
            st.divider()
