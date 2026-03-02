import streamlit as st
import time
from utils import load_data, display_cols, color_diff_yield

df_isa = load_data('data/asset_position_isa.csv')
isa_total = df_isa['Actual'].sum() if not df_isa.empty else 0

st.title("🏠 내집 마련 (3~5년 단기 목표)")
st.markdown("단기 변동성을 방어하고 시드머니를 지키는 **ISA 계좌 중심**의 전략 공간입니다.")

col_tgt, _ = st.columns([1, 1])
with col_tgt:
    st.info(f"💡 **현재 ISA 계좌 총 자산: {isa_total:,.0f}원**")

st.subheader("1. 아파트 목표가 설정")
apt_query = st.text_input("아파트 단지명 검색 (예: 반포동 아크로리버파크):")
if st.button("실거래가 검색"):
    with st.spinner("부동산 데이터를 불러오는 중..."):
        time.sleep(1)
        target_price = 42 if "반포" in apt_query or "아크로" in apt_query else 18
        st.success(f"✅ **{apt_query if apt_query else '선택한 아파트'}**의 목표가액은 **{target_price}억 원**입니다.")
        total_krw = 43000000 # 추후 전체 합산 연동 가능
        achievement_rate = min((total_krw / (target_price * 100000000)) * 100, 100)
        st.progress(int(achievement_rate))
        st.caption(f"현재 총자산 대비 달성률: {achievement_rate:.1f}%")

st.divider()
st.subheader("2. ISA 포트폴리오 현황")
if not df_isa.empty:
    cols_to_show = [c for c in display_cols if c in df_isa.columns]
    styled_df_isa = df_isa[cols_to_show].style.format({'Weight(%)': '{:.2f}%', 'Budget': '{:,.0f}', 'Actual': '{:,.0f}', 'Difference': '{:,.0f}', 'Yield(%)': '{:.2f}%'}).map(color_diff_yield, subset=['Difference'] if 'Yield(%)' not in cols_to_show else ['Difference', 'Yield(%)'])
    st.dataframe(styled_df_isa, use_container_width=True)
else:
    st.warning("asset_position_isa.csv 데이터가 없습니다.")