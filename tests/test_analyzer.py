from datetime import date
import pandas as pd

from src.analyzer import build_analyst_prompt, generate_local_fallback_summary


def test_build_analyst_prompt():
    records = [
        {
            'province': '서울특별시', 'sigungu': '서초구', 'bjdong': '반포동',
            'apt_name': '래미안원베일리', 'deal_date': date(2026, 9, 29),
            'deal_amount': 460000, 'exclu_use_ar': 92.2, 'pyeong': 27.9,
            'price_per_pyeong': 16487.5, 'floor': 4, 'build_year': 2023
        },
        {
            'province': '서울특별시', 'sigungu': '강남구', 'bjdong': '대치동',
            'apt_name': '은마', 'deal_date': date(2026, 9, 29),
            'deal_amount': 305000, 'exclu_use_ar': 76.79, 'pyeong': 23.2,
            'price_per_pyeong': 13146.6, 'floor': 1, 'build_year': 1979
        }
    ]
    df = pd.DataFrame(records)
    prompt = build_analyst_prompt(date(2026, 9, 29), df)
    assert "2026-09-29" in prompt
    assert "래미안원베일리" in prompt
    assert "46억원" in prompt
    assert "수석 부동산 애널리스트" in prompt


def test_generate_local_fallback_summary():
    records = [
        {
            'province': '서울특별시', 'sigungu': '서초구', 'bjdong': '반포동',
            'apt_name': '래미안원베일리', 'deal_date': date(2026, 9, 29),
            'deal_amount': 460000, 'exclu_use_ar': 92.2, 'pyeong': 27.9,
            'price_per_pyeong': 16487.5, 'floor': 4, 'build_year': 2023
        }
    ]
    df = pd.DataFrame(records)
    summary = generate_local_fallback_summary(date(2026, 9, 29), df)
    assert summary['deal_date'] == "2026-09-29"
    assert summary['engine'] == "local-analyst-fallback"
    assert "headline" in summary
    assert "market_trend" in summary
    assert "key_complexes" in summary
    assert "analyst_opinion" in summary
    assert "래미안원베일리" in summary['key_complexes']


def test_cache_save_and_load(tmp_path):
    from src.analyzer import save_cached_report, load_cached_report

    test_date = date(2026, 9, 29)
    sample_report = {
        "deal_date": "2026-09-29",
        "engine": "gemini-1.5-flash",
        "headline": "반포 래미안원베일리 46억 최고가 신고",
        "market_trend": "거래량 유지",
        "key_complexes": "원베일리 심층 분석",
        "analyst_opinion": "선별적 투자 유효",
    }

    # 처음에는 캐시가 없어야 함
    assert load_cached_report(test_date, cache_dir=tmp_path) is None

    # 저장
    saved_path = save_cached_report(test_date, sample_report, cache_dir=tmp_path)
    assert saved_path.exists()
    assert saved_path.name == "2026-09-29.json"

    # 로드
    loaded = load_cached_report(test_date, cache_dir=tmp_path)
    assert loaded is not None
    assert loaded["headline"] == sample_report["headline"]
    assert loaded["engine"] == "gemini-1.5-flash"


def test_path_traversal_defense(tmp_path):
    from src.analyzer import save_cached_report, load_cached_report

    # deal_date는 반드시 datetime.date 타입이어야 함 (문자열이나 ../ 경로 주입 불가)
    import pytest
    with pytest.raises((TypeError, ValueError)):
        save_cached_report("../../etc/passwd", {}, cache_dir=tmp_path)  # type: ignore

    with pytest.raises((TypeError, ValueError)):
        load_cached_report("../../etc/passwd", cache_dir=tmp_path)  # type: ignore

