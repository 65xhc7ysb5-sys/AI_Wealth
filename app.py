import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import os
import time

# --- RAG(검색 증강 생성)를 위한 라이브러리 추가 ---
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain

# 환경 변수 로드 (.env 보호)
load_dotenv()

st.set_page_config(page_title="Linchpin Wealth", page_icon="🎯", layout="centered")

# ==========================================
# ⚙️ 핵심 엔진 1: 데이터 로드 및 전처리
# ==========================================
def load_data():
    try:
        df = pd.read_csv('data/portfolio_initial.csv')
        
        # 1. Ticker가 없는 행(총합 행 등) 분리
        total_mask = df['Ticker'].isna() | (df['Ticker'].astype(str).str.strip() == '') | (df['Ticker'].astype(str).str.lower() == 'nan')
        total_df = df[total_mask].copy()
        df = df[~total_mask].copy()
        
        # 2. Ticker 정리 및 인덱스화
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
        if 'Actual' in df.columns:
            df = df[df['Actual'] > 0]
        
        # 5. 초과/부족분(Difference) 컬럼 추가
        if 'Actual' in df.columns and 'Budget' in df.columns:
            df['Difference'] = df['Actual'] - df['Budget']
        
        # MVP 임시 주가 세팅 (1주당 1만원 가정)
        if 'Price' not in df.columns:
            df['Price'] = 10000 
            
        return df, total_df
        
    except Exception as e:
        st.error(f"🚨 데이터 로드 중 오류 발생: {e}")
        return pd.DataFrame(), pd.DataFrame()


@st.cache_resource # 앱을 새로고침할 때마다 문서를 다시 읽지 않도록 메모리에 캐싱(저장)합니다.
def create_vector_db():
    try:
        # 1. data 폴더의 PDF 읽기
        loader = PyPDFDirectoryLoader("data/reports")
        docs = loader.load()
        if not docs:
            return None
        
        # 2. 문서를 1000글자 단위로 쪼개기
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        split_docs = text_splitter.split_documents(docs)
        
        # 3. 구글 임베딩을 사용해 FAISS 벡터 DB 생성
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        vectorstore = FAISS.from_documents(split_docs, embeddings)
        return vectorstore
    except Exception as e:
        st.error(f"문서 데이터베이스 생성 중 오류: {e}")
        return None

# 벡터 DB 생성 (앱 실행 시 한 번만 로드됨)
vectorstore = create_vector_db()

# ==========================================
# ⚙️ 핵심 엔진 2: 스마트 리밸런싱 계산기
# ==========================================
def calculate_rebalancing(df, new_deposit):
    total_actual = df['Actual'].sum()
    target_total = total_actual + new_deposit
    
    df['Target_After_Deposit'] = target_total * (df['Weight(%)'] / 100)
    df['Shortfall'] = df['Target_After_Deposit'] - df['Actual']
    df['Shortfall'] = df['Shortfall'].apply(lambda x: x if x > 0 else 0) # 매도 방지
    
    total_shortfall = df['Shortfall'].sum()
    if total_shortfall > 0:
        df['Buy_Amount'] = new_deposit * (df['Shortfall'] / total_shortfall)
        df['Shares_to_Buy'] = (df['Buy_Amount'] / df['Price']).astype(int)
    else:
        df['Buy_Amount'] = 0
        df['Shares_to_Buy'] = 0
        
    return df

# --- 데이터 불러오기 ---
df, total_df = load_data()
total_actual_krw = df['Actual'].sum() if not df.empty else 0


# ==========================================
# 🎨 UI: 메인 화면 구성 시작
# ==========================================
st.title("🎯 Linchpin Wealth MVP")
st.markdown("### 당신의 AI 수석 자산관리사")
st.markdown("---")

# 🎯 섹션 1: Life-Goal Dashboard
st.subheader("🎯 Life-Goal Dashboard")
tab1, tab2 = st.tabs(["🏠 내집 마련 목표", "🏖️ 은퇴 자금(연금) 목표"])

