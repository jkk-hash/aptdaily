from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.utils import format_korean_currency

DATA_PATH = Path("data/latest_7days.parquet")
META_PATH = Path("data/metadata.json")

# ==========================================
# 1. 비즈니스 로직 및 데이터 필터링 함수 (테스트 보장)
# ==========================================


def filter_data(
    df: pd.DataFrame,
    selected_provinces: list[str] | None = None,
    selected_sigungus: list[str] | None = None,
    apt_search: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    min_area: float | None = None,
    max_area: float | None = None,
    min_floor: int | None = None,
    max_floor: int | None = None,
    selected_dates: list | None = None
) -> pd.DataFrame:
    """사용자가 선택한 다양한 조건에 맞춰 DataFrame을 필터링합니다."""
    if df.empty:
        return df

    filtered = df.copy()

    if selected_provinces:
        filtered = filtered[filtered['province'].isin(selected_provinces)]

    if selected_sigungus:
        filtered = filtered[filtered['sigungu'].isin(selected_sigungus)]

    if apt_search and apt_search.strip():
        search_term = apt_search.strip().lower()
        match_mask = filtered['apt_name'].str.lower().str.contains(
            search_term, na=False
        )
        filtered = filtered[match_mask]

    if min_price is not None:
        filtered = filtered[filtered['deal_amount'] >= min_price]
    if max_price is not None:
        filtered = filtered[filtered['deal_amount'] <= max_price]

    if min_area is not None:
        filtered = filtered[filtered['exclu_use_ar'] >= min_area]
    if max_area is not None:
        filtered = filtered[filtered['exclu_use_ar'] <= max_area]

    if min_floor is not None:
        filtered = filtered[filtered['floor'] >= min_floor]
    if max_floor is not None:
        filtered = filtered[filtered['floor'] <= max_floor]

    if selected_dates:
        filtered = filtered[filtered['deal_date'].isin(selected_dates)]

    return filtered


def calculate_kpis(df: pd.DataFrame) -> dict:
    """대시보드 상단에 표시할 4대 핵심 지표(KPI)를 계산합니다."""
    if df.empty:
        return {
            'total_count': 0,
            'avg_amount': 0,
            'avg_pyeong_price': 0,
            'max_trade': None
        }

    total_count = len(df)
    avg_amount = df['deal_amount'].mean()
    avg_pyeong_price = df['price_per_pyeong'].mean()

    max_row = df.loc[df['deal_amount'].idxmax()]
    max_trade = {
        'apt_name': max_row['apt_name'],
        'deal_amount': int(max_row['deal_amount']),
        'province': max_row.get('province', ''),
        'sigungu': max_row.get('sigungu', ''),
        'floor': int(max_row.get('floor', 1)),
        'exclu_use_ar': float(max_row.get('exclu_use_ar', 0))
    }

    return {
        'total_count': total_count,
        'avg_amount': avg_amount,
        'avg_pyeong_price': avg_pyeong_price,
        'max_trade': max_trade
    }


def get_daily_trend(df: pd.DataFrame) -> pd.DataFrame:
    """일자별 거래량 및 평균 거래금액을 집계합니다."""
    if df.empty:
        return pd.DataFrame(columns=['deal_date', 'deal_count', 'avg_amount'])

    daily = df.groupby('deal_date').agg(
        deal_count=('deal_amount', 'count'),
        avg_amount=('deal_amount', 'mean'),
        avg_pyeong_price=('price_per_pyeong', 'mean')
    ).reset_index().sort_values('deal_date')

    daily['avg_amount'] = daily['avg_amount'].round(0)
    daily['avg_pyeong_price'] = daily['avg_pyeong_price'].round(1)
    return daily

# ==========================================
# 2. Streamlit 대시보드 UI 구현 (프리미엄 핀테크 디자인)
# ==========================================


