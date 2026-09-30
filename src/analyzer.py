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
    prov_counts = daily_df['province'].value_counts().head(3)
    prov_summary = ", ".join([f"{p} {c}건" for p, c in prov_counts.items()])

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
            "market_trend": "금일 공식 집계된 아파트 매매 실거래 신고 건수는 0건으로, "
                           "시장 참여자들의 짙은 관망 심리가 반영된 흐름을 보이고 있습니다.",
            "key_complexes": "특이 거래 단지가 집계되지 않았습니다.",
            "analyst_opinion": "부동산 거래 신고 기한(30일)에 따른 시차를 감안할 때, "
                              "향후 순차적인 거래 인입 추이를 지속 모니터링할 필요가 있습니다.",
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

