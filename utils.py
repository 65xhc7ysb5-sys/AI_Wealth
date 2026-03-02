import streamlit as st
import pandas as pd
import os
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

@st.cache_data
def load_data(file_name):
    try:
        if not os.path.exists(file_name):
            return pd.DataFrame()
            
        df = pd.read_csv(file_name)
        total_mask = df['Ticker'].isna() | (df['Ticker'].astype(str).str.strip() == '') | (df['Ticker'].astype(str).str.lower() == 'nan')
        df = df[~total_mask].copy()
        df['Ticker'] = df['Ticker'].astype(str).str.replace('.0', '', regex=False)
        df.set_index('Ticker', inplace=True)
        
        if 'Weight(%)' not in df.columns and 'Weight' in df.columns:
            df['Weight(%)'] = df['Weight'].astype(str).str.replace('%', '').astype(float)
            
        for col in ['Budget', 'Actual', 'Difference']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('₩', '').str.replace(',', '').str.replace('\t', '').str.strip()
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        if 'Yield(%)' in df.columns:
            df['Yield(%)'] = pd.to_numeric(df['Yield(%)'].astype(str).str.replace('%', ''), errors='coerce').fillna(0.0)
            
        df = df[df['Actual'] > 0]
        
        if 'Actual' in df.columns and 'Budget' in df.columns and 'Difference' not in df.columns:
            df['Difference'] = df['Actual'] - df['Budget']
            
        return df
    except Exception as e:
        st.error(f"🚨 {file_name} 로드 중 오류 발생: {e}")
        return pd.DataFrame()

@st.cache_resource
def create_vector_db():
    try:
        loader = PyPDFDirectoryLoader("data")
        docs = loader.load()
        if not docs: return None
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        split_docs = text_splitter.split_documents(docs)
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        vectorstore = FAISS.from_documents(split_docs, embeddings)
        return vectorstore
    except Exception as e:
        return None

def color_diff_yield(val):
    if val < 0: return 'color: #2ecc71; font-weight: bold;'
    elif val > 0: return 'color: #e74c3c; font-weight: bold;'
    return ''

display_cols = ['ETF Name', 'Weight(%)', 'Budget', 'Actual', 'Difference', 'Yield(%)']