@st.cache_data(ttl=1800)
def load_data():
    """Parquet 파일과 메타데이터를 로드합니다."""
    if not DATA_PATH.exists():
        return pd.DataFrame(), {}

    df = pd.read_parquet(DATA_PATH)
    metadata = {}
    if META_PATH.exists():
        with open(META_PATH, "r", encoding="utf-8") as f:
            metadata = json.load(f)

    if 'deal_date' in df.columns:
        df['deal_date'] = pd.to_datetime(df['deal_date']).dt.date

    return df, metadata


def inject_custom_css():
    """프리미엄 핀테크/프롭테크 글래스모피즘 스타일 CSS를 주입합니다."""
    st.markdown("""
        <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

        * {
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
        }

        /* 메인 컨테이너 패딩 */
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }

        /* 프리미엄 헤더 배너 */
        .header-box {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border-radius: 18px;
            padding: 24px 30px;
            color: #ffffff;
            margin-bottom: 24px;
            box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.08);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        .header-title-box h1 {
            font-size: 1.85rem !important;
            font-weight: 800 !important;
            margin: 0 !important;
            color: #ffffff !important;
            letter-spacing: -0.5px;
        }
        .header-title-box p {
            margin: 6px 0 0 0;
            color: #94a3b8;
            font-size: 0.92rem;
        }
        .header-badges {
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }
        .sync-badge {
            background: rgba(255, 255, 255, 0.12);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            padding: 6px 14px;
            border-radius: 30px;
            font-size: 0.82rem;
            color: #e2e8f0;
            font-weight: 500;
        }
        .live-dot {
            height: 8px;
            width: 8px;
            background-color: #10b981;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
            box-shadow: 0 0 8px #10b981;
        }

        /* 모던 KPI 카드 디자인 */
        .kpi-container {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 18px;
            margin-bottom: 24px;
        }
        @media (max-width: 900px) {
            .kpi-container { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 500px) {
            .kpi-container { grid-template-columns: 1fr; }
        }

        .kpi-card {
            background: #ffffff;
            border-radius: 16px;
            padding: 20px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.03);
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            position: relative;
            overflow: hidden;
        }
        .kpi-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 20px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.02);
            border-color: #cbd5e1;
        }
        .kpi-card-1 { border-top: 4px solid #3b82f6; }
        .kpi-card-2 { border-top: 4px solid #8b5cf6; }
        .kpi-card-3 { border-top: 4px solid #10b981; }
        .kpi-card-4 { border-top: 4px solid #f59e0b; }

        .kpi-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .kpi-label {
            font-size: 0.85rem;
            color: #64748b;
            font-weight: 600;
            letter-spacing: -0.2px;
        }
        .kpi-icon {
            font-size: 1.25rem;
            padding: 6px;
            border-radius: 10px;
            background: #f8fafc;
        }
        .kpi-num {
            font-size: 1.7rem;
            font-weight: 800;
            color: #0f172a;
            line-height: 1.2;
            letter-spacing: -0.5px;
        }
        .kpi-sub {
            font-size: 0.8rem;
            color: #94a3b8;
            margin-top: 6px;
            font-weight: 500;
        }

        /* 탭 스타일링 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 4px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px 10px 0 0;
            padding: 10px 18px;
            font-weight: 700;
            font-size: 0.95rem;
            color: #64748b;
            border: none;
            background: transparent;
        }
        .stTabs [aria-selected="true"] {
            color: #2563eb !important;
            border-bottom: 3px solid #2563eb !important;
            background: rgba(37, 99, 235, 0.04) !important;
        }

        /* 섹션 카드 컨테이너 */
        .chart-card {
            background: #ffffff;
            border-radius: 16px;
            padding: 22px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.04);
            margin-bottom: 20px;
        }
        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .chart-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: #1e293b;
            margin: 0;
        }
        .chart-desc {
            font-size: 0.82rem;
            color: #64748b;
            margin-top: 2px;
        }
        </style>
    """, unsafe_allow_html=True)


