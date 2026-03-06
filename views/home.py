import streamlit as st
import requests
import os
import html
import json
import re
import email.utils           # 💡 추가: 날짜 파싱용 모듈
from datetime import datetime, timezone, timedelta # 💡 추가: 시간 계산용 모듈
from utils import load_data
from langchain_google_genai import ChatGoogleGenerativeAI
from prompts import get_news_briefing_prompt

# ==========================================
# 🔍 1. 보조 함수: 내 포트폴리오 '핵심 키워드' 스마트 추출
# ==========================================
def get_my_portfolio_keywords():
    raw_etf_names = set()
    
    for acc_type in ['isa', 'irp', 'pension']:
        df = load_data(acc_type)
        if not df.empty:
            for name in df['ETF Name']:
                raw_etf_names.add(name)
                
    raw_etf_list = list(raw_etf_names)
    
    search_keywords = set()
    for name in raw_etf_list:
        name_upper = name.upper()
        if "나스닥" in name_upper: search_keywords.add("나스닥")
        elif "S&P" in name_upper: search_keywords.add("S&P500")
        elif "다우존스" in name_upper: search_keywords.add("다우존스")
        elif "코리아" in name_upper: search_keywords.add("KOSPI")
        elif "중국" in name_upper or "차이나" in name_upper: search_keywords.add("중국 증시")
        elif "인도" in name_upper: search_keywords.add("인도 증시")
        elif "배당" in name_upper: search_keywords.add("배당주")
        elif "채권" in name_upper or "국고채" in name_upper: search_keywords.add("금리 인하")
        elif "리츠" in name_upper or "REITS" in name_upper: search_keywords.add("부동산 리츠")
        elif "금" in name_upper: search_keywords.add("금")
        else:
            clean_name = name.replace("TIGER", "").replace("KODEX", "").replace("ACE", "").replace("RISE", "").strip()
            if clean_name:
                search_keywords.add(clean_name.split()[0])
                
    return raw_etf_list, list(search_keywords)


# ==========================================
# 2. 종합 자산 요약
# ==========================================
st.subheader("💼 나의 종합 자산 요약")

accounts = {'ISA (내집마련)': 'isa', 'IRP (퇴직연금)': 'irp', '연금저축': 'pension'}
col1, col2, col3 = st.columns(3)
cols = [col1, col2, col3]

for i, (acc_name, acc_type) in enumerate(accounts.items()):
    df = load_data(acc_type)
    if not df.empty:
        total_budget = df['Budget'].sum()
        total_actual = df['Actual'].sum()
        profit = total_actual - total_budget
        yield_pct = (profit / total_budget * 100) if total_budget > 0 else 0
        
        cols[i].metric(
            label=acc_name, 
            value=f"{total_actual/10000:,.0f} 만원", 
            delta=f"{profit/10000:,.0f}만원 ({yield_pct:.2f}%)"
        )
    else:
        cols[i].metric(label=acc_name, value="0 원", delta="데이터 없음", delta_color="off")


