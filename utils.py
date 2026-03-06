import sqlite3
import pandas as pd
import os
import streamlit as st

# 💡 AI 수석코치 (RAG)용 라이브러리 추가
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

DB_PATH = 'portfolio.db'
DATA_DIR = 'data' 

def init_db():
    """데이터베이스와 테이블을 생성하고, data 폴더에 초기 CSV가 있다면 DB로 마이그레이션합니다."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 포트폴리오 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_type TEXT NOT NULL,  -- 'isa', 'irp', 'pension'
            ticker TEXT NOT NULL,
            etf_name TEXT NOT NULL,
            unit REAL DEFAULT 0,
            budget REAL DEFAULT 0,
            actual REAL DEFAULT 0
        )
    ''')
    
    # 2. 사용자 설정 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    
    # [마이그레이션] DB가 비어있을 때만 data 폴더를 뒤져서 이사
    cursor.execute("SELECT COUNT(*) FROM portfolio")
    if cursor.fetchone()[0] == 0:
        csv_files = {
            'isa': 'asset_position_isa.csv',
            'irp': 'asset_position_irp.csv',
            'pension': 'asset_position_pension.csv'
        }
        
        for account, file_name in csv_files.items():
            file_path = os.path.join(DATA_DIR, file_name) 
            
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                df.columns = df.columns.str.strip() 
                
                # 💡 [핵심 방어 로직] CSV의 빈 행과 결측치를 완벽하게 청소합니다!
                if 'Ticker' in df.columns:
                    df = df.dropna(subset=['Ticker']) # Ticker가 없는 껍데기 빈 줄(엔터) 삭제
                
                # 비어있는 셀(NaN)을 기본값으로 채워넣어 NOT NULL 에러 방지
                df = df.fillna({
                    'ETF Name': '알 수 없음', 
                    'Unit': 0, 
                    'Budget': 0, 
                    'Actual': 0
                })
                
                for _, row in df.iterrows():
                    cursor.execute('''
                        INSERT INTO portfolio (account_type, ticker, etf_name, unit, budget, actual)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        account, 
                        str(row['Ticker']).replace('.0',''), 
                        str(row['ETF Name']), # 안전하게 문자열 변환
                        float(row.get('Unit', 0)), 
                        float(row.get('Budget', 0)), 
                        float(row.get('Actual', 0))
                    ))
        conn.commit()
    
    conn.close()

# 앱 실행 시 무조건 한 번 DB를 초기화/체크
init_db()

def load_data(account_type):
    """특정 계좌의 포트폴리오 데이터를 불러와 DataFrame으로 반환합니다."""
    conn = sqlite3.connect(DB_PATH)
    query = f"SELECT ticker AS Ticker, etf_name AS 'ETF Name', unit AS Unit, budget AS Budget, actual AS Actual FROM portfolio WHERE account_type = '{account_type}'"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if not df.empty:
        df.set_index('Ticker', inplace=True)
    return df

def save_portfolio(account_type, action_df, current_df):
    """매매 완료 후 DB에 포트폴리오를 갱신합니다."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for ticker, row in action_df.iterrows():
        if row['Action Unit'] == 0: continue
        
        cursor.execute(f"SELECT unit, budget FROM portfolio WHERE account_type = ? AND ticker = ?", (account_type, str(ticker)))
        result = cursor.fetchone()
        
        if result:
            curr_unit, curr_budget = result
            action_u = row['Action Unit']
            live_p = row['Live Price']
            avg_price = curr_budget / curr_unit if curr_unit > 0 else live_p
            
            if action_u > 0: 
                new_unit = curr_unit + action_u
                new_budget = curr_budget + (action_u * live_p)
            else: 
                new_unit = curr_unit + action_u
                new_budget = 0 if new_unit <= 0 else curr_budget + (action_u * avg_price)
                
            cursor.execute('''
                UPDATE portfolio SET unit = ?, budget = ? WHERE account_type = ? AND ticker = ?
            ''', (new_unit, new_budget, account_type, str(ticker)))
            
    conn.commit()
    conn.close()

def color_diff_yield(val):
    if isinstance(val, str):
        val = float(val.replace(',', '').replace('%', '').replace(' 원', '').strip())
    color = '#e74c3c' if val < 0 else '#2ecc71' if val > 0 else 'gray'
    return f'color: {color}; font-weight: bold;'


# ==========================================
# 🤖 AI 수석코치용 벡터 데이터베이스 (RAG 엔진)
# ==========================================
@st.cache_resource # 💡 Streamlit 앱이 재실행될 때마다 매번 DB를 새로 만들지 않도록 캐싱(메모리 저장)합니다.
def create_vector_db(file_path="data/coach_knowledge.txt"):
    """
    텍스트 문서를 읽어 Gemini 임베딩을 통해 FAISS 벡터 DB로 변환합니다.
    (ai_coach.py 에서 이 함수를 호출하여 사용합니다)
    """
    # 1. 문서가 없다면 에러가 나지 않도록 기본 지식 파일을 자동 생성합니다.
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("이 문서는 AI 수석코치를 위한 기본 지식 베이스입니다. 사용자의 ISA, IRP, 연금저축 포트폴리오를 분석하고 최적의 자산 배분 조언을 제공합니다.")
    
    # 2. 문서 로드 및 쪼개기 (Chunking)
    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=100
    )
    docs = text_splitter.split_documents(documents)
    
    # 3. Gemini 임베딩 모델 세팅
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")
        
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001", # 💡 구글의 최신 텍스트 임베딩 모델로 교체!
        google_api_key=api_key
    )
    
    # 4. FAISS 벡터 데이터베이스 생성 및 반환
    vector_db = FAISS.from_documents(docs, embeddings)
    
    return vector_db