def build_daily_trend_chart(daily_trend: pd.DataFrame) -> go.Figure:
    """일자별 거래량 및 평균 거래금액 추이를 나타내는 프리미엄 듀얼 축 차트를 생성합니다."""
    fig = go.Figure()

    # 1. 일자별 거래량 (부드러운 라운드 코발트 막대)
    fig.add_trace(go.Bar(
        x=daily_trend['deal_date'].astype(str),
        y=daily_trend['deal_count'],
        name="거래량 (건)",
        marker=dict(
            color="#3B82F6",
            line=dict(color="#2563EB", width=1),
            opacity=0.85
        ),
        hovertemplate="<b>%{x}</b><br>실거래 신고 건수: <b>%{y:,}건</b><extra></extra>",
        yaxis="y"
    ))

    # 2. 일자별 평균 거래금액 (생동감 넘치는 코랄 로즈 곡선 스플라인)
    fig.add_trace(go.Scatter(
        x=daily_trend['deal_date'].astype(str),
        y=daily_trend['avg_amount'] / 10000,
        name="평균 거래가 (억원)",
        line=dict(color="#F43F5E", width=3.5, shape="spline"),
        marker=dict(
            size=9,
            color="#F43F5E",
            line=dict(color="#FFFFFF", width=2.5),
            symbol="circle"
        ),
        mode="lines+markers",
        hovertemplate="<b>%{x}</b><br>평균 실거래가: <b>%{y:.2f}억원</b><extra></extra>",
        yaxis="y2"
    ))

    # 레이아웃 고도화 (클린 핀테크 테마)
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=30, b=20),
        height=450,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0.7)",
            bordercolor="rgba(226,232,240,0.8)",
            borderwidth=1,
            font=dict(size=12, family="Pretendard")
        ),
        xaxis=dict(
            title="",
            tickfont=dict(size=12, color="#475569", family="Pretendard"),
            showgrid=False,
            linecolor="#cbd5e1"
        ),
        yaxis=dict(
            title=dict(text="거래량 (건)", font=dict(color="#2563EB", size=13)),
            tickfont=dict(color="#2563EB", size=11),
            showgrid=True,
            gridcolor="rgba(226, 232, 240, 0.6)",
            gridwidth=1
        ),
        yaxis2=dict(
            title=dict(text="평균 거래가 (억원)", font=dict(color="#E11D48", size=13)),
            tickfont=dict(color="#E11D48", size=11),
            overlaying="y",
            side="right",
            showgrid=False
        )
    )

    return fig


def build_province_price_chart(df: pd.DataFrame) -> go.Figure:
    """주요 시·도별 평균 평당단가 랭킹 수평 바 차트를 생성합니다."""
    prov_summary = df.groupby('province').agg(
        avg_pyeong=('price_per_pyeong', 'mean'),
        deal_count=('deal_amount', 'count')
    ).reset_index().sort_values('avg_pyeong', ascending=True)

    fig = go.Figure(go.Bar(
        x=prov_summary['avg_pyeong'],
        y=prov_summary['province'],
        orientation='h',
        marker=dict(
            color=prov_summary['avg_pyeong'],
            colorscale=[
                [0.0, "#93C5FD"],
                [0.5, "#6366F1"],
                [1.0, "#4338CA"]
            ],
            line=dict(color="#ffffff", width=1)
        ),
        text=prov_summary.apply(
            lambda r: f"{r['avg_pyeong']:,.0f}만 ({r['deal_count']}건)", axis=1
        ),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>평균 평당단가: <b>%{x:,.0f}만원/평</b><extra></extra>"
    ))

    fig.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=50, t=10, b=10),
        height=380,
        xaxis=dict(
            title="3.3㎡당 단가 (만원/평)",
            showgrid=True,
            gridcolor="rgba(226, 232, 240, 0.6)"
        ),
        yaxis=dict(
            title="",
            tickfont=dict(size=12, family="Pretendard", color="#1e293b")
        )
    )
    return fig


