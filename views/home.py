import streamlit as st
from utils import load_data

# 데이터 로드
df_isa = load_data('data/asset_position_isa.csv')
df_pension = load_data('data/asset_position_pension.csv')
df_irp = load_data('data/asset_position_irp.csv')

isa_total = df_isa['Actual'].sum() if not df_isa.empty else 0
pension_total = df_pension['Actual'].sum() if not df_pension.empty else 0
irp_total = df_irp['Actual'].sum() if not df_irp.empty else 0
total_actual_krw = isa_total + pension_total + irp_total

st.title("전체 자산 요약 대시보드")
st.markdown("정훈 님의 전체 자산 현황과 오늘의 시장 핵심 인사이트를 확인하세요.")

col1, col2, col3, col4 = st.columns(4)
col1.metric("총 순자산 (KRW)", f"{total_actual_krw:,.0f}원")
col2.metric("ISA (내집마련)", f"{isa_total:,.0f}원")
col3.metric("개인연금", f"{pension_total:,.0f}원")
col4.metric("IRP", f"{irp_total:,.0f}원")

st.divider()
st.subheader("📰 오늘의 AI 마켓 브리핑")
news1, news2 = st.columns(2)
with news1:
    st.info("**[뉴스] 美 S&P500 역대 최고치 경신, AI 랠리 지속**\n\n*AI 코치 코멘트:* 연금/IRP 계좌 내 S&P500 비중이 긍정적인 수혜를 받고 있습니다. 멘탈을 유지하며 장기 투자를 이어가세요.")
with news2:
    st.warning("**[뉴스] 한국은행, 기준금리 인하 시기 연기 시사**\n\n*AI 코치 코멘트:* 고금리 장기화는 ISA 계좌의 단기 방어형 포트폴리오(파킹형 ETF 등)에 유리한 환경입니다.")