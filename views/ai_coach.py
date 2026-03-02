import streamlit as st
import os
from utils import load_data, create_vector_db
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain
from langchain_google_genai import ChatGoogleGenerativeAI

st.title("💬 Linchpin AI 수석 코치")
st.markdown("정훈 님이 업로드한 초고급 웰스 리포트와 거시경제 자료를 바탕으로 프라이빗 상담을 진행합니다.")

df_isa = load_data('data/asset_position_isa.csv')
df_pension = load_data('data/asset_position_pension.csv')
df_irp = load_data('data/asset_position_irp.csv')
vectorstore = create_vector_db()

api_key = os.getenv("GEMINI_API_KEY")

if st.button("🔥 목표 기반(Goal-Based) 전체 포트폴리오 정밀 진단받기"):
    if not api_key:
        st.error("API 키를 확인해주세요.")
    elif vectorstore is None:
        st.warning("데이터베이스가 없습니다. PDF 파일을 1-2개만 남기고 다시 시도해주세요.")
    else:
        with st.spinner("AI가 각 계좌(ISA, 연금, IRP)의 데이터를 통합 분석 중입니다..."):
            try:
                llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0.3)
                system_prompt = (
                    "당신은 대한민국 상위 10% 자산가를 위한 'Linchpin Wealth 수석 AI 자산관리 코치'입니다.\n"
                    "아래 [Context]를 활용하되, 고객의 상황(내집마련/노후)에 맞게 유연하게 해석하세요.\n"
                    "**[절대 준수]** 1. 환각 방지(국가별 정책 분리) 2. 비현실적 대안투자 추천 지양 3. ISA/IRP 활용 절세 팁 반드시 포함.\n\n"
                    "[Context]\n{context}"
                )
                prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])
                retriever = vectorstore.as_retriever(search_kwargs={"k": 3}) 
                rag_chain = create_retrieval_chain(retriever, create_stuff_documents_chain(llm, prompt))
                
                portfolio_context = ""
                if not df_isa.empty: portfolio_context += f"[ISA 계좌 (내집마련용)]\n{df_isa[['ETF Name', 'Difference']].to_string()}\n\n"
                if not df_pension.empty: portfolio_context += f"[개인연금 계좌 (노후용)]\n{df_pension[['ETF Name', 'Difference']].to_string()}\n\n"
                if not df_irp.empty: portfolio_context += f"[IRP 계좌 (노후용)]\n{df_irp[['ETF Name', 'Difference']].to_string()}\n"

                user_question = f"고객: 정훈 (40대 남성). 목표: 1. 단기 내집마련 2. 장기 노후자금 확보.\n현재 자산 현황:\n{portfolio_context}\n\nTrack A(ISA 방어막 점검), Track B(노후 주식 추천), 구체적 절세 팁(ISA/IRP) 3가지를 분리해서 조언해줘."
                
                res = rag_chain.invoke({"input": user_question})
                st.info(res["answer"])
            except Exception as e:
                st.error(f"오류 발생: {e}")