def build_area_price_scatter(df: pd.DataFrame) -> go.Figure:
    """전용면적 대비 실거래가 분포 인터랙티브 산점도 차트를 생성합니다."""
    plot_df = df.copy()
    plot_df['deal_amount_eok'] = (plot_df['deal_amount'] / 10000).round(2)

    fig = px.scatter(
        plot_df,
        x="exclu_use_ar",
        y="deal_amount_eok",
        color="province",
        color_discrete_sequence=px.colors.qualitative.Prism,
        opacity=0.75,
        hover_data={
            "apt_name": True,
            "sigungu": True,
            "floor": True,
            "pyeong": ":.1f",
            "deal_amount_eok": ":.2f",
            "exclu_use_ar": False,
            "province": False
        },
        labels={
            "exclu_use_ar": "전용면적 (㎡)",
            "deal_amount_eok": "거래금액 (억원)",
            "province": "지역"
        }
    )

    fig.update_traces(
        marker=dict(size=8, line=dict(width=0.5, color="white")),
        hovertemplate=(
            "<b>%{customdata[0]}</b> (%{customdata[1]}, %{customdata[2]}층)<br>"
            "전용면적: %{x:.1f}㎡ (%{customdata[3]}평)<br>"
            "실거래가: <b>%{y:.2f}억원</b><extra></extra>"
        )
    )

    fig.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=10, t=10, b=10),
        height=380,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=11)
        ),
        xaxis=dict(
            title="전용면적 (㎡)",
            showgrid=True,
            gridcolor="rgba(226, 232, 240, 0.6)"
        ),
        yaxis=dict(
            title="실거래가 (억원)",
            showgrid=True,
            gridcolor="rgba(226, 232, 240, 0.6)"
        )
    )
    return fig


def build_top10_chart(df: pd.DataFrame) -> go.Figure:
    """최근 7일 전국 최고가 실거래 단지 TOP 10 수평 랭킹 차트를 생성합니다."""
    top10 = df.sort_values(by="deal_amount", ascending=False).head(10).copy()
    top10 = top10.sort_values(by="deal_amount", ascending=True)

    labels = top10.apply(
        lambda r: f"{r['apt_name']} ({r['sigungu']}, {r['floor']}층)", axis=1
    )

    fig = go.Figure(go.Bar(
        x=top10['deal_amount'] / 10000,
        y=labels,
        orientation='h',
        marker=dict(
            color=top10['deal_amount'],
            colorscale=[
                [0.0, "#F59E0B"],
                [0.5, "#EF4444"],
                [1.0, "#881337"]
            ],
            line=dict(color="#ffffff", width=1)
        ),
        text=top10['deal_amount'].apply(format_korean_currency),
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(color="#ffffff", size=11, family="Pretendard"),
        hovertemplate="<b>%{y}</b><br>거래금액: <b>%{x:.2f}억원</b><extra></extra>"
    ))

    fig.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=30, t=10, b=10),
        height=420,
        xaxis=dict(
            title="실거래 금액 (억원)",
            showgrid=True,
            gridcolor="rgba(226, 232, 240, 0.6)"
        ),
        yaxis=dict(
            title="",
            tickfont=dict(size=12, family="Pretendard", color="#1e293b")
        )
    )
    return fig