# [탭 1] 내집 마련 시뮬레이터
with tab1:
    st.markdown("**원하는 아파트 단지를 검색해 목표가액을 설정하세요.**")
    apt_query = st.text_input("아파트 단지명 (예: 반포동 아크로리버파크):", placeholder="지역구와 아파트 이름을 입력하세요")
    
    if st.button("실거래가 검색 및 목표 설정"):
        if apt_query:
            with st.spinner("부동산 실거래가 데이터를 불러오는 중..."):
                time.sleep(1) # API 통신 흉내내기
                
                # Mock 데이터 분기 처리
                if "아크로리버파크" in apt_query or "반포" in apt_query:
                    sale_price, jeonse_price, target_price = "42억 원", "20억 원", 22
                elif "마포" in apt_query or "래미안" in apt_query:
                    sale_price, jeonse_price, target_price = "18억 원", "10억 원", 8
                else:
                    sale_price, jeonse_price, target_price = "12억 원", "7억 원", 5
                
                st.success(f"✅ **{apt_query}**의 현재 매매 거래가, 전세가는 각각 {sale_price}, {jeonse_price}이므로, 목표가액은 **{target_price}억 원**입니다.")
                
                # 달성률 프로그레스 바 계산
                achievement_rate = min((total_actual_krw / (target_price * 100000000)) * 100, 100)
                st.progress(int(achievement_rate))
                st.caption(f"현재 총자산({total_actual_krw:,.0f}원) 기준 달성률: {achievement_rate:.1f}%")

# [탭 2] 은퇴 자금 시뮬레이터
with tab2:
    st.markdown("**은퇴 시점의 3층 연금(국민/퇴직/개인) 현금 흐름을 시뮬레이션 합니다.**")
    irp_target = st.slider("개인연금 + IRP 목표가액 (단위: 억 원)", min_value=1, max_value=20, value=5, step=1)
    
    # 4% 룰 기반 가상 현금 흐름 계산
    monthly_irp = irp_target * 33 
    monthly_national = 120 
    monthly_company = 80   
    total_monthly_cashflow = monthly_irp + monthly_national + monthly_company
    estimated_net_worth = irp_target + 10 # 부동산 포함 가상 순자산
    
    st.info(
        f"💡 **목표가액 {irp_target}억 원**으로 설정하시면,\n\n"
        f"**60대 중반에 순자산 {estimated_net_worth}억 원 및 월 현금 흐름 {total_monthly_cashflow:,}만 원** 확보가 가능합니다.\n"
        f"(상세: 개인연금 {monthly_irp}만 원 + 국민연금 {monthly_national}만 원 + 퇴직연금 {monthly_company}만 원)\n\n"
        f"🔥 이는 **대한민국 상위 10% 은퇴 자금 수준**입니다."
    )

st.markdown("---")


# 📊 섹션 2: 현재 포트폴리오 상태
st.subheader("📊 현재 포트폴리오 상태")

if not df.empty:
    # 차이(Difference)에 색상을 입히는 함수
    def color_difference(val):
        if val < 0:
            return 'color: #2ecc71; font-weight: bold;' # 마이너스(부족)는 초록색
        elif val > 0:
            return 'color: #e74c3c; font-weight: bold;' # 플러스(초과)는 빨간색
        return ''

    display_cols = ['ETF Name', 'Weight(%)', 'Budget', 'Actual', 'Difference']
    
    # 숫자 포맷팅 및 색상 적용
    styled_df = df[display_cols].style.format({
        'Weight(%)': '{:.2f}%',
        'Budget': '{:,.0f}',
        'Actual': '{:,.0f}',
        'Difference': '{:,.0f}'
    }).map(color_difference, subset=['Difference'])
    
    st.dataframe(styled_df, width='content')
    
    total_budget = df['Budget'].sum()
    st.info(f"💡 **총 자산 현황** | 목표 배분액: **{total_budget:,.0f}원** | 현재 총 자산: **{total_actual_krw:,.0f}원**")


# ⚡ 섹션 3: Action Center (리밸런싱)
st.subheader("⚡ Action Center: 월간 리밸런싱")
deposit = st.number_input("이번 달 투자금(원)을 입력하세요:", min_value=0, value=1000000, step=100000)

if st.button("리밸런싱 플랜 계산하기"):
    result_df = calculate_rebalancing(df.copy(), deposit)
    action_df = result_df[result_df['Shares_to_Buy'] > 0][['ETF Name', 'Shares_to_Buy', 'Buy_Amount']]
    
    st.success("✅ 최적의 물타기 매수 플랜이 준비되었습니다!")
    styled_action = action_df.style.format({'Buy_Amount': '{:,.0f}원'})
    st.table(styled_action)


# 💬 섹션 4: AI 코치 (RAG + Gemini 2.5 Flash - V2 프롬프트 적용)
st.divider()
st.subheader("💬 Linchpin AI 수석 코치의 데이터 기반 맞춤 진단")

