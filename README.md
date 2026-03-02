# File Structure

Linchpin_Wealth/
├── app.py              (🚀 실행 및 메뉴 네비게이션 담당)
├── utils.py            (⚙️ 데이터 로드 & RAG 등 공통 기능 담당)
├── views/              (📂 새로 만들 폴더: 화면 UI 파일들 보관)
│   ├── home.py         (화면 1: 대시보드)
│   ├── track_a.py      (화면 2: 내집마련)
│   ├── track_b.py      (화면 3: 노후준비)
│   └── ai_coach.py     (화면 4: AI 코치)
├── data/               (PDF 파일들)
├── .env
└── asset_position_feb_2026.csv