import streamlit as st
import pandas as pd
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import yfinance as yf
from utils import load_data, color_diff_yield

# ==========================================
# ⚙️ 보조 함수: 실시간 시세 조회
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

# ==========================================
# 📊 데이터 로드 및 실시간 지표 계산
# ==========================================
df_isa = load_data('data/asset_position_isa.csv')
live_prices = {}
if not df_isa.empty:
    live_actuals = []
    for ticker, row in df_isa.iterrows():
        live_price = get_live_price(ticker)
        current_unit = row.get('Unit', 0)
        if live_price:
            live_actuals.append(current_unit * live_price)
            live_prices[ticker] = live_price
        else:
            live_actuals.append(row['Actual'])
            live_prices[ticker] = row['Actual'] / current_unit if current_unit > 0 else 0
            
    df_isa['Live Price'] = [live_prices.get(t, 0) for t in df_isa.index]
    df_isa['Actual'] = live_actuals
    df_isa['Profit/Loss'] = df_isa['Actual'] - df_isa['Budget'] 
    df_isa['Yield(%)'] = df_isa.apply(lambda x: (x['Profit/Loss'] / x['Budget'] * 100) if x['Budget'] > 0 else 0, axis=1)

isa_total = df_isa['Actual'].sum() if not df_isa.empty else 0
if not df_isa.empty: df_isa['Current Weight(%)'] = (df_isa['Actual'] / isa_total * 100).fillna(0)

# ==========================================
# 💾 Session State 초기화
# ==========================================
if 'target_weights' not in st.session_state and not df_isa.empty:
    st.session_state['target_weights'] = df_isa['Current Weight(%)'].copy()

# 목표 아파트 정보 저장용 상태 (기본값 세팅)
if 'apt_target_name' not in st.session_state: st.session_state['apt_target_name'] = "구리시 교문 한양 30평"
if 'apt_sale_price' not in st.session_state: st.session_state['apt_sale_price'] = 900000000
if 'apt_jeonse_price' not in st.session_state: st.session_state['apt_jeonse_price'] = 450000000
if 'apt_gap_budget' not in st.session_state: st.session_state['apt_gap_budget'] = 450000000

# ==========================================
# 🖥️ UI 렌더링 시작
# ==========================================
st.title("🏠 내집 마련 (3~5년 단기 목표)")
st.markdown("단기 변동성을 방어하고 시드머니를 지키는 **ISA 계좌 중심**의 전략 공간입니다.")

# ------------------------------------------
# 1. 🎯 최상단: 목표 타겟 설정 (네이버 호가 수동 입력)
# ------------------------------------------
st.subheader("1. 🎯 나의 내집마련 목표 & 시뮬레이션")

# 💡 [위치 복구] 사용자가 가장 먼저 볼 수 있도록 최상단으로 끌어올렸습니다.
with st.expander("🔍 타겟 아파트 및 네이버 호가 입력", expanded=(st.session_state['apt_gap_budget'] == 0)):
    st.markdown("현재 네이버 부동산에 올라온 **가장 정확한 호가**를 직접 입력하여 목표를 설정하세요.")
    
    new_apt_name = st.text_input("목표 단지명 (예: 구리시 교문 한양 30평):", value=st.session_state['apt_target_name'])
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        input_sale = st.number_input("네이버 매매 최저 호가 (원)", value=int(st.session_state['apt_sale_price']), step=10000000)
        st.markdown(f"<div style='color: #e74c3c; font-weight: bold; margin-top: -10px;'>{input_sale/100000000:.2f}억</div>", unsafe_allow_html=True)
    with col_input2:
        input_jeonse = st.number_input("네이버 전세 최저 호가 (원)", value=int(st.session_state['apt_jeonse_price']), step=10000000)
        st.markdown(f"<div style='color: #2980b9; font-weight: bold; margin-top: -10px;'>{input_jeonse/100000000:.2f}억</div>", unsafe_allow_html=True)
        
    if st.button("✅ 이 가격으로 타겟 확정 및 시뮬레이션 업데이트"):
        st.session_state['apt_target_name'] = new_apt_name
        st.session_state['apt_sale_price'] = input_sale
        st.session_state['apt_jeonse_price'] = input_jeonse
        st.session_state['apt_gap_budget'] = input_sale - input_jeonse
        st.success("✅ 타겟이 성공적으로 업데이트되었습니다!")
        time.sleep(0.5)
        st.rerun()

# ------------------------------------------
# 💡 시뮬레이션 대시보드 (입력창 바로 아래에 위치)
# ------------------------------------------
target_gap = st.session_state['apt_gap_budget']