if st.button("목표 기반(Goal-Based) 포트폴리오 진단받기"):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("🚨 .env 파일에 유효한 Gemini API 키를 입력해주세요!")
    elif vectorstore is None:
        st.warning("🚨 'data' 폴더에 PDF 문서가 없거나 DB 생성에 실패했습니다. 일반 모드로 답변하거나 PDF를 추가해주세요.")
    else:
        with st.spinner("Linchpin AI가 정훈님의 '내집마련' 및 '노후' 목표를 바탕으로 실전 전략을 분석 중입니다... 🔍"):
            try:
                # 1. LLM 설정 (온도를 살짝 높여 유연성을 줌)
                llm = ChatGoogleGenerativeAI(
                    model="gemini-2.5-flash", 
                    google_api_key=api_key, 
                    temperature=0.3 
                )
                
                # 2. 시스템 프롬프트 (강력한 가드레일 및 역할 부여)
                system_prompt = (
                    "당신은 대한민국 상위 10% 자산가를 위한 'Linchpin Wealth 수석 AI 자산관리 코치'입니다.\n"
                    "아래 제공된 [Context] 문서(부자 보고서, 경제 전망 등)의 데이터를 근거로 활용하되, "
                    "보고서의 모델(예: 60/40+ 모델)을 기계적으로 강요하지 말고 고객의 현재 상황과 목표에 맞춰 유연하게 해석하세요.\n"
                    "**[절대 준수 가이드라인]**\n"
                    "1. 팩트 교차 검증: 미국 자산(예: 클린에너지)은 미국 정책과, 중국 자산은 중국 정책과 연결하는 등 논리적 오류(환각)를 철저히 방지하세요.\n"
                    "2. 시장 상황 반영: 현재의 거시경제(금리, 인플레이션 등)를 바탕으로 비현실적인 대안투자(PE/PC) 추천은 지양하고 실전적인 ETF 위주로 조언하세요.\n"
                    "3. 어조: 단호하지만 고객의 현실을 공감하는 프로페셔널한 톤을 유지하세요.\n\n"
                    "[Context]\n{context}"
                )
                
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("human", "{input}")
                ])
                
                # 3. RAG 체인 연결
                retriever = vectorstore.as_retriever(search_kwargs={"k": 4}) 
                question_answer_chain = create_stuff_documents_chain(llm, prompt)
                rag_chain = create_retrieval_chain(retriever, question_answer_chain)
                
                # 4. 사용자 질문 구성 (Goal-Based Two-Track 전략 지시)
                portfolio_summary = df[['ETF Name', 'Weight(%)', 'Actual', 'Difference']].to_string()
                user_question = f"""
                고객 정보: '정훈', 40대 남성.
                최우선 목표: 
                1. 단기(3~5년): 서울 주요 입지 내집마련 
                2. 장기(15~20년): 대한민국 상위 10% 수준의 노후 자금 확보
                
                현재 포트폴리오 현황 (Difference가 마이너스면 목표치보다 부족함):
                {portfolio_summary}
                
                위 정보와 [Context] 문서를 바탕으로 다음 3가지를 코칭해주세요:
                
                1. Track A (내집마련 방어막): 3~5년 내에 활용할 자금 특성을 고려할 때, 현재 편입된 안전자산(예: KOFR 금리액티브 등)의 비중이 훌륭한 방어막 역할을 하고 있는지 진단해주세요. 억지로 채권 비중을 높일 필요가 없음을 설명해주세요.
                2. Track B (노후 장기 성장): 15년 뒤 상위 10% 진입을 위해, 현재 부족한 주식 자산(Difference 마이너스) 중 어떤 ETF를 우선 매수해야 하는지 거시경제 트렌드(미국 AI 인프라 등)와 매칭하여 실전적으로 추천해주세요.
                3. 실전 절세 팁 (How-to): 세금 누수 방지를 강조만 하지 말고, 구체적으로 ISA, 연금저축, IRP 계좌를 활용해 배당 소득세와 과세이연 효과를 누려야 한다는 실전적인 'Action Plan'을 제시해주세요.
                """
                
                # 5. 실행 및 결과 출력
                response = rag_chain.invoke({"input": user_question})
                st.info(response["answer"])
                
            except Exception as e:
                st.error(f"🚨 AI 응답 중 오류가 발생했습니다: {type(e).__name__} - {e}")