def main():
    st.set_page_config(
        page_title="전국 아파트 실거래가 대시보드 (최근 7일)",
        page_icon="🏢",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    inject_custom_css()

    df_raw, metadata = load_data()

    if df_raw.empty:
        st.warning(
            "⚠️ 아직 수집된 데이터가 없습니다. 먼저 `src/collector.py`를 실행해 주세요."
        )
        st.stop()

    # ==========================================
    # 3. 사이드바 필터 디자인
    # ==========================================
    st.sidebar.markdown("""
        <div style='margin-bottom: 14px;'>
            <h3 style='margin:0; font-size:1.15rem; font-weight:800; color:#1e293b;'>
                🔍 스마트 필터링
            </h3>
            <p style='margin:4px 0 0 0; font-size:0.8rem; color:#64748b;'>
                원하시는 조건을 자유롭게 설정하세요.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # 1. 시·도 선택
    all_provinces = sorted(df_raw['province'].dropna().unique().tolist())
    selected_provinces = st.sidebar.multiselect(
        "📍 시·도 선택 (기본: 전국 전체)",
        options=all_provinces,
        default=[]
    )

    # 2. 시·군·구 선택 (선택된 시도에 따라 동적 연동)
    if selected_provinces:
        matched_sgg = df_raw[df_raw['province'].isin(selected_provinces)]
        available_sigungus = sorted(
            matched_sgg['sigungu'].dropna().unique().tolist()
        )
    else:
        available_sigungus = sorted(
            df_raw['sigungu'].dropna().unique().tolist()
        )

    selected_sigungus = st.sidebar.multiselect(
        "🏙️ 시·군·구 상세 선택",
        options=available_sigungus,
        default=[]
    )

    # 3. 아파트 단지명 검색
    apt_search = st.sidebar.text_input(
        "🔎 아파트 단지명 검색",
        placeholder="예: 래미안, 자이, 아크로, 힐스테이트"
    )

    st.sidebar.markdown(
        "<hr style='margin:16px 0; border-color:#e2e8f0;'/>",
        unsafe_allow_html=True
    )

    # 4. 거래금액 범위 슬라이더 (만원 단위)
    deal_amounts = [int(v) for v in df_raw['deal_amount'].dropna().tolist()]
    min_amount_raw = min(deal_amounts) if deal_amounts else 0
    max_amount_raw = max(deal_amounts) if deal_amounts else 1000000

    price_range = st.sidebar.slider(
        "💰 거래금액 범위 (만원)",
        min_value=min_amount_raw,
        max_value=max_amount_raw,
        value=(min_amount_raw, max_amount_raw),
        step=5000,
        format="%d만원"
    )

    # 5. 전용면적 범위 슬라이더 (㎡)
    areas = [float(v) for v in df_raw['exclu_use_ar'].dropna().tolist()]
    min_ar_raw = min(areas) if areas else 10.0
    max_ar_raw = max(areas) if areas else 300.0

    area_range = st.sidebar.slider(
        "📐 전용면적 범위 (㎡)",
        min_value=round(min_ar_raw, 1),
        max_value=round(max_ar_raw, 1),
        value=(round(min_ar_raw, 1), round(max_ar_raw, 1)),
        step=10.0
    )

    # 6. 층수 필터
    floors = [int(v) for v in df_raw['floor'].dropna().tolist()]
    min_floor_raw = min(floors) if floors else 1
    max_floor_raw = max(floors) if floors else 50
    floor_range = st.sidebar.slider(
        "🏢 층수 범위",
        min_value=min_floor_raw,
        max_value=max_floor_raw,
        value=(min_floor_raw, max_floor_raw)
    )

    # 필터 적용
    df_filtered = filter_data(
        df_raw,
        selected_provinces=selected_provinces,
        selected_sigungus=selected_sigungus,
        apt_search=apt_search,
        min_price=price_range[0],
        max_price=price_range[1],
        min_area=area_range[0],
        max_area=area_range[1],
        min_floor=floor_range[0],
        max_floor=floor_range[1]
    )

    # ==========================================
    # 4. 상단 모던 배너 및 지표 카드 영역
    # ==========================================
    last_up = metadata.get("last_updated", "최근 갱신")
    date_r = metadata.get("date_range", ["-", "-"])

    st.markdown(f"""
        <div class="header-box">
            <div class="header-title-box">
                <h1>🏢 전국 아파트 실거래가 모니터링</h1>
                <p>국토교통부 실거래가 공개시스템 연계 OpenAPI 기반 실시간 거래 분석 플랫폼</p>
            </div>
            <div class="header-badges">
                <div class="sync-badge">
                    <span class="live-dot"></span>수집 대상: <b>{date_r[0]} ~ {date_r[1]}</b>
                </div>
                <div class="sync-badge">
                    ⏱️ 최종 동기화: <b>{last_up}</b>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 핵심 KPI 카드 영역
    kpis = calculate_kpis(df_filtered)
    avg_formatted = format_korean_currency(kpis['avg_amount'])
    max_t = kpis['max_trade']
    if max_t:
        max_amt_fmt = format_korean_currency(max_t['deal_amount'])
        max_name_fmt = max_t['apt_name']
        max_sub_fmt = f"{max_t['sigungu']} {max_t['floor']}층 ({max_amt_fmt})"
    else:
        max_name_fmt = "-"
        max_sub_fmt = "거래 없음"

    card_4_num_style = (
        "font-size: 1.25rem; white-space: nowrap; "
        "overflow: hidden; text-overflow: ellipsis;"
    )

    st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card kpi-card-1">
                <div class="kpi-header">
                    <span class="kpi-label">총 실거래 건수</span>
                    <span class="kpi-icon">📊</span>
                </div>
                <div class="kpi-num">{kpis['total_count']:,}건</div>
                <div class="kpi-sub">전체 {len(df_raw):,}건 중 조건 만족</div>
            </div>
            <div class="kpi-card kpi-card-2">
                <div class="kpi-header">
                    <span class="kpi-label">평균 실거래 금액</span>
                    <span class="kpi-icon">💰</span>
                </div>
                <div class="kpi-num">{avg_formatted}</div>
                <div class="kpi-sub">선택된 단지 평균 기준</div>
            </div>
            <div class="kpi-card kpi-card-3">
                <div class="kpi-header">
                    <span class="kpi-label">평균 3.3㎡당 단가</span>
                    <span class="kpi-icon">📐</span>
                </div>
                <div class="kpi-num">{kpis['avg_pyeong_price']:,.0f}만원</div>
                <div class="kpi-sub">평당 가격 (단위: 만원/평)</div>
            </div>
            <div class="kpi-card kpi-card-4">
                <div class="kpi-header">
                    <span class="kpi-label">최고가 거래 단지</span>
                    <span class="kpi-icon">👑</span>
                </div>
                <div class="kpi-num" style="{card_4_num_style}" title="{max_name_fmt}">
                    {max_name_fmt}
                </div>
                <div class="kpi-sub">{max_sub_fmt}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if df_filtered.empty:
        st.info("💡 선택하신 조건에 일치하는 실거래 데이터가 없습니다. 사이드바 필터를 변경해 주세요.")
        st.stop()

    # ==========================================
    # 5. 인터랙티브 데이터 분석 탭 영역
    # ==========================================
    tab1, tab2, tab3 = st.tabs([
        "📈 일자별 거래량 및 평균가 추이",
        "📊 평당 단가 및 가격대 다차원 분석",
        "👑 최고가 거래 단지 TOP 10"
    ])

    with tab1:
        st.markdown("""
            <div class="chart-card">
                <div class="chart-header">
                    <div>
                        <h3 class="chart-title">일자별 실거래량 및 평균 거래금액 추이</h3>
                        <p class="chart-desc">
                            계약 체결일자별 총 거래 건수(막대)와 평균 거래가(선)의 복합 변동 흐름을 한눈에 파악합니다.
                        </p>
                    </div>
                </div>
        """, unsafe_allow_html=True)

        daily_trend = get_daily_trend(df_filtered)
        if not daily_trend.empty:
            fig_trend = build_daily_trend_chart(daily_trend)
            st.plotly_chart(fig_trend, use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("""
                <div class="chart-card">
                    <div class="chart-header">
                        <div>
                            <h3 class="chart-title">주요 시·도별 평균 평당단가 랭킹</h3>
                            <p class="chart-desc">지역별 3.3㎡당 평균 가격 수준을 비교합니다.</p>
                        </div>
                    </div>
            """, unsafe_allow_html=True)
            fig_prov = build_province_price_chart(df_filtered)
            st.plotly_chart(fig_prov, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_c2:
            st.markdown("""
                <div class="chart-card">
                    <div class="chart-header">
                        <div>
                            <h3 class="chart-title">전용면적(㎡) 대비 거래금액 분포</h3>
                            <p class="chart-desc">아파트 면적과 실거래 금액 간의 상관관계를 탐색합니다.</p>
                        </div>
                    </div>
            """, unsafe_allow_html=True)
            fig_scatter = build_area_price_scatter(df_filtered)
            st.plotly_chart(fig_scatter, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with tab3:
        st.markdown("""
            <div class="chart-card">
                <div class="chart-header">
                    <div>
                        <h3 class="chart-title">전국 최고가 실거래 아파트 TOP 10 랭킹</h3>
                        <p class="chart-desc">선택된 조건 내에서 가장 높은 금액에 거래된 아파트 단지 상위 10건입니다.</p>
                    </div>
                </div>
        """, unsafe_allow_html=True)
        fig_top10 = build_top10_chart(df_filtered)
        st.plotly_chart(fig_top10, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================
    # 6. 상세 거래 내역 테이블 (계약일자 최신순 정렬)
    # ==========================================
    st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
    c_tbl_header1, c_tbl_header2 = st.columns([3, 1])
    with c_tbl_header1:
        st.subheader(f"📋 실시간 상세 거래 내역 (총 {len(df_filtered):,}건)")
        st.caption("📅 계약일자가 가장 최근인 거래부터 역순으로 자동 정렬됩니다.")
    with c_tbl_header2:
        df_sorted = df_filtered.sort_values(
            by=['deal_date', 'deal_amount'], ascending=[False, False]
        ).reset_index(drop=True)
        csv_bytes = df_sorted.to_csv(
            index=False, encoding="utf-8-sig"
        ).encode("utf-8-sig")
        today_str = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d")
        st.download_button(
            label="📥 데이터 다운로드 (CSV)",
            data=csv_bytes,
            file_name=f"apartment_trades_{today_str}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # 표시용 데이터프레임 가공
    display_df = df_sorted.copy()
    display_df['거래금액'] = display_df['deal_amount'].apply(
        format_korean_currency
    )
    display_df['평당단가'] = display_df['price_per_pyeong'].apply(
        lambda x: f"{x:,.0f}만원"
    )
    display_df['전용면적(㎡)'] = display_df['exclu_use_ar'].apply(
        lambda x: f"{x:.1f}㎡"
    )
    display_df['평수'] = display_df['pyeong'].apply(lambda x: f"{x:.1f}평")
    display_df['층'] = display_df['floor'].apply(lambda x: f"{x}층")
    display_df['건축년도'] = display_df['build_year'].astype(str) + "년"

    cols_to_show = [
        'deal_date', 'province', 'sigungu', 'bjdong', 'apt_name',
        '거래금액', '평당단가', '전용면적(㎡)', '평수', '층', '건축년도'
    ]
    rename_cols = {
        'deal_date': '계약일자',
        'province': '시·도',
        'sigungu': '시·군·구',
        'bjdong': '법정동',
        'apt_name': '단지명'
    }
    display_df = pd.DataFrame(display_df[cols_to_show])
    display_df.columns = [
        rename_cols.get(col, col) for col in display_df.columns
    ]

    st.dataframe(
        display_df,
        use_container_width=True,
        height=400,
        column_config={
            "계약일자": st.column_config.DateColumn("계약일자", format="YYYY-MM-DD"),
            "거래금액": st.column_config.TextColumn("거래금액"),
            "평당단가": st.column_config.TextColumn("평당단가"),
            "전용면적(㎡)": st.column_config.TextColumn("전용면적"),
            "단지명": st.column_config.TextColumn("단지명", width="medium")
        }
    )


if __name__ == "__main__":
    main()
