from datetime import date, datetime, timedelta
import json
from pathlib import Path
from zoneinfo import ZoneInfo


def get_recent_7days_range(
    reference_date: date | None = None,
    include_today: bool = True
) -> tuple[date, date]:
    """기준일(기본: KST 오늘) 기준 최근 7일 날짜 범위를 반환합니다.

    include_today가 True인 경우: 오늘(T)을 포함한 최근 7일 (T-6 ~ T)
    include_today가 False인 경우: 전일(T-1) 기준 최근 7일 (T-7 ~ T-1)
    """
    if reference_date is None:
        reference_date = datetime.now(ZoneInfo("Asia/Seoul")).date()
    if include_today:
        end_date = reference_date
        start_date = reference_date - timedelta(days=6)
    else:
        end_date = reference_date - timedelta(days=1)
        start_date = reference_date - timedelta(days=7)
    return start_date, end_date


def get_target_ymd_list(start_date: date, end_date: date) -> list[str]:
    """시작일부터 종료일까지 포함되는 YYYYMM 문자열 리스트(정렬됨)를 반환합니다."""
    months = set()
    curr = start_date
    while curr <= end_date:
        months.add(curr.strftime("%Y%m"))
        # 다음달 첫날로 이동
        if curr.month == 12:
            curr = date(curr.year + 1, 1, 1)
        else:
            curr = date(curr.year, curr.month + 1, 1)
    return sorted(list(months))


def format_korean_currency(amount_manwon: int | float | None) -> str:
    """만원 단위 숫자를 한국식 금액(X억 Y,YYY만원) 문자열로 포맷팅합니다."""
    if amount_manwon is None or amount_manwon == 0:
        return "0원"
    amount = int(round(amount_manwon))
    eok = amount // 10000
    man = amount % 10000

    parts = []
    if eok > 0:
        parts.append(f"{eok:,}억원" if man == 0 else f"{eok:,}억")
    if man > 0:
        parts.append(f"{man:,}만원")

    return " ".join(parts) if parts else "0원"


def load_lawd_codes(filepath: str | Path = "data/lawd_cd.json") -> dict[str, dict[str, str]]:
    """전국 시군구 법정동 코드 매핑 파일을 로드합니다."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Lawd code file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
