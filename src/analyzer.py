from __future__ import annotations

from datetime import date, datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

try:
    from src.utils import format_korean_currency
except (ImportError, ModuleNotFoundError):
    try:
        from .utils import format_korean_currency
    except (ImportError, ModuleNotFoundError):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from src.utils import format_korean_currency


def build_analyst_prompt(deal_date: date, daily_df: pd.DataFrame) -> str:
    """당일 실거래 통계 스냅샷을 기반으로 부동산 수석 애널리스트 AI 프롬프트를 생성합니다."""
    date_str = deal_date.isoformat()

    if daily_df.empty:
        return f"""당신은 대한민국 아파트 시장 15년 차 수석 부동산 애널리스트입니다.
기준일자: {date_str}
금일은 전국 아파트 실거래 신고 건수가 0건으로 집계되었습니다.
아래 4가지 항목에 맞추어 마크다운 형식으로 관망세 및 거래 동향 리포트를 작성해 주세요.
1. ### [오늘의 시황 헤드라인]
2. ### [시장 동향 및 거래 활성도]
3. ### [주요 단지 심층 분석]
4. ### [애널리스트 총평 및 시사점]
"""

    total_count = len(daily_df)
    avg_price = daily_df['deal_amount'].mean()
    avg_pyeong = daily_df['price_per_pyeong'].mean()

    # 최고가 TOP 3 단지
    top3_trades = daily_df.sort_values(
        by='deal_amount', ascending=False
    ).head(3)
    top3_summary = []
    for _, r in top3_trades.iterrows():
        top3_summary.append(
            f"- {r.get('province', '')} {r.get('sigungu', '')} {r.get('apt_name', '')} "
            f"({r.get('floor', 1)}층, 전용 {r.get('exclu_use_ar', 0)}㎡): "
            f"{format_korean_currency(r['deal_amount'])}"
        )
    top3_str = "\n".join(top3_summary)

    # 주요 시도별 거래 비중
    if 'province' in daily_df.columns:
        prov_counts = daily_df['province'].value_counts().head(3)
        prov_summary = ", ".join([f"{p} {c}건" for p, c in prov_counts.items()])
    else:
        prov_summary = f"전국 {total_count:,}건"

    prompt = f"""당신은 대한민국 아파트 시장 15년 차 수석 부동산 애널리스트입니다.
제공된 일자별 국토교통부 공공데이터 실거래 통계를 바탕으로 투자자와 실수요자를 위한 깊이 있는 일일 시황 브리핑 리포트를 작성해 주세요.

[기준 일자]
{date_str}

[당일 시장 핵심 통계]
- 총 실거래 신고 건수: {total_count:,}건
- 평균 거래 금액: {format_korean_currency(avg_price)}
- 평균 3.3㎡당 단가: {avg_pyeong:,.0f}만원/평
- 주요 지역 거래량 비중: {prov_summary}

[당일 최고가 주요 거래 단지 TOP 3]
{top3_str}

[작성 지침 및 출력 형식]
반드시 아래 4개의 정확한 마크다운 헤더 형식을 유지하여 전문적이고 객관적인 어조로 작성해 주세요.
인사말이나 사족 없이 즉시 아래 헤더부터 시작하세요.

### [오늘의 시황 헤드라인]
(시장 분위기와 핵심 특징을 관통하는 임팩트 있는 1줄 헤드라인)

### [시장 동향 및 거래 활성도]
(금일 거래량 규모, 전반적인 가격 수준, 활발하게 거래된 지역적 특징 분석)

### [주요 단지 심층 분석]
(최고가 거래 단지의 입지적 가치, 평형대, 층수 특성과 상징성에 대한 상세 분석)

### [애널리스트 총평 및 시사점]
(거시 경제, 금리, 대출 환경과 연계하여 매수자/매도자 관점에서의 시장 시사점 및 조언)
"""
    return prompt.strip()


