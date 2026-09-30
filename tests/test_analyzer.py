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
        load_cached_report("../../etc/passwd", cache_dir=tmp_path)


def test_parse_gemini_markdown_response():
    from src.analyzer import parse_gemini_response

    sample_gemini_text = """### [오늘의 시황 헤드라인]
서초·강남 중심 랜드마크 신고가 지속 속 수도권 거래 주도

### [시장 동향 및 거래 활성도]
금일 전국 실거래는 총 120건으로 집계되었으며 평당 3,500만원 선에서 유지 중입니다.

### [주요 단지 심층 분석]
래미안원베일리 46억 거래는 희소성 높은 한강변 프리미엄을 반영합니다.

### [애널리스트 총평 및 시사점]
선별적 똘똘한 한 채 쏠림 현상이 심화되므로 무리한 대출보다는 핵심지 위주 분할 접근이 필요합니다.
"""
    parsed = parse_gemini_response(sample_gemini_text)
    assert "서초·강남" in parsed["headline"]
    assert "120건" in parsed["market_trend"]
    assert "래미안원베일리" in parsed["key_complexes"]
    assert "똘똘한 한 채" in parsed["analyst_opinion"]


def test_call_gemini_api_success(monkeypatch):
    from src.analyzer import call_gemini_api

    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "### [오늘의 시황 헤드라인]\n테스트 헤드라인"}
                            ]
                        }
                    }
                ]
            }

        def raise_for_status(self):
            pass

    monkeypatch.setattr("requests.post", lambda url, **kwargs: MockResponse())

    res = call_gemini_api("테스트 프롬프트", api_key="dummy_api_key")
    assert "테스트 헤드라인" in res


def test_get_or_create_daily_report_cache_first(tmp_path, monkeypatch):
    from src.analyzer import get_or_create_daily_report, save_cached_report

    test_date = date(2026, 9, 29)
    existing_report = {
        "deal_date": "2026-09-29",
        "engine": "gemini-1.5-flash",
        "headline": "기존 캐시된 헤드라인",
        "market_trend": "캐시 동향",
        "key_complexes": "캐시 단지",
        "analyst_opinion": "캐시 총평",
    }
    save_cached_report(test_date, existing_report, cache_dir=tmp_path)

    # API가 호출되면 안 됨 - 호출 시 에러를 유발하는 mock 설정
    def fail_if_called(*args, **kwargs):
        raise RuntimeError("API should NOT be called when cache exists!")

    monkeypatch.setattr("requests.post", fail_if_called)

    df = pd.DataFrame([{"deal_amount": 10000, "price_per_pyeong": 1000}])
    report = get_or_create_daily_report(test_date, df, api_key="dummy", cache_dir=tmp_path)
    assert report["headline"] == "기존 캐시된 헤드라인"


def test_get_or_create_daily_report_without_api_key(tmp_path, monkeypatch):
    from src.analyzer import get_or_create_daily_report

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    test_date = date(2026, 9, 29)
    records = [
        {
            'province': '서울특별시', 'sigungu': '서초구', 'bjdong': '반포동',
            'apt_name': '래미안원베일리', 'deal_date': date(2026, 9, 29),
            'deal_amount': 460000, 'exclu_use_ar': 92.2, 'pyeong': 27.9,
            'price_per_pyeong': 16487.5, 'floor': 4, 'build_year': 2023
        }
    ]
    df = pd.DataFrame(records)
    report = get_or_create_daily_report(test_date, df, api_key=None, cache_dir=tmp_path)

    assert report["engine"] == "local-analyst-fallback"
    assert "래미안원베일리" in report["headline"]

    # 캐시 파일이 실제로 저장되었는지 확인
    cache_file = tmp_path / "2026-09-29.json"
    assert cache_file.exists()


def test_get_or_create_daily_report_force_refresh(tmp_path, monkeypatch):
    from src.analyzer import get_or_create_daily_report, save_cached_report

    test_date = date(2026, 9, 29)
    existing_report = {
        "deal_date": "2026-09-29",
        "engine": "local-analyst-fallback",
        "headline": "구버전 헤드라인",
        "market_trend": "구버전 동향",
        "key_complexes": "구버전 단지",
        "analyst_opinion": "구버전 총평",
    }
    save_cached_report(test_date, existing_report, cache_dir=tmp_path)

    # API 응답을 mocking
    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": "### [오늘의 시황 헤드라인]\n신규 강제갱신 헤드라인\n\n"
                                            "### [시장 동향 및 거래 활성도]\n신규 동향\n\n"
                                            "### [주요 단지 심층 분석]\n신규 단지\n\n"
                                            "### [애널리스트 총평 및 시사점]\n신규 총평"
                                }
                            ]
                        }
                    }
                ]
            }

        def raise_for_status(self):
            pass

    monkeypatch.setattr("requests.post", lambda url, **kwargs: MockResponse())

    df = pd.DataFrame([{"deal_amount": 10000, "price_per_pyeong": 1000}])
    # force_refresh=True 로 호출
    new_report = get_or_create_daily_report(
        test_date, df, api_key="test_key", cache_dir=tmp_path, force_refresh=True
    )
    assert new_report["headline"] == "신규 강제갱신 헤드라인"
    assert new_report["engine"] == "gemini-1.5-flash"
