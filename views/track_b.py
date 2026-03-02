import streamlit as st
import pandas as pd
import yfinance as yf
import altair as alt
from utils import load_data, color_diff_yield

# ==========================================
# ⚙️ 보조 함수: 실시간 시세 조회 및 포트폴리오 처리
# ==========================================
def get_live_price(ticker):
    try:
        ks_ticker = f"{ticker}.KS"
        stock = yf.Ticker(ks_ticker)
        todays_data = stock.history(period='1d')
        if not todays_data.empty:
            return float(todays_data['Close'].iloc[-1])
    except:
        pass
    return None

def process_portfolio(df):
    """데이터프레임의 실시간 가격, 손익, 비중을 계산하여 반환하는 헬퍼 함수"""
    if df.empty:
        return df, 0
        
    live_prices = {}
    live_actuals = []
    
    for ticker, row in df.iterrows():
        live_price = get_live_price(ticker)
        current_unit = row.get('Unit', 0)
        if live_price:
            live_actuals.append(current_unit * live_price)
            live_prices[ticker] = live_price
        else:
            live_actuals.append(row['Actual'])
            live_prices[ticker] = row['Actual'] / current_unit if current_unit > 0 else 0
            
    df['Live Price'] = [live_prices.get(t, 0) for t in df.index]
    df['Actual'] = live_actuals
    df['Profit/Loss'] = df['Actual'] - df['Budget'] 
    df['Yield(%)'] = df.apply(lambda x: (x['Profit/Loss'] / x['Budget'] * 100) if x['Budget'] > 0 else 0, axis=1)

    total_actual = df['Actual'].sum()
    df['Current Weight(%)'] = (df['Actual'] / total_actual * 100).fillna(0)
    
    return df, total_actual

# ==========================================
# 📊 데이터 로드 및 실시간 지표 계산 (IRP + 연금저축 통합)
# ==========================================
df_irp_raw = load_data('data/asset_position_irp.csv')
df_pension_raw = load_data('data/asset_position_pension.csv')

# 각각의 포트폴리오를 실시간 데이터로 갱신
df_irp, irp_total = process_portfolio(df_irp_raw)
df_pension, pension_total = process_portfolio(df_pension_raw)

# 💡 두 계좌의 총합 (은퇴 시뮬레이션용 핵심 자산)
total_personal_assets = irp_total + pension_total

# 통합 시각화용 데이터프레임 만들기
df_combined = pd.DataFrame()
if not df_irp.empty or not df_pension.empty:
    df_combined = pd.concat([df_irp.assign(Account='IRP'), df_pension.assign(Account='연금저축')])
    if not df_combined.empty:
        df_combined['Total Weight(%)'] = (df_combined['Actual'] / total_personal_assets * 100).fillna(0)

# ==========================================
# 🖥️ UI 렌더링 시작
# ==========================================
st.title("🏖️ 은퇴 설계 (상위 10% 노후 준비)")
st.markdown("안정적인 배당과 장기 우상향에 투자하는 **연금 3층탑(개인/국민/퇴직) 종합 관리** 공간입니다.")