# ==========================================
# 📰 3. AI 뉴스 브리핑 파이프라인 (업그레이드 버전)
# ==========================================
@st.cache_data(ttl=10800)
def get_ai_news_briefing(raw_etfs, search_keywords):
    naver_id = os.getenv("NAVER_CLIENT_ID")
    naver_secret = os.getenv("NAVER_CLIENT_SECRET")
    
    if not naver_id or not naver_secret:
        return None
    
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret}
    
    # 💡 1. 스마트 필터링이 적용된 fetch_news 함수로 교체
    def fetch_news(query, max_results=10):
        try:
            res = requests.get(url, headers=headers, params={"query": query, "display": 100, "sort": "date"})
            res.raise_for_status()
            items = res.json().get("items", [])
            
            kst = timezone(timedelta(hours=9))
            today = datetime.now(kst).date()
            
            parsed_items = []
            for item in items:
                pub_date_str = item.get('pubDate', '')
                try:
                    pub_date = email.utils.parsedate_to_datetime(pub_date_str).astimezone(kst).date()
                except Exception:
                    continue 
                    
                title = html.unescape(item['title'].replace('<b>', '').replace('</b>', ''))
                desc = html.unescape(item['description'].replace('<b>', '').replace('</b>', ''))
                
                parsed_items.append({
                    "date": pub_date,
                    "date_str": pub_date_str,
                    "title": title,
                    "link": item['link'],
                    "desc": desc
                })

            # 스마트 폴백 전략 (3일 -> 7일 -> 무조건 최신)
            target_items = [item for item in parsed_items if item["date"] >= today - timedelta(days=3)]
            if not target_items:
                target_items = [item for item in parsed_items if item["date"] >= today - timedelta(days=7)]
            if not target_items:
                target_items = parsed_items[:max_results]

            text = ""
            for i, item in enumerate(target_items[:max_results]):
                text += f"[키워드: {query} / 기사 번호: {i+1}]\n발행일: {item['date_str']}\n제목: {item['title']}\n링크: {item['link']}\n내용: {item['desc']}\n---\n"
                
            return text
        except Exception as e:
            print(f"News Fetch Error ({query}): {e}")
            return ""

    # 💡 2. 'OR' 연산자 제거 및 단일 키워드 기반으로 변경
    macro_news_text = fetch_news("증시 전망", 15)
    
    portfolio_news_text = ""
    my_holdings_str = "보유 종목 없음"
    
    if search_keywords:
        # 내 종목 키워드를 하나씩 순회하며 뉴스를 모음
        for keyword in search_keywords[:3]: 
            portfolio_news_text += fetch_news(keyword, 10) + "\n"
        my_holdings_str = ", ".join(raw_etfs) 

    # 뉴스가 부족할 경우 대체 키워드
    if not portfolio_news_text.strip():
        portfolio_news_text = fetch_news("국내 증시", 10)

    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)
        prompt = get_news_briefing_prompt(my_holdings_str, macro_news_text, portfolio_news_text)
        
        ai_response = llm.invoke(prompt)
        return ai_response.content
        
    except Exception as e:
        print(f"Error fetching AI news: {e}")
        return None

# ==========================================
# 🖥️ 3. 홈 대시보드 UI 렌더링
# ==========================================
st.title("📊 Linchpin Wealth 대시보드")
st.markdown("나만의 맞춤형 자산 관리 현황과 오늘의 핵심 시황을 한눈에 확인하세요.")

# ------------------------------------------
# ▶ 상단: AI 뉴스 브리핑 섹션 (카드 UI 적용)
# ------------------------------------------
st.subheader("🌅 오늘의 AI 맞춤 시황 브리핑")

raw_etfs, search_keywords = get_my_portfolio_keywords()

with st.spinner("AI 편집장이 시장 동향과 고객님의 보유 종목 관련 뉴스를 분석 중입니다..."):
    news_briefing_raw = get_ai_news_briefing(raw_etfs, search_keywords)

if news_briefing_raw:
    try:
        # 💡 3. 정규식 오류 수정 및 JSON 안전 파싱 로직 추가
        json_match = re.search(r'```json\n(.*?)\n```', news_briefing_raw, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            start_idx = news_briefing_raw.find('{')
            end_idx = news_briefing_raw.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_text = news_briefing_raw[start_idx:end_idx+1]
            else:
                json_text = "{}"

        news_data = json.loads(json_text)

        st.markdown("#### 🌍 거시경제 핵심 요약")
        if "macro_news" in news_data and news_data["macro_news"]:
            for news in news_data["macro_news"]:
                with st.expander(f"📌 {news.get('title', '제목 없음')}"):
                    st.write(news.get("summary", "내용이 없습니다."))
                    st.markdown(f"[기사 원문 보기]({news.get('link', '#')})")
        else:
            st.info("관련된 거시경제 뉴스가 없습니다.")

        st.markdown("---")

        st.markdown("#### 💼 내 보유 종목 맞춤 시황")
        if "portfolio_news" in news_data and news_data["portfolio_news"]:
            for news in news_data["portfolio_news"]:
                with st.expander(f"💡 {news.get('title', '제목 없음')}"):
                    st.write(news.get("summary", "내용이 없습니다."))
                    st.info(f"**연관 보유 종목:** {news.get('related_etfs', '정보 없음')}")
                    st.markdown(f"[기사 원문 보기]({news.get('link', '#')})")
        else:
            st.info("현재 보유 종목과 관련된 특별한 뉴스가 없습니다.")

    except json.JSONDecodeError:
        st.error("AI가 분석한 결과를 화면에 표시하는 데 실패했습니다.")
        with st.expander("AI 원본 분석 결과 보기"):
            st.text(news_briefing_raw)
else:
    st.warning("오늘의 뉴스를 불러오지 못했습니다. 네트워크 상태나 API 키를 확인해주세요.")