from datetime import date
import pandas as pd
import pytest

try:
    from app import calculate_kpis, filter_data, get_daily_trend
except (ImportError, ModuleNotFoundError):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app import calculate_kpis, filter_data, get_daily_trend


@pytest.fixture
def sample_df():
    records = [
        {
            'province': '서울특별시', 'sigungu': '강남구', 'sigungu_cd': '11680',
            'bjdong': '개포동', 'apt_name': '디에이치퍼스티어아이파크', 'deal_date': date(2026, 9, 25),
            'deal_amount': 295000, 'exclu_use_ar': 84.9, 'pyeong': 25.7, 'price_per_pyeong': 11478.6,
            'floor': 15, 'build_year': 2024
        },
        {
            'province': '서울특별시', 'sigungu': '서초구', 'sigungu_cd': '11650',
            'bjdong': '반포동', 'apt_name': '아크로리버파크', 'deal_date': date(2026, 9, 26),
            'deal_amount': 430000, 'exclu_use_ar': 84.95, 'pyeong': 25.7, 'price_per_pyeong': 16731.5,
            'floor': 20, 'build_year': 2016
        },
        {
            'province': '경기도', 'sigungu': '성남시 분당구', 'sigungu_cd': '41135',
            'bjdong': '정자동', 'apt_name': '파크뷰', 'deal_date': date(2026, 9, 27),
            'deal_amount': 210000, 'exclu_use_ar': 139.9, 'pyeong': 42.3, 'price_per_pyeong': 4964.5,
            'floor': 8, 'build_year': 2004
        }
    ]
    return pd.DataFrame(records)


def test_filter_data_by_province(sample_df):
    filtered = filter_data(sample_df, selected_provinces=['서울특별시'])
    assert len(filtered) == 2
    assert set(filtered['province']) == {'서울특별시'}


def test_filter_data_by_apt_name(sample_df):
    filtered = filter_data(sample_df, apt_search='아크로')
    assert len(filtered) == 1
    assert filtered.iloc[0]['apt_name'] == '아크로리버파크'


def test_filter_data_by_price_range(sample_df):
    # 20억원 이상 30억원 이하 (200000 ~ 300000 만원)
    filtered = filter_data(sample_df, min_price=200000, max_price=300000)
    assert len(filtered) == 2
    assert '아크로리버파크' not in filtered['apt_name'].values


def test_calculate_kpis(sample_df):
    kpis = calculate_kpis(sample_df)
    assert kpis['total_count'] == 3
    # 평균: (295000 + 430000 + 210000) / 3 = 311666.67
    assert 311600 < kpis['avg_amount'] < 311700
    assert kpis['max_trade']['apt_name'] == '아크로리버파크'
    assert kpis['max_trade']['deal_amount'] == 430000


def test_get_daily_trend(sample_df):
    trend = get_daily_trend(sample_df)
    assert len(trend) == 3
    assert 'deal_count' in trend.columns
    assert 'avg_amount' in trend.columns


def test_filter_data_by_date(sample_df):
    target_date = date(2026, 9, 26)
    filtered = filter_data(sample_df, selected_dates=[target_date])
    assert len(filtered) == 1
    assert filtered.iloc[0]['apt_name'] == '아크로리버파크'
    assert filtered.iloc[0]['deal_amount'] == 430000


def test_daily_kpis_for_single_date(sample_df):
    target_date = date(2026, 9, 26)
    daily_df = filter_data(sample_df, selected_dates=[target_date])
    kpis = calculate_kpis(daily_df)
    assert kpis['total_count'] == 1
    assert kpis['avg_amount'] == 430000
    assert kpis['max_trade']['apt_name'] == '아크로리버파크'
