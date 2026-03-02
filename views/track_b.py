import streamlit as st
from utils import load_data, display_cols, color_diff_yield

df_pension = load_data('data/asset_position_pension.csv')
df_irp = load_data('data/asset_position_irp.csv')

pension_total = df_pension['Actual'].sum() if not df_pension.empty else 0
irp_total = df_irp['Actual'].sum() if not df_irp.empty else 0
track_b_total = pension_total + irp_total

st.title("🏖️ 노후 준비 (15~20년 장기 목표)")
st.markdown("대한민국 상위 10% 진입을 위해 복리 효과를 극대화하는 **개인연금 및 IRP 계좌 중심**의 공격적 투자 공간입니다.")

m1, m2, m3 = st.columns(3)
m1.metric("🎯 노후 준비 총 자산 (연금+IRP)", f"{track_b_total:,.0f}원")
m2.metric("🟢 개인연금 자산", f"{pension_total:,.0f}원")
m3.metric("🔵 IRP 자산", f"{irp_total:,.0f}원")

st.divider()

st.subheader("1. 3층 연금 시뮬레이터")
irp_target = st.slider("개인연금+IRP 목표가액 (단위: 억 원)", 1, 20, 5)
monthly_total = (irp_target * 33) + 120 + 80
st.info(f"💡 목표가액 **{irp_target}억 원** 달성 시, 60대 중반 예상 월 현금 흐름은 **{monthly_total:,}만 원**입니다. (국민+퇴직+개인 합산)")

st.divider()

st.subheader("2. 개인연금 포트폴리오 현황")
if not df_pension.empty:
    cols_p = [c for c in display_cols if c in df_pension.columns]
    # 💡 subset에 존재하지 않는 컬럼이 들어가면 에러가 나므로, 실제 존재하는 컬럼만 필터링합니다.
    subset_p = [col for col in ['Difference', 'Yield'] if col in cols_p]
    
    styled_df_p = df_pension[cols_p].style.format({
        'Weight(%)': '{:.2f}%', 'Budget': '{:,.0f}', 'Actual': '{:,.0f}', 
        'Difference': '{:,.0f}', 'Yield(%)': '{:.2f}%'
    }).map(color_diff_yield, subset=subset_p)
    st.dataframe(styled_df_p, use_container_width=True)

st.write("")

st.subheader("3. IRP 포트폴리오 현황")
if not df_irp.empty:
    cols_i = [c for c in display_cols if c in df_irp.columns]
    # 💡 마찬가지로 IRP 테이블에도 적용합니다.
    subset_i = [col for col in ['Difference', 'Yield'] if col in cols_i]
    
    styled_df_i = df_irp[cols_i].style.format({
        'Weight(%)': '{:.2f}%', 'Budget': '{:,.0f}', 'Actual': '{:,.0f}', 
        'Difference': '{:,.0f}', 'Yield(%)': '{:.2f}%'
    }).map(color_diff_yield, subset=subset_i)
    st.dataframe(styled_df_i, use_container_width=True)