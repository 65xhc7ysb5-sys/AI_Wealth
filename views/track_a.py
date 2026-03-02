import streamlit as st
import pandas as pd
import time
import os
import json
import yfinance as yf
from utils import load_data, display_cols, color_diff_yield
from langchain_google_genai import ChatGoogleGenerativeAI

# ==========================================
# ⚙️ 보조 함수: 실시간 시세 조회 및 AI 부동산
# ==========================================
def get_live_price(ticker):
    """yfinance를 이용해 한국 주식/ETF 실시간 가격 조회"""
    try:
        ks_ticker = f"{ticker}.KS"
        stock = yf.Ticker(ks_ticker)
        todays_data = stock.history(period='1d')
        if not todays_data.empty:
            return float(todays_data['Close'].iloc[-1])
    except:
        pass
    return None

def estimate_real_estate_ai(apt_name):
    """Gemini AI를 활용한 매매가/전세가/갭 추정"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: return None
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0.1)
    prompt = f"""
    당신은 한국 부동산 전문가입니다. 사용자가 검색한 아파트 '{apt_name}'의 대략적인 현재 실거래 매매가와 전세가를 추정해주세요.
    반드시 아래 JSON 형식으로만 응답하세요. 숫자(원 단위)만 적으세요.
    예시: {{"sale": 1500000000, "jeonse": 800000000}}
    """
    try:
        res = llm.invoke(prompt)
        clean_text = res.content.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
    except Exception as e:
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
            new_actual = current_unit * live_price
            live_actuals.append(new_actual)
            live_prices[ticker] = live_price
        else:
            live_actuals.append(row['Actual'])
            live_prices[ticker] = row['Actual'] / current_unit if current_unit > 0 else 0
            
    # 실시간 지표 업데이트
    df_isa['Live Price'] = [live_prices.get(t, 0) for t in df_isa.index]
    df_isa['Actual'] = live_actuals
    
    # 평가손익(Profit/Loss) 및 수익률 계산
    df_isa['Profit/Loss'] = df_isa['Actual'] - df_isa['Budget'] 
    df_isa['Yield(%)'] = df_isa.apply(
        lambda x: (x['Profit/Loss'] / x['Budget'] * 100) if x['Budget'] > 0 else 0, axis=1
    )

isa_total = df_isa['Actual'].sum() if not df_isa.empty else 0
if not df_isa.empty:
    df_isa['Current Weight(%)'] = (df_isa['Actual'] / isa_total * 100).fillna(0)

# Session State 초기화 (타겟 비중)
if 'target_weights' not in st.session_state:
    if not df_isa.empty:
        st.session_state['target_weights'] = df_isa['Current Weight(%)'].copy()


# ==========================================
# 🖥️ UI 렌더링 시작
# ==========================================
st.title("🏠 내집 마련 (3~5년 단기 목표)")
st.markdown("단기 변동성을 방어하고 시드머니를 지키는 **ISA 계좌 중심**의 전략 공간입니다.")

col_tgt, _ = st.columns([1, 1])
with col_tgt:
    st.info(f"💡 **현재 ISA 계좌 실시간 총 자산: {isa_total:,.0f}원**")

# ------------------------------------------
# 1. 아파트 목표가 (API/AI 연동)
# ------------------------------------------
st.subheader("1. 🎯 타겟 아파트 갭(Gap) 분석")
apt_query = st.text_input("목표 아파트 단지명 검색 (예: 마포 래미안 푸르지오):")

if st.button("실거래가 및 갭 예산 조회"):
    with st.spinner("AI가 최신 실거래가와 전세가를 분석 중입니다..."):
        time.sleep(1)
        ai_data = estimate_real_estate_ai(apt_query)
        
        if ai_data and 'sale' in ai_data and 'jeonse' in ai_data:
            gap_price = ai_data['sale'] - ai_data['jeonse']
            col1, col2, col3 = st.columns(3)
            col1.metric("추정 매매가", f"{ai_data['sale'] / 100000000:.1f}억 원")
            col2.metric("추정 전세가", f"{ai_data['jeonse'] / 100000000:.1f}억 원")
            col3.metric("🔥 필요 예산 (Gap)", f"{gap_price / 100000000:.1f}억 원")
            
            achievement_rate = min((isa_total / gap_price) * 100, 100) if gap_price > 0 else 0
            st.progress(int(achievement_rate))
            st.caption(f"현재 자산 대비 갭 투자 달성률: {achievement_rate:.1f}%")
        else:
            st.warning("데이터를 불러오지 못했습니다. 다시 시도해주세요.")

st.divider()

# ------------------------------------------
# 2. 실시간 포트폴리오 스냅샷
# ------------------------------------------
st.subheader("2. 📊 현재 포트폴리오 현황 (실시간 시세 반영)")
if not df_isa.empty:
    # 에러 방지용: 존재하는 컬럼만 선택
    desired_cols = ['ETF Name', 'Unit', 'Live Price', 'Budget', 'Actual', 'Current Weight(%)', 'Profit/Loss', 'Yield(%)']
    snapshot_cols = [c for c in desired_cols if c in df_isa.columns]
    
    format_dict = {
        'Unit': '{:,.0f} 주', 'Live Price': '{:,.0f} 원', 'Budget': '{:,.0f} 원', 
        'Actual': '{:,.0f} 원', 'Current Weight(%)': '{:.2f}%', 
        'Profit/Loss': '{:,.0f} 원', 'Yield(%)': '{:.2f}%'
    }
    
    active_format_dict = {k: v for k, v in format_dict.items() if k in snapshot_cols}
    subset_color = [c for c in ['Profit/Loss', 'Yield(%)'] if c in snapshot_cols]
    
    styled_snapshot = df_isa[snapshot_cols].style.format(active_format_dict).map(color_diff_yield, subset=subset_color)
    st.dataframe(styled_snapshot, use_container_width=True)
else:
    st.warning("ISA 계좌 데이터가 없습니다.")

st.divider()

# ------------------------------------------
# 3. 실시간 포트폴리오 및 리밸런싱 에디터
# ------------------------------------------
st.subheader("3. ⚖️ 월간 스마트 리밸런싱 및 매매 액션")
deposit = st.number_input("💰 이번 달 ISA 계좌 추가 납입액 (원):", value=1000000, step=100000)
new_total_budget = isa_total + deposit

st.write("**[Step 1] 종목별 목표 비중(%) 조정** (표의 숫자를 직접 더블클릭해서 수정하세요)")

if not df_isa.empty:
    edit_df = df_isa[['ETF Name', 'Current Weight(%)']].copy()
    edit_df['Target Weight(%)'] = st.session_state['target_weights']
    
    edited_df = st.data_editor(
        edit_df,
        column_config={
            "ETF Name": st.column_config.TextColumn("종목명", disabled=True),
            "Current Weight(%)": st.column_config.NumberColumn("현재 비중(%)", disabled=True, format="%.2f%%"),
            "Target Weight(%)": st.column_config.NumberColumn("🎯 목표 비중(%)", min_value=0.0, max_value=100.0, format="%.2f%%")
        },
        use_container_width=True
    )
    
    total_target_weight = edited_df['Target Weight(%)'].sum()
    if abs(total_target_weight - 100.0) > 0.1:
        st.error(f"🚨 목표 비중의 합이 100%가 되어야 합니다! (현재: {total_target_weight:.1f}%)")
    else:
        if st.button("✅ 리밸런싱 비중 확정 및 계산"):
            st.session_state['target_weights'] = edited_df['Target Weight(%)']
            st.success("비중이 확정되었습니다! 아래 Action Plan에 따라 HTS/MTS에서 매매를 진행하세요.")
    
    st.write("---")
    st.write("**[Step 2] 최종 Action Plan (매수/매도 지시서)**")
    
    action_df = df_isa[['ETF Name', 'Live Price', 'Actual']].copy()
    action_df['Target Amount'] = (new_total_budget * (st.session_state['target_weights'] / 100)).round(-2)
    action_df['Action Amount'] = action_df['Target Amount'] - action_df['Actual']
    # 주수 계산 (소수점 버림 처리)
    action_df['Action Unit'] = (action_df['Action Amount'] / action_df['Live Price']).fillna(0).astype(int)
    
    def color_action(val):
        if val > 0: return 'color: #e74c3c; font-weight: bold;' 
        elif val < 0: return 'color: #2ecc71; font-weight: bold;'
        return ''
    
    styled_action = action_df[['ETF Name', 'Live Price', 'Action Amount', 'Action Unit']].style.format({
        'Live Price': '{:,.0f} 원', 'Action Amount': '{:,.0f} 원', 'Action Unit': '{:,.0f} 주'
    }).map(color_action, subset=['Action Amount', 'Action Unit'])
    
    st.dataframe(styled_action, use_container_width=True)
    st.caption("※ **Action Unit**이 양수(+)면 매수, 음수(-)면 매도입니다.")

    # ------------------------------------------
    # 4. 평단가 기반 매매 후 CSV 자동 업데이트
    # ------------------------------------------
    st.write("---")
    st.write("**[Step 3] 포트폴리오 장부 갱신 (평단가 적용)**")
    st.warning("실제 매매를 마치셨다면, 아래 버튼을 눌러 내 자산 현황 장부를 업데이트하세요.")
    
    if st.button("💾 매매 완료 및 포트폴리오(CSV) 갱신하기"):
        try:
            csv_path = 'asset_position_isa.csv'
            original_df = pd.read_csv(csv_path)
            original_df['Ticker'] = original_df['Ticker'].astype(str).str.replace('.0', '', regex=False)
            original_df.columns = original_df.columns.str.strip() # 공백 제거 안전장치
            
            for idx, row in action_df.iterrows():
                if row['Action Unit'] == 0:
                    continue # 변화가 없는 종목은 패스
                    
                mask = original_df['Ticker'] == str(idx)
                if mask.any():
                    curr_unit = float(original_df.loc[mask, 'Unit'].values[0])
                    curr_budget = float(original_df.loc[mask, 'Budget'].values[0])
                    
                    action_u = row['Action Unit']
                    live_p = row['Live Price']
                    
                    # 💡 현재 평단가 계산 (0으로 나누기 방지)
                    avg_price = curr_budget / curr_unit if curr_unit > 0 else live_p
                    
                    if action_u > 0:
                        # 매수 (물타기/불타기): 총 비용을 더해줌
                        new_unit = curr_unit + action_u
                        new_budget = curr_budget + (action_u * live_p)
                    else:
                        # 매도: 평단가는 유지한 채, 남은 주식 수만큼 원금 재계산
                        new_unit = curr_unit + action_u
                        if new_unit <= 0:
                            new_unit = 0
                            new_budget = 0 # 전량 매도
                        else:
                            new_budget = curr_budget + (action_u * avg_price) # action_u가 음수이므로 원금이 깎임
                    
                    original_df.loc[mask, 'Unit'] = new_unit
                    original_df.loc[mask, 'Budget'] = new_budget
            
            original_df.to_csv(csv_path, index=False)
            st.success("🎉 평단가 기준 매매 내역이 완벽하게 반영되었습니다! 화면을 새로고침합니다...")
            time.sleep(1.5)
            st.rerun()
            
        except Exception as e:
            st.error(f"🚨 업데이트 중 오류가 발생했습니다: {e}")