# ------------------------------------------
# 1. ⚙️ 은퇴 변수 및 3층 연금탑 설정
# ------------------------------------------
with st.expander("⚙️ 나의 은퇴 프로필 및 3층 연금 납입액 설정", expanded=True):
    st.info("💡 통계청 기준 상위 10% 가구의 적정 노후 생활비는 **현재 가치 기준 월 500만 원**입니다.")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    current_age = col_p1.number_input("현재 나이 (세)", value=35, step=1)
    retire_age = col_p2.number_input("목표 은퇴 나이 (세)", value=60, step=1)
    target_monthly_income = col_p3.number_input("목표 월 생활비 (현재 가치, 원)", value=5000000, step=500000)
    st.markdown(f"<div style='color: #2980b9; font-weight: bold; margin-top: -10px; margin-bottom: 15px; text-align: right;'>₩ {target_monthly_income:,.0f} ({target_monthly_income/10000:,.0f}만)</div>", unsafe_allow_html=True)
    
    st.write("---")
    st.write("💰 **현재 보유 연금 및 월 납입액 설정 (3층탑)**")
    
    col_v1, col_v2, col_v3 = st.columns(3)
    
    with col_v1:
        st.markdown("**(1) 개인연금 + IRP**")
        st.success(f"💼 합산 포트폴리오 잔액: **{total_personal_assets/10000:,.0f} 만 원**")
        irp_monthly = st.number_input("합산 월 예상 납입액 (원)", value=500000, step=100000, key="irp_m")
        st.markdown(f"<div style='color: #2980b9; font-weight: bold; margin-top: -10px; margin-bottom: 15px;'>₩ {irp_monthly:,.0f} ({irp_monthly/10000:,.0f}만)</div>", unsafe_allow_html=True)
        
    with col_v2:
        st.markdown("**(2) 국민연금**")
        st.info("💡 국민연금공단 예상수령액 기준")
        national_pension = st.number_input("예상 월 수령액 (현재 가치, 원)", value=1500000, step=100000, key="np_m")
        st.markdown(f"<div style='color: #2980b9; font-weight: bold; margin-top: -10px; margin-bottom: 15px;'>₩ {national_pension:,.0f} ({national_pension/10000:,.0f}만)</div>", unsafe_allow_html=True)
        
    with col_v3:
        st.markdown("**(3) 퇴직연금 (DC)**")
        dc_balance = st.number_input("현재 포트폴리오 잔액 (원)", value=30000000, step=5000000, key="dc_b")
        st.markdown(f"<div style='color: #2980b9; font-weight: bold; margin-top: -10px; margin-bottom: 15px;'>₩ {dc_balance:,.0f} ({dc_balance/10000:,.0f}만)</div>", unsafe_allow_html=True)
        dc_monthly = st.number_input("월 예상 납입액 (원)", value=500000, step=100000, key="dc_m")
        st.markdown(f"<div style='color: #2980b9; font-weight: bold; margin-top: -10px; margin-bottom: 15px;'>₩ {dc_monthly:,.0f} ({dc_monthly/10000:,.0f}만)</div>", unsafe_allow_html=True)

    st.write("---")
    st.write("📈 **시뮬레이션 환경 변수**")
    col_r1, col_r2 = st.columns(2)
    expected_return = col_r1.number_input("연금 자산 예상 연평균 수익률 (%)", value=7.0, step=1.0)
    inflation_rate = col_r2.number_input("예상 연평균 물가상승률 (%)", value=2.5, step=0.5)

# ------------------------------------------
# 📈 은퇴 시뮬레이션 알고리즘 계산
# ------------------------------------------
years_to_retire = max(retire_age - current_age, 1)

# 인플레이션 반영 (미래 은퇴 시점 기준)
future_target_monthly = target_monthly_income * ((1 + inflation_rate/100) ** years_to_retire)
future_national_pension = national_pension * ((1 + inflation_rate/100) ** years_to_retire)

projected_personal = total_personal_assets
projected_dc = dc_balance
asset_monthly_rate = (expected_return / 100) / 12

sim_data = []

for year in range(current_age, retire_age + 1):
    sim_data.append({
        "Age": f"{year}세",
        "개인/IRP 누적 자산 (억원)": projected_personal / 100000000,
        "퇴직연금(DC) 누적 자산 (억원)": projected_dc / 100000000,
        "총 연금 자산 (억원)": (projected_personal + projected_dc) / 100000000
    })
    
    if year < retire_age:
        for _ in range(12):
            projected_personal = (projected_personal * (1 + asset_monthly_rate)) + irp_monthly
            projected_dc = (projected_dc * (1 + asset_monthly_rate)) + dc_monthly

# 4% 룰 적용 예상 연금액
future_personal_monthly = (projected_personal * 0.04) / 12
future_dc_monthly = (projected_dc * 0.04) / 12
total_future_monthly = future_national_pension + future_personal_monthly + future_dc_monthly

# ------------------------------------------
# 🏆 2. 최상단 대시보드 (각 연금별 기여도)
# ------------------------------------------
st.subheader(f"2. 🎯 {retire_age}세 은퇴 시점 월 현금흐름(Cashflow) 기여도")
st.caption(f"💡 인플레이션 {inflation_rate}%가 반영된 미래 가치 기준이며, 개인/퇴직연금은 안전 인출률(4% 룰)을 적용한 월 수령액입니다.")

achievement_rate = min((total_future_monthly / future_target_monthly) * 100, 100)
st.progress(int(achievement_rate))
st.write(f"🔥 목표 생활비 대비 예상 달성률: **{achievement_rate:.1f}%**")

