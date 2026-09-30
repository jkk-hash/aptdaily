from datetime import date
import pandas as pd

try:
    from src.collector import clean_and_filter_deals, parse_xml_items
    from src.utils import format_korean_currency, get_recent_7days_range, get_target_ymd_list
except (ImportError, ModuleNotFoundError):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.collector import clean_and_filter_deals, parse_xml_items
    from src.utils import format_korean_currency, get_recent_7days_range, get_target_ymd_list


def test_get_recent_7days_range():
    ref_date = date(2026, 9, 30)
    # 기본값: 오늘(9월 30일) 포함 7일 (2026-09-24 ~ 2026-09-30)
    start_date, end_date = get_recent_7days_range(ref_date)
    assert start_date == date(2026, 9, 24)
    assert end_date == date(2026, 9, 30)

    # 전일 기준 7일 (2026-09-23 ~ 2026-09-29)
    start_date_prev, end_date_prev = get_recent_7days_range(ref_date, include_today=False)
    assert start_date_prev == date(2026, 9, 23)
    assert end_date_prev == date(2026, 9, 29)


def test_get_target_ymd_list():
    # 월 경계에 걸치는 경우 (예: 2026-10-04 -> 2026-09-27 ~ 2026-10-03)
    start_date = date(2026, 9, 27)
    end_date = date(2026, 10, 3)
    ymd_list = get_target_ymd_list(start_date, end_date)
    assert ymd_list == ['202609', '202610']

    # 같은 달 내에 있는 경우 (2026-09-23 ~ 2026-09-29)
    ymd_list_same = get_target_ymd_list(date(2026, 9, 23), date(2026, 9, 29))
    assert ymd_list_same == ['202609']


def test_format_korean_currency():
    assert format_korean_currency(85000) == "8억 5,000만원"
    assert format_korean_currency(120000) == "12억원"
    assert format_korean_currency(4500) == "4,500만원"
    assert format_korean_currency(0) == "0원"


def test_parse_xml_items():
    sample_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <response>
        <header>
            <resultCode>00</resultCode>
            <resultMsg>NORMAL SERVICE.</resultMsg>
        </header>
        <body>
            <items>
                <item>
                    <dealAmount>   85,000</dealAmount>
                    <buildYear>2018</buildYear>
                    <dealYear>2026</dealYear>
                    <dealMonth>9</dealMonth>
                    <dealDay>25</dealDay>
                    <dong>역삼동</dong>
                    <aptName>역삼래미안</aptName>
                    <excluUseAr>84.95</excluUseAr>
                    <floor>12</floor>
                    <sggCd>11680</sggCd>
                </item>
            </items>
        </body>
    </response>
    """
    items = parse_xml_items(sample_xml)
    assert len(items) == 1
    assert items[0]['aptName'] == '역삼래미안'
    assert items[0]['dealAmount'].strip() == '85,000'


def test_clean_and_filter_deals():
    raw_records = [
        {
            'sggCd': '11680', 'dong': '역삼동', 'aptName': '역삼래미안',
            'dealYear': 2026, 'dealMonth': 9, 'dealDay': 25,
            'dealAmount': '   85,000', 'excluUseAr': 84.95, 'floor': 12, 'buildYear': 2018
        },
        # 날짜 범위 밖 (너무 이전: 9월 10일)
        {
            'sggCd': '11680', 'dong': '역삼동', 'aptName': '역삼아이파크',
            'dealYear': 2026, 'dealMonth': 9, 'dealDay': 10,
            'dealAmount': '  120,000', 'excluUseAr': 84.95, 'floor': 5, 'buildYear': 2015
        },
        # 중복 레코드
        {
            'sggCd': '11680', 'dong': '역삼동', 'aptName': '역삼래미안',
            'dealYear': 2026, 'dealMonth': 9, 'dealDay': 25,
            'dealAmount': '   85,000', 'excluUseAr': 84.95, 'floor': 12, 'buildYear': 2018
        }
    ]
    df_raw = pd.DataFrame(raw_records)
    start_date = date(2026, 9, 23)
    end_date = date(2026, 9, 29)

    df_clean = clean_and_filter_deals(df_raw, start_date, end_date)
    assert len(df_clean) == 1
    row = df_clean.iloc[0]
    assert row['apt_name'] == '역삼래미안'
    assert row['deal_amount'] == 85000
    assert row['deal_date'] == date(2026, 9, 25)
    # 84.95 / 3.305785 = 25.697평 -> 85000 / 25.697 = ~3307.7만원
    assert 3300 < row['price_per_pyeong'] < 3320
