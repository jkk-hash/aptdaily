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