col_res1, col_res2, col_res3, col_res4 = st.columns(4)
col_res1.metric("🎯 목표 월 생활비", f"{future_target_monthly/10000:,.0f} 만 원")
col_res2.metric("🔵 (1) 개인+IRP 월 기여액", f"{future_personal_monthly/10000:,.0f} 만 원")
col_res3.metric("🟡 (2) 국민연금 월 기여액", f"{future_national_pension/10000:,.0f} 만 원")
col_res4.metric("🟢 (3) 퇴직/DC 월 기여액", f"{future_dc_monthly/10000:,.0f} 만 원")

st.divider()

diff_monthly = total_future_monthly - future_target_monthly
if diff_monthly >= 0:
    st.success(f"🎉 **축하합니다!** 3층 연금탑이 완성되어, 은퇴 후 목표 생활비보다 매월 **{diff_monthly/10000:,.0f}만 원**을 더 여유롭게 사용할 수 있습니다. (총 예상 연금 자산: **{(projected_personal + projected_dc)/100000000:.1f}억 원**)")
else:
    st.warning(f"🚨 **목표 대비 부족합니다.** 은퇴 후 매월 **{abs(diff_monthly)/10000:,.0f}만 원**이 부족할 것으로 예상됩니다. 납입액을 늘리거나, 예상 수익률을 높이는 전략이 필요합니다. (총 예상 연금 자산: **{(projected_personal + projected_dc)/100000000:.1f}억 원**)")

st.line_chart(pd.DataFrame(sim_data).set_index("Age"), color=["#3498db", "#2ecc71", "#9b59b6"])

st.divider()

# ------------------------------------------
# 3. 📊 실시간 포트폴리오 통합 뷰어 (시각화 추가)
# ------------------------------------------
st.subheader("3. 📊 연금저축 & IRP 통합 포트폴리오 현황")

if not df_combined.empty:
    # 💡 통합 시각화 (Altair 도넛 차트)
    st.markdown("##### 🍩 연금 자산 통합 비중")
    
    chart_data = df_combined[['ETF Name', 'Actual']].groupby('ETF Name').sum().reset_index()
    donut_chart = alt.Chart(chart_data).mark_arc(innerRadius=60).encode(
        theta=alt.Theta(field="Actual", type="quantitative"),
        color=alt.Color(field="ETF Name", type="nominal", legend=alt.Legend(title="투자 종목")),
        tooltip=['ETF Name', alt.Tooltip('Actual', format=',.0f', title='평가금액(원)')]
    ).properties(height=350)
    
    st.altair_chart(donut_chart, use_container_width=True)
    
    # 💡 계좌별 탭(Tab)으로 깔끔하게 데이터프레임 분리
    tab1, tab2 = st.tabs(["📘 연금저축펀드 상세", "📗 IRP (개인형 퇴직연금) 상세"])
    
    desired_cols = ['ETF Name', 'Unit', 'Live Price', 'Budget', 'Actual', 'Current Weight(%)', 'Profit/Loss', 'Yield(%)']
    format_dict = {'Unit': '{:,.0f} 주', 'Live Price': '{:,.0f} 원', 'Budget': '{:,.0f} 원', 'Actual': '{:,.0f} 원', 'Current Weight(%)': '{:.2f}%', 'Profit/Loss': '{:,.0f} 원', 'Yield(%)': '{:.2f}%'}
    
    with tab1:
        if not df_pension.empty:
            pension_cols = [c for c in desired_cols if c in df_pension.columns]
            styled_pension = df_pension[pension_cols].style.format({k: v for k, v in format_dict.items() if k in pension_cols}).map(color_diff_yield, subset=[c for c in ['Profit/Loss', 'Yield(%)'] if c in pension_cols])
            st.dataframe(styled_pension, use_container_width=True)
        else:
            st.info("연금저축 데이터가 없습니다.")
            
    with tab2:
        if not df_irp.empty:
            irp_cols = [c for c in desired_cols if c in df_irp.columns]
            styled_irp = df_irp[irp_cols].style.format({k: v for k, v in format_dict.items() if k in irp_cols}).map(color_diff_yield, subset=[c for c in ['Profit/Loss', 'Yield(%)'] if c in irp_cols])
            st.dataframe(styled_irp, use_container_width=True)
        else:
            st.info("IRP 데이터가 없습니다.")
else:
    st.info("개인연금(IRP/연금저축) 포트폴리오 데이터가 없습니다.")

st.write("💡 *포트폴리오 종목 및 비중 변경은 AI Advisor의 진단 후 별도의 액션 플랜을 통해 진행하세요.*")