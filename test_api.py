import requests
import os
import email.utils
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# .env 파일에서 API 키를 불러옵니다. (앱을 실행할 때와 동일한 환경)
load_dotenv()
naver_id = os.getenv("NAVER_CLIENT_ID")
naver_secret = os.getenv("NAVER_CLIENT_SECRET")

if not naver_id or not naver_secret:
    print("❌ 에러: API 키를 찾을 수 없습니다. .env 파일을 확인해주세요.")
    exit()

# 테스트용 검색어 (거시경제)
query = "거시경제"
url = "https://openapi.naver.com/v1/search/news.json"
headers = {"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret}

print("=== 🔍 1. API 원본 호출 테스트 ===")
# 일부러 10개만 가져와서 꼼꼼히 뜯어봅니다.
res = requests.get(url, headers=headers, params={"query": query, "display": 10, "sort": "date"})

if res.status_code != 200:
    print(f"❌ API 호출 에러 발생 (상태 코드: {res.status_code})")
    print(res.text)
    exit()

items = res.json().get("items", [])
print(f"✅ 성공적으로 {len(items)}개의 기사를 네이버에서 받아왔습니다.\n")

print("=== ⏱️ 2. 날짜 파싱 및 필터링 로직 검증 ===")
kst = timezone(timedelta(hours=9))
today = datetime.now(kst).date()
recent_limit_3 = today - timedelta(days=3)

print(f"▶ 현재 설정된 '오늘' KST 기준: {today}")
print(f"▶ 최근 3일 커트라인 기준: {recent_limit_3}\n")

for i, item in enumerate(items):
    raw_date = item.get('pubDate', '')
    title = item['title'].replace('<b>', '').replace('</b>', '')
    
    try:
        # 네이버의 원본 날짜를 우리가 다룰 수 있는 날짜 객체로 변환
        parsed_date = email.utils.parsedate_to_datetime(raw_date).astimezone(kst).date()
        
        # 3일 이내인지 판별
        is_within_3_days = parsed_date >= recent_limit_3
        
        print(f"[{i+1}] {title[:30]}...") # 제목은 너무 기니까 30자만 출력
        print(f"   - 네이버 원본 날짜 (pubDate): {raw_date}")
        print(f"   - 파이썬 변환 날짜: {parsed_date}")
        if is_within_3_days:
            print(f"   - 판정: ✅ 통과 (3일 이내 기사입니다)")
        else:
            print(f"   - 판정: ❌ 탈락 (너무 오래된 기사입니다)")
        print("-" * 50)
            
    except Exception as e:
        print(f"[{i+1}] ⚠️ 날짜 변환 실패: {raw_date} (에러 원인: {e})")