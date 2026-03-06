import streamlit as st
import pandas as pd
import os
from utils import load_data, create_vector_db
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain
from langchain_google_genai import ChatGoogleGenerativeAI
from prompts import get_ai_coach_system_prompt # 💡 프롬프트 함수 불러오기

# ==========================================
# 📊 1. 고객의 실시간 포트폴리오 데이터 텍스트화
# ==========================================
def get_portfolio_context():
    """DB에서 ISA, IRP, 연금저축 데이터를 불러와 AI가 읽기 쉬운 텍스트로 요약합니다."""
    context = ""
    accounts = {'ISA (내집마련용)': 'isa', 'IRP (퇴직연금)': 'irp', '연금저축': 'pension'}
    
    total_assets = 0
    for acc_name, acc_type in accounts.items():
        df = load_data(acc_type)
        if not df.empty:
            total_budget = df['Budget'].sum()
            total_actual = df['Actual'].sum()
            total_assets += total_actual
            yield_pct = ((total_actual - total_budget) / total_budget * 100) if total_budget > 0 else 0
            
            context += f"\n▶ {acc_name} 계좌 현황 (총 평가액: {total_actual:,.0f}원, 수익률: {yield_pct:.2f}%)\n"
            for ticker, row in df.iterrows():
                profit = row['Actual'] - row['Budget']
                item_yield = (profit / row['Budget'] * 100) if row['Budget'] > 0 else 0
                context += f" - {row['ETF Name']} ({ticker}): {row['Unit']}주, 평가액 {row['Actual']:,.0f}원 (수익률 {item_yield:.2f}%)\n"
        else:
            context += f"\n▶ {acc_name} 계좌: 현재 보유 종목 없음\n"
            
    if total_assets == 0:
        return "현재 데이터베이스에 등록된 자산 내역이 없습니다."
        
    return context

# ==========================================
# 🖥️ 2. UI 및 AI 챗봇 로직
# ==========================================
st.title("🤖 AI 수석 자산관리 코치")
st.markdown("Linchpin Wealth의 AI 코치가 **고객님의 실제 포트폴리오 데이터**를 기반으로 1:1 맞춤 진단을 제공합니다.")

# API 키 확인
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("🚨 .env 파일에 GEMINI_API_KEY를 설정해 주세요.")
    st.stop()

# 세션 상태 초기화
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# 채팅 내역 출력
for msg in st.session_state["chat_history"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 사용자 입력
user_input = st.chat_input("포트폴리오 리밸런싱이나 노후 준비에 대해 무엇이든 물어보세요.")

if user_input:
    # 1. 사용자 메시지 화면에 표시 및 저장
    st.session_state["chat_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. AI 응답 생성 준비
    with st.chat_message("assistant"):
        with st.spinner("고객님의 포트폴리오 데이터를 분석 중입니다..."):
            try:
                # DB 데이터 요약본 가져오기
                portfolio_context = get_portfolio_context()
                
                # 벡터 DB 가져오기 (지식 베이스)
                vector_db = create_vector_db()
                retriever = vector_db.as_retriever(search_kwargs={"k": 3})
                
                # LLM 세팅
                llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.3)
                
                # 💡 깔끔해진 프롬프트 호출!
                system_prompt = system_prompt = get_ai_coach_system_prompt(portfolio_context)

                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("human", "{input}")
                ])
                
                # 체인 생성 및 실행
                question_answer_chain = create_stuff_documents_chain(llm, prompt)
                rag_chain = create_retrieval_chain(retriever, question_answer_chain)
                
                response = rag_chain.invoke({"input": user_input})
                answer = response["answer"]
                
                # 응답 출력 및 저장
                st.markdown(answer)
                st.session_state["chat_history"].append({"role": "assistant", "content": answer})
                
            except Exception as e:
                st.error(f"응답 생성 중 오류가 발생했습니다: {e}")