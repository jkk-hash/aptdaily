from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_streamlit_app_overview_and_daily_detail():
    """Streamlit 통합 UI 테스트: 전국 종합 대시보드 및 일자별 상세 분석 뷰 검증"""
    at = AppTest.from_file("../app.py", default_timeout=30)
    at.run()

    # 1. 초기 실행 (전국 종합 대시보드) 정상 렌더링 검증
    assert not at.exception, f"App execution failed with exception: {at.exception}"

    # 사이드바 라디오 메뉴 검증
    assert len(at.sidebar.radio) >= 1
    nav_radio = at.sidebar.radio[0]
    assert nav_radio.value == "📊 전국 종합 대시보드"

    # 2. 일자별 상세 분석 & AI 리포트 메뉴로 전환
    nav_radio.set_value("📅 일자별 상세 분석 & AI 리포트")
    at.run()

    assert not at.exception, f"Switching to daily detail view failed: {at.exception}"

    # 일자 선택 selectbox가 존재하는지 확인
    assert len(at.sidebar.selectbox) >= 1

    # AI 브리핑 카드 관련 마크다운 내용 검증
    markdown_texts = [m.value for m in at.markdown]
    combined_md = "\n".join(markdown_texts)

    assert "아파트 실거래 상세 분석" in combined_md
    assert "AI 부동산 수석 애널리스트" in combined_md
    assert "시장 동향 및 거래 활성도" in combined_md
    assert "주요 단지 심층 분석" in combined_md
    assert "애널리스트 총평 및 시사점" in combined_md

    # 캐시 파일이 data/reports에 생성되었는지 확인
    reports_dir = Path("data/reports")
    assert reports_dir.exists()
    cached_files = list(reports_dir.glob("*.json"))
    assert len(cached_files) >= 1, "Expected at least 1 cached daily report JSON file"
