import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import os

# 환경 변수 로드 (.env 파일에서 API 키 등을 안전하게 가져올 준비)
load_dotenv()

st.set_page_config(page_title="Linchpin Wealth", page_icon="🎯", layout="centered")

def load_data():
    # 임시 데이터 (다음 단계에서 실제 투자 자산 티커로 교체할 예정입니다)
    data = {
        'Ticker': ['S&P500TR', 'Nifty50', 'CSI300', 'KOFR'],
        'Weight(%)': [40, 20, 5, 35],
        'Actual(KRW)': [18000000, 8000000, 3000000, 15000000],
        'Price': [15000, 20000, 10000, 50000] 
    }
    return pd.DataFrame(data)

def calculate_rebalancing(df, new_deposit):
    total_actual = df['Actual(KRW)'].sum()
    target_total = total_actual + new_deposit
    
    df['Target(KRW)'] = target_total * (df['Weight(%)'] / 100)
    df['Shortfall'] = df['Target(KRW)'] - df['Actual(KRW)']
    df['Shortfall'] = df['Shortfall'].apply(lambda x: x if x > 0 else 0)
    
    total_shortfall = df['Shortfall'].sum()
    if total_shortfall > 0:
        df['Buy_Amount'] = new_deposit * (df['Shortfall'] / total_shortfall)
        df['Shares_to_Buy'] = (df['Buy_Amount'] / df['Price']).astype(int)
    else:
        df['Buy_Amount'] = 0
        df['Shares_to_Buy'] = 0
        
    return df

st.title("🎯 Linchpin Wealth MVP")
st.markdown("### 당신의 AI 수석 자산관리사")

df = load_data()
st.subheader("📊 현재 포트폴리오 상태")
st.dataframe(df[['Ticker', 'Weight(%)', 'Actual(KRW)']])

st.subheader("⚡ Action Center: 월간 리밸런싱")
deposit = st.number_input("이번 달 투자금(원)을 입력하세요:", min_value=0, value=1000000, step=100000)

if st.button("리밸런싱 플랜 계산하기"):
    result_df = calculate_rebalancing(df.copy(), deposit)
    action_df = result_df[result_df['Shares_to_Buy'] > 0][['Ticker', 'Shares_to_Buy', 'Buy_Amount']]
    
    st.success("✅ 최적의 물타기 매수 플랜이 준비되었습니다!")
    st.table(action_df)