def generate_local_fallback_summary(deal_date: date, daily_df: pd.DataFrame) -> dict:
    """API 키 미등록 또는 호출 실패 시 정밀 통계 기반 로컬 애널리스트 브리핑을 생성합니다."""
    date_str = deal_date.isoformat()
    now_str = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S KST")

    if daily_df.empty:
        return {
            "deal_date": date_str,
            "created_at": now_str,
            "engine": "local-analyst-fallback",
            "headline": f"{date_str} 당일 실거래 신고 내역 부재 속 관망세 지속",
            "market_trend": (
                "금일 공식 집계된 아파트 매매 실거래 신고 건수는 0건으로, "
                "시장 참여자들의 짙은 관망 심리가 반영된 흐름을 보이고 있습니다."
            ),
            "key_complexes": "특이 거래 단지가 집계되지 않았습니다.",
            "analyst_opinion": (
                "부동산 거래 신고 기한(30일)에 따른 시차를 감안할 때, "
                "향후 순차적인 거래 인입 추이를 지속 모니터링할 필요가 있습니다."
            ),
            "stats_snapshot": {"total_count": 0, "avg_amount": 0, "avg_pyeong_price": 0}
        }

    total_count = len(daily_df)
    avg_price = float(daily_df['deal_amount'].mean())
    avg_pyeong = float(daily_df['price_per_pyeong'].mean())

    max_row = daily_df.loc[daily_df['deal_amount'].idxmax()]
    max_apt = str(max_row['apt_name'])
    max_amt = int(max_row['deal_amount'])
    max_sgg = str(max_row.get('sigungu', ''))
    max_fl = int(max_row.get('floor', 1))

    prov_top = daily_df['province'].value_counts().index[0]
    prov_top_cnt = daily_df['province'].value_counts().iloc[0]

    headline = (
        f"{max_sgg} '{max_apt}' {format_korean_currency(max_amt)} 최고가 주도 속 "
        f"{prov_top} 중심 실거래 지속"
    )

    market_trend = (
        f"금일 전국 아파트 시장에서는 총 {total_count:,}건의 실거래가 신고되었습니다. "
        f"평균 거래 금액은 {format_korean_currency(avg_price)}, "
        f"3.3㎡당 평균 단가는 {avg_pyeong:,.0f}만원으로 집계되었습니다. "
        f"지역별로는 {prov_top}에서만 {prov_top_cnt:,}건이 체결되며 시장 유동성을 견인했습니다."
    )

    key_complexes = (
        f"금일 최고가 거래는 {max_sgg}에 위치한 '{max_apt}'({max_fl}층)로, "
        f"{format_korean_currency(max_amt)}에 매매 체결되며 랜드마크의 견고한 가치를 증명했습니다. "
        f"대출 규제 속에서도 핵심 입지 우량 매물에 대한 매수 수요는 지속되고 있습니다."
    )

    analyst_opinion = (
        "현재 시장은 거시 경제 불확실성과 금리 방향성을 주시하며 지역별·단지별 양극화가 뚜렷합니다. "
        "실수요자 관점에서는 무리한 레버리지보다는 입지 경쟁력이 검증된 핵심지를 중심으로 "
        "선별적 접근을 유지하는 전략이 유효합니다."
    )

    return {
        "deal_date": date_str,
        "created_at": now_str,
        "engine": "local-analyst-fallback",
        "headline": headline,
        "market_trend": market_trend,
        "key_complexes": key_complexes,
        "analyst_opinion": analyst_opinion,
        "stats_snapshot": {
            "total_count": total_count,
            "avg_amount": round(avg_price, 1),
            "avg_pyeong_price": round(avg_pyeong, 1),
            "max_trade": {
                "apt_name": max_apt,
                "deal_amount": max_amt,
                "sigungu": max_sgg,
                "floor": max_fl
            }
        }
    }


def get_cache_path(deal_date: date, cache_dir: Path | str = "data/reports") -> Path:
    """날짜별 리포트 캐시 파일 경로를 안전하게 반환합니다. Path Traversal 공격을 방어합니다."""
    if not isinstance(deal_date, date):
        raise TypeError("deal_date must be an instance of datetime.date")

    dir_path = Path(cache_dir)
    return dir_path / f"{deal_date.isoformat()}.json"


def load_cached_report(deal_date: date, cache_dir: Path | str = "data/reports") -> dict | None:
    """저장된 날짜별 리포트 JSON을 로드합니다. 없으면 None을 반환합니다."""
    file_path = get_cache_path(deal_date, cache_dir)
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_cached_report(deal_date: date, report_data: dict, cache_dir: Path | str = "data/reports") -> Path:
    """날짜별 리포트 JSON을 영속 저장합니다."""
    file_path = get_cache_path(deal_date, cache_dir)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    return file_path


