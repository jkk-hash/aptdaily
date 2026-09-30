# 🏢 전국 아파트 실거래가(최근 7일) 대시보드

공공데이터포털(국토교통부 아파트매매 실거래가 OpenAPI)을 연동하여 **최근 7일간의 전국 아파트 매매 실거래가**를 매일 자동으로 수집하고 인터랙티브하게 시각화하는 **완전 무료(Zero-Cost Serverless)** 대시보드 시스템입니다.

---

## 🌟 주요 특징

1. **완전 무료 Zero-Infra 운영**:
   - 데이터 수집 및 스케줄러: **GitHub Actions** (매일 KST 02:00 자동 수집)
   - 데이터 저장소: **GitHub Repository** (`data/latest_7days.parquet` 롤링 보관)
   - 웹 대시보드 호스팅: **Streamlit Community Cloud** (무료 호스팅)
2. **초고속 압축 Parquet 롤링 파이프라인**:
   - 최근 7일(`T-7` ~ `T-1`) 데이터만 단일 Parquet 파일로 압축 관리하여 저장소 용량을 최소화하고 0.1초 미만의 빠른 로딩 속도 보장.
3. **보안 공급망 정책 준수**:
   - `pyproject.toml`에 `[tool.uv] exclude-newer = "10 days"` 정책을 기본 적용하여 외부 라이브러리 공급망 공격 및 해킹 위험을 사전에 차단.
4. **풍부한 인터랙티브 분석 기능**:
   - 전국 17개 시·도 및 250개 시·군·구 동적 계층 필터
   - 아파트 단지명 실시간 검색
   - 거래금액, 전용면적, 층수 슬라이더 필터링
   - 4대 핵심 KPI 카드 (총 거래량, 평균가, 평당 단가, 최고가 거래 단지)
   - 일자별 거래량 & 평균가 복합 추이 차트 (Plotly)
   - 전용면적 대비 거래가 산점도 및 시도별 3.3㎡당 단가 분포 박스플롯
   - 상세 거래 내역 인터랙티브 테이블 및 필터링 결과 CSV 다운로드

---

## 🏗️ 시스템 아키텍처

```
[국토교통부 OpenAPI]
        │
        ▼ (매일 KST 02:00 자동 수집)
[GitHub Actions (cron)] ──▶ uv 가상환경 (10일 Cooldown 보안 정책)
        │
        ▼ (필터링 & Snappy 압축)
[data/latest_7days.parquet] ──▶ Git Auto Commit & Push
        │
        ▼ (실시간 동기화)
[Streamlit Community Cloud] ──▶ 사용자 인터랙티브 웹 대시보드
```

---

## 🚀 로컬 실행 방법

### 1. 가상환경 및 의존성 설치
본 프로젝트는 초고속 패키지 관리자 `uv`를 사용합니다:
```bash
# 의존성 설치 (10일 쿨다운 보안 정책 자동 적용)
uv sync
```

### 2. 환경변수 설정 (선택 사항)
공공데이터포털 API 인증키가 있는 경우 `.env` 파일에 설정합니다:
```bash
cp .env.example .env
# .env 파일을 열고 DATA_GO_KR_API_KEY 입력
```
> **참고**: API 키가 없거나 미설정된 경우에도 대시보드 UI/UX를 즉시 테스트할 수 있도록 현실적인 샘플(Mock) 데이터가 자동 로드됩니다.

### 3. 데이터 수집 실행
```bash
# 수집기 실행 (최근 7일 실거래가 수집 및 data/latest_7days.parquet 생성)
uv run python src/collector.py
```

### 4. 대시보드 실행
```bash
uv run streamlit run app.py
```
브라우저에서 `http://localhost:8501`로 대시보드가 열립니다.

### 5. 테스트 스위트 실행
```bash
uv run pytest
```

---

## ☁️ GitHub 배포 및 무료 호스팅 가이드

### 1. GitHub 원격 저장소 생성 및 푸시
```bash
git init
git add .
git commit -m "feat: initial commit for apartment dashboard"
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git branch -M main
git push -u origin main
```

### 2. GitHub Actions Secrets 등록
1. GitHub 저장소의 **Settings** > **Secrets and variables** > **Actions** 메뉴로 이동합니다.
2. **New repository secret** 버튼을 클릭합니다:
   - Name: `DATA_GO_KR_API_KEY`
   - Secret: 공공데이터포털에서 발급받은 일반 인증키(Encoding/Decoding 키) 입력

### 3. Streamlit Community Cloud 배포
1. [share.streamlit.io](https://share.streamlit.io/)에 접속하여 GitHub 계정으로 로그인합니다.
2. **New app** 버튼을 클릭합니다.
3. 생성한 저장소(`Repository`), 브랜치(`main`), 메인 파일 경로(`app.py`)를 선택합니다.
4. **Deploy!** 버튼을 클릭하면 1~2분 내에 전 세계 어디서나 접속 가능한 고유 URL이 생성됩니다.

---

## 📁 프로젝트 구조

```text
├── .github/
│   └── workflows/
│       └── daily_collect.yml   # GitHub Actions 매일 수집 워크플로우
├── data/
│   ├── lawd_cd.json            # 전국 시군구 법정동 코드 (250개)
│   ├── latest_7days.parquet    # 최근 7일 실거래가 데이터 (압축)
│   └── metadata.json           # 수집 시각 및 데이터 기간 메타데이터
├── src/
│   ├── __init__.py
│   ├── collector.py            # 공공데이터 API 수집 및 정제기
│   └── utils.py                # 날짜 범위 및 금액 포맷팅 유틸리티
├── tests/
│   ├── test_collector.py       # 수집기 단위 테스트 (5개)
│   └── test_dashboard.py       # 대시보드 로직 단위 테스트 (5개)
├── .env.example                # 환경변수 템플릿
├── .gitignore                  # Git 무시 파일 목록
├── app.py                      # Streamlit 메인 대시보드 애플리케이션
├── pyproject.toml              # 프로젝트 의존성 및 uv 보안 설정(exclude-newer)
└── README.md                   # 프로젝트 문서
```
