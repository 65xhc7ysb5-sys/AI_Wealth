import streamlit as st
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

st.set_page_config(page_title="Linchpin Wealth", page_icon="🎯", layout="wide")

st.sidebar.title("🎯 Linchpin Wealth")
st.sidebar.markdown("대한민국 상위 10%를 위한 AI 자산관리")
st.sidebar.divider()

# 페이지 라우팅 설정
pages = {
    "메인 대시보드": [
        st.Page("views/home.py", title="🏠 홈 대시보드"),
    ],
    "목표 기반 포트폴리오": [
        st.Page("views/track_a.py", title="🏠 Track A: 내집 마련 (ISA)"),
        st.Page("views/track_b.py", title="🏖️ Track B: 노후 준비 (연금+IRP)"),
    ],
    "전문가 코칭": [
        st.Page("views/ai_coach.py", title="💬 AI 수석 코치 (지식 RAG)")
    ]
}

pg = st.navigation(pages)

st.sidebar.divider()
st.sidebar.caption("© 2026 Linchpin Wealth MVP")

pg.run()