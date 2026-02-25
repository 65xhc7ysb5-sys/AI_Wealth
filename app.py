import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv()

st.set_page_config(page_title="Linchpin Wealth", page_icon="🎯", layout="centered")

def load_data():
    try:
        df = pd.read_csv('data/portfolio_initial.csv')
        
        # 1. Ticker가 없는 행(총합 행 등)을 따로 분리
        total_mask = df['Ticker'].isna() | (df['Ticker'].astype(str).str.strip() == '') | (df['Ticker'].astype(str).str.lower() == 'nan')
        total_df = df[total_mask].copy()
        df = df[~total_mask].copy()
        
        # 2. Ticker를 깔끔한 문자열로 만들고 인덱스로 설정
        df['Ticker'] = df['Ticker'].astype(str).str.replace('.0', '', regex=False)
        df.set_index('Ticker', inplace=True)
        
        # 3. 데이터 클렌징 (%, ₩, 쉼표, 공백 제거)
        if 'Weight' in df.columns:
            df['Weight(%)'] = df['Weight'].astype(str).str.replace('%', '').astype(float)
            
        for col in ['Budget', 'Actual']:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace('₩', '')
                    .str.replace(',', '')
                    .str.replace('\t', '')
                    .str.strip()
                )
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        # 4. Actual이 0인 행은 과감히 삭제
        df = df[df['Actual'] > 0]
        
        # 5. 초과/부족분(Difference) 컬럼 추가 (Actual - Budget)
        df['Difference'] = df['Actual'] - df['Budget']
        
        # MVP 임시 주가 세팅
        if 'Price' not in df.columns:
            df['Price'] = 10000 
            
        return df, total_df
        
    except Exception as e:
        st.error(f"🚨 데이터 로드 중 오류 발생: {e}")
        return pd.DataFrame(), pd.DataFrame()

def calculate_rebalancing(df, new_deposit):
    # (리밸런싱 로직은 기존과 동일하되, Budget/Actual 컬럼명에 맞춤)
    total_actual = df['Actual'].sum()
    target_total = total_actual + new_deposit
    
    df['Target_After_Deposit'] = target_total * (df['Weight(%)'] / 100)
    df['Shortfall'] = df['Target_After_Deposit'] - df['Actual']
    df['Shortfall'] = df['Shortfall'].apply(lambda x: x if x > 0 else 0)
    
    total_shortfall = df['Shortfall'].sum()
    if total_shortfall > 0:
        df['Buy_Amount'] = new_deposit * (df['Shortfall'] / total_shortfall)
        df['Shares_to_Buy'] = (df['Buy_Amount'] / df['Price']).astype(int)
    else:
        df['Buy_Amount'] = 0
        df['Shares_to_Buy'] = 0
        
    return df

# --- UI 화면 구성 ---
st.title("🎯 Linchpin Wealth MVP")
st.markdown("### 당신의 AI 수석 자산관리사")

df, total_df = load_data()

st.subheader("📊 현재 포트폴리오 상태")

if not df.empty:
    # 차이(Difference)에 색상을 입히는 함수
    def color_difference(val):
        if val < 0:
            return 'color: #2ecc71; font-weight: bold;' # 마이너스(부족분)는 초록색
        elif val > 0:
            return 'color: #e74c3c; font-weight: bold;' # 플러스(초과분)는 빨간색
        return ''

    # 화면에 보여줄 컬럼만 선택
    display_cols = ['ETF Name', 'Weight(%)', 'Budget', 'Actual', 'Difference']
    
    # Pandas Styler로 쉼표(,) 및 퍼센트(%) 포맷팅 적용
    styled_df = df[display_cols].style.format({
        'Weight(%)': '{:.2f}%',
        'Budget': '{:,.0f}',
        'Actual': '{:,.0f}',
        'Difference': '{:,.0f}'
    }).map(color_difference, subset=['Difference'])
    
    # 표 렌더링 (Ticker가 인덱스이므로 자동으로 가장 왼쪽에 깔끔하게 붙습니다)
    st.dataframe(styled_df, use_container_width=True)
    
    # 총합(Total) 정보 표시
    total_actual = df['Actual'].sum()
    total_budget = df['Budget'].sum()
    st.info(f"💡 **총 자산 현황** | 목표 배분액: **{total_budget:,.0f}원** | 현재 총 자산: **{total_actual:,.0f}원**")

# --- 액션 센터 ---
st.subheader("⚡ Action Center: 월간 리밸런싱")
deposit = st.number_input("이번 달 투자금(원)을 입력하세요:", min_value=0, value=1000000, step=100000)

if st.button("리밸런싱 플랜 계산하기"):
    result_df = calculate_rebalancing(df.copy(), deposit)
    action_df = result_df[result_df['Shares_to_Buy'] > 0][['ETF Name', 'Shares_to_Buy', 'Buy_Amount']]
    
    st.success("✅ 최적의 물타기 매수 플랜이 준비되었습니다!")
    
    # 결과 표 포맷팅
    styled_action = action_df.style.format({'Buy_Amount': '{:,.0f}원'})
    st.table(styled_action)


# --- AI 코치 섹션 (LangChain + Gemini 버전) ---
st.divider()
st.subheader("💬 Linchpin AI 코치의 포트폴리오 진단")

if st.button("이번 달 포트폴리오 진단받기 (Gemini AI)"):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "AIza-여기에_발급받은_구글키를_넣으세요":
        st.error("🚨 .env 파일에 유효한 Gemini API 키를 입력해주세요!")
    else:
        with st.spinner("Linchpin AI가 정훈님의 자산 배분 상태를 분석하고 있습니다... 🔍"):
            try:
                # 1. LangChain 패키지 임포트
                from langchain_google_genai import ChatGoogleGenerativeAI
                
                # 2. 모델 설정 (안정적인 gemini-pro 사용)                
                llm = ChatGoogleGenerativeAI(
                    model="gemini-2.5-flash", 
                    google_api_key=api_key, 
                    temperature=0.7
                )

                
                # 3. 데이터 및 프롬프트 준비
                portfolio_summary = df[['ETF Name', 'Weight(%)', 'Actual', 'Difference']].to_string()
                
                prompt = f"""
                당신은 세계 최고의 거시경제 분석가이자 리테일 현장의 경험을 가진 '린치핀(Linchpin) 자산관리 코치'입니다.
                고객의 이름은 '정훈'입니다.
                
                아래는 정훈님의 이번 달 포트폴리오 실제 현황입니다 (Difference가 마이너스면 목표치보다 부족, 플러스면 초과를 의미합니다):
                {portfolio_summary}
                
                위 데이터를 바탕으로 다음 3가지를 포함하여 3~4문단으로 짧고 임팩트 있게 코칭해주세요:
                1. 현재 가장 비중이 부족해서 매수가 시급한 자산 1개 추천 및 그 이유 (저가 매수 기회 관점)
                2. 올웨더 포트폴리오 관점에서 현재 방어력(KOFR 등 안전자산)에 대한 칭찬 또는 점검
                3. 시장의 노이즈에 흔들리지 말고 장기 목표(내집마련, 노후)를 유지하라는 리더십 있는 격려
                
                어조: 단호하지만 따뜻하고, 전문가다운 통찰력이 느껴지는 톤.
                """
                
                # 4. LangChain을 통해 AI 호출 (invoke 메서드 사용)
                response = llm.invoke(prompt)
                
                # 5. 결과 텍스트 출력
                st.info(response.content)
                
            except Exception as e:
                st.error(f"🚨 AI 응답 중 오류가 발생했습니다: {type(e).__name__} - {e}")