def parse_gemini_response(text: str) -> dict[str, str]:
    """Gemini 마크다운 응답 텍스트를 파싱하여 4개 섹션 딕셔너리로 변환합니다."""
    import re

    patterns = {
        "headline": r"###\s*\[?오늘의\s*시황\s*헤드라인\]?\s*\n(.*?)(?=\n###|\Z)",
        "market_trend": r"###\s*\[?시장\s*동향(?:\s*및\s*거래\s*활성도)?\]?\s*\n(.*?)(?=\n###|\Z)",
        "key_complexes": r"###\s*\[?주요\s*단지\s*심층\s*분석\]?\s*\n(.*?)(?=\n###|\Z)",
        "analyst_opinion": r"###\s*\[?애널리스트\s*총평(?:\s*및\s*시사점)?\]?\s*\n(.*?)(?=\n###|\Z)",
    }

    result = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            # 괄호 안내문 제거 (예: "(시장 분위기와 ...)")
            content = re.sub(r"^\(.*?\)\s*", "", content)
            result[key] = content.strip()
        else:
            result[key] = ""

    # 특정 섹션이 비어있는 경우 유연한 보완
    if not result["headline"]:
        first_line = text.strip().split("\n")[0]
        result["headline"] = first_line.replace("#", "").strip() or "금일 아파트 실거래 시황 요약"
    if not result["market_trend"]:
        result["market_trend"] = "당일 거래량 및 시장 지표에 따른 동향이 집계되었습니다."
    if not result["key_complexes"]:
        result["key_complexes"] = "금일 신고된 주요 아파트 거래 내역을 분석 중입니다."
    if not result["analyst_opinion"]:
        result["analyst_opinion"] = "시장 추세를 주시하며 선별적인 투자 및 매수 전략이 권장됩니다."

    return result


def call_gemini_api(
    prompt: str,
    api_key: str,
    model: str = "gemini-1.5-flash",
    timeout: int = 15
) -> str:
    """Google AI Studio v1beta REST API를 직접 호출하여 Gemini 분석 결과를 가져옵니다."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1024,
        }
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()

    data = resp.json()
    try:
        candidate_text = data["candidates"][0]["content"]["parts"][0]["text"]
        return candidate_text
    except (KeyError, IndexError) as err:
        raise ValueError(f"Unexpected response structure from Gemini API: {data}") from err


def get_or_create_daily_report(
    deal_date: date,
    daily_df: pd.DataFrame,
    api_key: str | None = None,
    cache_dir: Path | str = "data/reports",
    force_refresh: bool = False,
    model: str = "gemini-1.5-flash"
) -> dict:
    """일자별 리포트를 캐시에서 먼저 로드하고, 없을 경우에만 Gemini API(또는 로컬 폴백)로 생성 및 캐시합니다."""
    # 1. 캐시가 이미 존재하고 강제 갱신이 아닌 경우 즉시 반환 (Zero Cost, Zero Latency)
    if not force_refresh:
        cached = load_cached_report(deal_date, cache_dir)
        if cached is not None:
            return cached

    # 2. API Key 확인 (인자 -> 환경변수)
    effective_api_key = api_key or os.getenv("GEMINI_API_KEY")

    now_str = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S KST")

    # API 키가 없으면 로컬 스마트 폴백 생성 후 캐시
    if not effective_api_key or not effective_api_key.strip():
        report = generate_local_fallback_summary(deal_date, daily_df)
        save_cached_report(deal_date, report, cache_dir)
        return report

    # 3. Gemini API 호출 시도
    prompt = build_analyst_prompt(deal_date, daily_df)
    try:
        raw_text = call_gemini_api(prompt, effective_api_key, model=model)
        parsed = parse_gemini_response(raw_text)
        report = {
            "deal_date": deal_date.isoformat(),
            "created_at": now_str,
            "engine": model,
            "headline": parsed["headline"],
            "market_trend": parsed["market_trend"],
            "key_complexes": parsed["key_complexes"],
            "analyst_opinion": parsed["analyst_opinion"],
        }
    except Exception as e:
        # API 오류(할당량 초과, 네트워크 단절 등) 시 안전하게 스마트 로컬 폴백 생성
        report = generate_local_fallback_summary(deal_date, daily_df)
        report["fallback_reason"] = f"Gemini API 호출 실패 ({e.__class__.__name__}): {str(e)}"

    # 4. 결과 캐시 저장
    save_cached_report(deal_date, report, cache_dir)
    return report