if target_gap > 0:
    st.info(f"**현재 타겟 단지:** {st.session_state['apt_target_name']}")
    col_t1, col_t2, col_t3 = st.columns(3)
    col_t1.metric("총 매매 호가 (현재)", f"{st.session_state['apt_sale_price']/100000000:.2f} 억 원")
    col_t2.metric("예상 전세가 (현재)", f"{st.session_state['apt_jeonse_price']/100000000:.2f} 억 원")
    col_t3.metric("🔥 현재 기준 필요 갭(Gap)", f"{target_gap/100000000:.2f} 억 원")
    
    st.divider()

    st.write("⚙️ **달성 시기 예측 시뮬레이터**")
    col_sim1, col_sim2, col_sim3 = st.columns(3)
    with col_sim1:
        other_assets = st.number_input("1. 가족 합산 추가 자산 (원)", value=100000000, step=10000000)
        st.markdown(f"<div style='color: #2980b9; font-weight: bold; margin-top: -10px; margin-bottom: 15px;'>₩ {other_assets:,.0f} ({other_assets/100000000:.1f}억)</div>", unsafe_allow_html=True)
    with col_sim2:
        credit_loan = st.number_input("2. 활용 가능 대출 (원)", value=50000000, step=10000000)
        st.markdown(f"<div style='color: #2980b9; font-weight: bold; margin-top: -10px; margin-bottom: 15px;'>₩ {credit_loan:,.0f} ({credit_loan/100000000:.1f}억)</div>", unsafe_allow_html=True)
    with col_sim3:
        monthly_invest = st.number_input("3. 매월 추가 적립액 (원)", value=1500000, step=100000)
        st.markdown(f"<div style='color: #2980b9; font-weight: bold; margin-top: -10px; margin-bottom: 15px;'>₩ {monthly_invest:,.0f} ({monthly_invest/10000:,.0f}만)</div>", unsafe_allow_html=True)

    col_sim4, col_sim5 = st.columns(2)
    with col_sim4: expected_return = st.number_input("4. 내 자산 예상 연평균 수익률 (%)", value=7.0, step=1.0)
    with col_sim5: real_estate_inflation = st.number_input("5. 아파트 연평균 상승률 (%)", value=3.0, step=1.0)
    
    current_total_assets = isa_total + other_assets + credit_loan
    achievement_rate = min((current_total_assets / target_gap) * 100, 100)
    
    st.progress(int(achievement_rate))
    st.caption(f"🚀 현재 가용 자산(대출 포함) 대비 목표 달성률: **{achievement_rate:.1f}%**")

    if achievement_rate < 100 and monthly_invest > 0:
        asset_monthly_rate = (expected_return / 100) / 12
        re_monthly_rate = (real_estate_inflation / 100) / 12
        
        projected_assets, dynamic_gap, months = current_total_assets, target_gap, 0
        sim_data = []
        today = datetime.today()
        
        while projected_assets < dynamic_gap and months < 360:
            if months % 12 == 0: 
                current_date = today + relativedelta(months=months)
                year_str = f"{current_date.year}년"
                
                sim_data.append({
                    "Date": year_str, 
                    "나의 예상 자산 (억원)": projected_assets / 100000000, 
                    "필요 갭 예산 (물가상승 반영)": dynamic_gap / 100000000      
                })
            
            months += 1
            projected_assets = (projected_assets * (1 + asset_monthly_rate)) + monthly_invest
            dynamic_gap = dynamic_gap * (1 + re_monthly_rate)
            
        target_date = today + relativedelta(months=months)
        year_str = f"{target_date.year}년 (달성!)"
        sim_data.append({
            "Date": year_str, 
            "나의 예상 자산 (억원)": projected_assets / 100000000, 
            "필요 갭 예산 (물가상승 반영)": dynamic_gap / 100000000
        })
        
        if months >= 360:
            st.error("🚨 30년 내에 따라잡기 어렵습니다. 투자 금액을 늘리거나 대출 한도를 확인하세요.")
        else:
            st.success(
                f"🎉 현재 추세라면 **{months // 12}년 {months % 12}개월 뒤 ({target_date.year}년 {target_date.month}월)**에 목표를 달성합니다!\n\n"
                f"*(💡 아파트 연평균 상승률 {real_estate_inflation}% 복리 적용 시, 달성 시점의 최종 필요 갭은 **{dynamic_gap/100000000:.2f}억 원**으로 예상됩니다.)*"
            )
        
        st.line_chart(pd.DataFrame(sim_data).set_index("Date"), color=["#2ecc71", "#e74c3c"]) 
        
    elif achievement_rate >= 100:
        st.success("🎉 영끌 대출을 포함하면 이미 목표 예산을 달성하셨습니다! 당장 네이버 부동산을 켜시죠!")

st.divider()

# ------------------------------------------
# 2. 실시간 포트폴리오 스냅샷
# ------------------------------------------
st.subheader("2. 📊 현재 포트폴리오 스냅샷 (실시간)")
if not df_isa.empty:
    desired_cols = ['ETF Name', 'Unit', 'Live Price', 'Budget', 'Actual', 'Current Weight(%)', 'Profit/Loss', 'Yield(%)']
    snapshot_cols = [c for c in desired_cols if c in df_isa.columns]
    format_dict = {'Unit': '{:,.0f} 주', 'Live Price': '{:,.0f} 원', 'Budget': '{:,.0f} 원', 'Actual': '{:,.0f} 원', 'Current Weight(%)': '{:.2f}%', 'Profit/Loss': '{:,.0f} 원', 'Yield(%)': '{:.2f}%'}
    styled_snapshot = df_isa[snapshot_cols].style.format({k: v for k, v in format_dict.items() if k in snapshot_cols}).map(color_diff_yield, subset=[c for c in ['Profit/Loss', 'Yield(%)'] if c in snapshot_cols])
    st.dataframe(styled_snapshot, use_container_width=True)

st.divider()

# ------------------------------------------
# 3. 실시간 포트폴리오 리밸런싱 및 장부 갱신
# ------------------------------------------
st.subheader("3. ⚖️ 월간 스마트 리밸런싱 및 매매 액션")

monthly_invest_rebal = monthly_invest if 'monthly_invest' in locals() else 1500000 
new_total_budget = isa_total + (monthly_invest_rebal if target_gap > 0 else 1000000)

if not df_isa.empty:
    edit_df = df_isa[['ETF Name', 'Current Weight(%)']].copy()
    edit_df['Target Weight(%)'] = st.session_state['target_weights']
    edited_df = st.data_editor(
        edit_df,
        column_config={"ETF Name": st.column_config.TextColumn("종목명", disabled=True), "Current Weight(%)": st.column_config.NumberColumn("현재 비중(%)", disabled=True, format="%.2f%%"), "Target Weight(%)": st.column_config.NumberColumn("🎯 목표 비중(%)", min_value=0.0, max_value=100.0, format="%.2f%%")},
        use_container_width=True
    )
    
    if abs(edited_df['Target Weight(%)'].sum() - 100.0) > 0.1:
        st.error(f"🚨 목표 비중의 합이 100%가 되어야 합니다! (현재: {edited_df['Target Weight(%)'].sum():.1f}%)")
    else:
        if st.button("✅ 리밸런싱 비중 확정 및 계산"):
            st.session_state['target_weights'] = edited_df['Target Weight(%)']
            st.success("비중 확정! 아래 Action Plan을 확인하세요.")
    
    action_df = df_isa[['ETF Name', 'Live Price', 'Actual']].copy()
    action_df['Target Amount'] = (new_total_budget * (st.session_state['target_weights'] / 100)).round(-2)
    action_df['Action Amount'] = action_df['Target Amount'] - action_df['Actual']
    action_df['Action Unit'] = (action_df['Action Amount'] / action_df['Live Price']).fillna(0).astype(int)
    
    def color_action(val): return 'color: #2ecc71; font-weight: bold;' if val > 0 else 'color: #e74c3c; font-weight: bold;' if val < 0 else ''
    styled_action = action_df[['ETF Name', 'Live Price', 'Action Amount', 'Action Unit']].style.format({'Live Price': '{:,.0f} 원', 'Action Amount': '{:,.0f} 원', 'Action Unit': '{:,.0f} 주'}).map(color_action, subset=['Action Amount', 'Action Unit'])
    st.dataframe(styled_action, use_container_width=True)

    st.write("---")
    st.write("**[Step 3] 포트폴리오 장부 갱신 (평단가 적용)**")
    if st.button("💾 매매 완료 및 포트폴리오(CSV) 갱신하기"):
        try:
            csv_path = 'data/asset_position_isa.csv'
            original_df = pd.read_csv(csv_path)
            original_df['Ticker'] = original_df['Ticker'].astype(str).str.replace('.0', '', regex=False)
            original_df.columns = original_df.columns.str.strip()
            
            for idx, row in action_df.iterrows():
                if row['Action Unit'] == 0: continue
                mask = original_df['Ticker'] == str(idx)
                if mask.any():
                    curr_unit, curr_budget = float(original_df.loc[mask, 'Unit'].values[0]), float(original_df.loc[mask, 'Budget'].values[0])
                    action_u, live_p = row['Action Unit'], row['Live Price']
                    avg_price = curr_budget / curr_unit if curr_unit > 0 else live_p
                    
                    if action_u > 0:
                        new_unit, new_budget = curr_unit + action_u, curr_budget + (action_u * live_p)
                    else:
                        new_unit = curr_unit + action_u
                        new_budget = 0 if new_unit <= 0 else curr_budget + (action_u * avg_price) 
                    
                    original_df.loc[mask, 'Unit'], original_df.loc[mask, 'Budget'] = new_unit, new_budget
            
            original_df.to_csv(csv_path, index=False)
            st.success("🎉 갱신이 완료되었습니다!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"🚨 업데이트 중 오류가 발생했습니다: {e}")