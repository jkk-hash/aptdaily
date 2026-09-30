import argparse
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import random
import time
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
import pandas as pd
import requests

try:
    from src.utils import get_recent_7days_range, get_target_ymd_list, load_lawd_codes
except (ImportError, ModuleNotFoundError):
    try:
        from .utils import get_recent_7days_range, get_target_ymd_list, load_lawd_codes
    except (ImportError, ModuleNotFoundError):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from src.utils import get_recent_7days_range, get_target_ymd_list, load_lawd_codes

load_dotenv()

# 국토교통부 아파트매매 실거래자료 OpenAPI 엔드포인트
API_ENDPOINT = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"


def parse_xml_items(xml_content: str | bytes) -> list[dict]:
    """공공데이터 API의 XML 응답을 파싱하여 아이템 리스트로 반환합니다."""
    items = []
    if not xml_content:
        return items

    if isinstance(xml_content, str) and not xml_content.strip():
        return items

    try:
        if isinstance(xml_content, str):
            root = ET.fromstring(xml_content.strip())
        else:
            root = ET.fromstring(xml_content)
    except ET.ParseError:
        return items

    body = root.find("body")
    if body is None:
        return items

    items_tag = body.find("items")
    if items_tag is None:
        return items

    for item in items_tag.findall("item"):
        record = {}
        for child in item:
            record[child.tag] = child.text.strip() if child.text else ""
        items.append(record)

    return items


def fetch_deals_by_lawd(service_key: str, lawd_cd: str, deal_ymd: str, max_retries: int = 2) -> list[dict]:
    """특정 시군구 코드와 계약월에 대해 OpenAPI를 호출합니다."""
    params = {
        "serviceKey": service_key,
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": deal_ymd,
        "numOfRows": 1000,
        "pageNo": 1
    }

    for _ in range(max_retries):
        try:
            resp = requests.get(API_ENDPOINT, params=params, timeout=10)
            if resp.status_code == 200:
                resp.encoding = "utf-8"
                items = parse_xml_items(resp.content)
                return items
        except Exception:
            time.sleep(0.5)

    return []


def clean_and_filter_deals(df: pd.DataFrame, start_date: date, end_date: date) -> pd.DataFrame:
    """원시 거래 데이터프레임을 표준화하고 최근 7일 기준으로 필터링 및 중복을 제거합니다."""
    if df.empty:
        return pd.DataFrame(columns=[
            'deal_date', 'province', 'sigungu', 'sigungu_cd', 'bjdong', 'apt_name',
            'deal_amount', 'exclu_use_ar', 'pyeong', 'price_per_pyeong', 'floor', 'build_year'
        ])

    df = df.copy()

    # 구/신 API 태그명 통합 매핑
    # 아파트명: aptNm (신) 또는 aptName (구)
    if 'aptNm' in df.columns and 'aptName' not in df.columns:
        df['apt_name'] = df['aptNm']
    elif 'aptName' in df.columns:
        df['apt_name'] = df['aptName']
    elif 'apt_name' not in df.columns:
        df['apt_name'] = ""

    # 법정동: umdNm (신) 또는 dong (구)
    if 'umdNm' in df.columns and 'dong' not in df.columns:
        df['bjdong'] = df['umdNm']
    elif 'dong' in df.columns:
        df['bjdong'] = df['dong']
    elif 'bjdong' not in df.columns:
        df['bjdong'] = ""

    # 컬럼 매핑 표준화
    col_map = {
        'dealAmount': 'deal_amount',
        'excluUseAr': 'exclu_use_ar',
        'sggCd': 'sigungu_cd',
        'floor': 'floor',
        'buildYear': 'build_year',
        'dealYear': 'deal_year',
        'dealMonth': 'deal_month',
        'dealDay': 'deal_day'
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # 해제(취소)된 거래 제외 (cdealType이 'O'이거나 해제일자가 존재하는 거래)
    if 'cdealType' in df.columns:
        df = df[df['cdealType'].astype(str).str.strip() != 'O']
    if 'cdealDay' in df.columns:
        df = df[df['cdealDay'].astype(str).str.strip() == '']

    # 필수 컬럼 존재 확인
    req_cols = ['deal_year', 'deal_month', 'deal_day', 'deal_amount', 'exclu_use_ar']
    for rc in req_cols:
        if rc not in df.columns:
            return pd.DataFrame()

    # 날짜 파싱 및 deal_date 생성
    try:
        df['deal_date'] = df.apply(
            lambda r: date(int(r['deal_year']), int(r['deal_month']), int(r['deal_day'])),
            axis=1
        )
    except Exception:
        return pd.DataFrame()

    # 최근 7일 날짜 필터링
    df = df[(df['deal_date'] >= start_date) & (df['deal_date'] <= end_date)]
    if df.empty:
        return pd.DataFrame()

    # 거래금액 정수화 (단위: 만원)
    df['deal_amount'] = (
        df['deal_amount']
        .astype(str)
        .str.replace(',', '', regex=False)
        .str.strip()
        .astype(int)
    )

    # 전용면적 실수화 (㎡) 및 평수/평당단가 계산
    df['exclu_use_ar'] = df['exclu_use_ar'].astype(float)
    df['pyeong'] = (df['exclu_use_ar'] / 3.305785).round(1)
    df['price_per_pyeong'] = (df['deal_amount'] / (df['exclu_use_ar'] / 3.305785)).round(1)

    # 층수 정수화
    if 'floor' in df.columns:
        df['floor'] = pd.to_numeric(df['floor'], errors='coerce').fillna(1).astype(int)
    if 'build_year' in df.columns:
        df['build_year'] = pd.to_numeric(df['build_year'], errors='coerce').fillna(2000).astype(int)

    # 중복 제거
    dedup_cols = ['sigungu_cd', 'bjdong', 'apt_name', 'deal_date', 'deal_amount', 'exclu_use_ar', 'floor']
    avail_dedup = [c for c in dedup_cols if c in df.columns]
    if avail_dedup:
        df = df.drop_duplicates(subset=avail_dedup)

    return df.reset_index(drop=True)


def generate_mock_data(start_date: date, end_date: date) -> pd.DataFrame:
    """테스트 및 API 키 미설정 시 사용할 현실적인 전국 7일치 실거래 Mock 데이터셋을 생성합니다."""
    sample_apts = [
        ('서울특별시', '강남구', '11680', '개포동', '디에이치퍼스티어아이파크', 84.9, 295000, 2024),
        ('서울특별시', '강남구', '11680', '대치동', '은마아파트', 76.79, 245000, 1979),
        ('서울특별시', '서초구', '11650', '반포동', '아크로리버파크', 84.95, 430000, 2016),
        ('서울특별시', '송파구', '11710', '잠실동', '잠실엘스', 84.8, 260000, 2008),
        ('서울특별시', '마포구', '11440', '아현동', '마포래미안푸르지오', 84.59, 185000, 2014),
        ('서울특별시', '노원구', '11350', '상계동', '상계주공7단지', 59.39, 65000, 1988),
        ('경기도', '성남시 분당구', '41135', '정자동', '파크뷰', 139.9, 210000, 2004),
        ('경기도', '수원시 영통구', '41117', '이의동', '광교중흥S-클래스', 84.9, 142000, 2019),
        ('경기도', '화성시', '41590', '오산동', '동탄역롯데캐슬', 84.95, 155000, 2021),
        ('인천광역시', '연수구', '28185', '송도동', '송도더샵퍼스트파크', 84.9, 98000, 2017),
        ('부산광역시', '해운대구', '26350', '우동', '해운대두산위브더제니스', 127.3, 175000, 2011),
        ('대구광역시', '수성구', '27260', '범어동', '범어에스케이뷰', 84.9, 105000, 2009),
        ('대전광역시', '유성구', '30200', '상대동', '도안신도시트리풀시티9단지', 101.9, 87000, 2011),
        ('세종특별자치시', '세종특별자치시', '36110', '새롬동', '새뜸마을1단지', 84.9, 72000, 2017),
        ('광주광역시', '남구', '29155', '봉선동', '봉선한국아델리움', 84.9, 79000, 2011)
    ]

    records = []
    delta_days = (end_date - start_date).days + 1

    random.seed(42)
    # 7일간 약 300~500건의 샘플 거래 생성
    for _ in range(350):
        day_offset = random.randint(0, delta_days - 1)
        deal_d = start_date + timedelta(days=day_offset)
        prov, sgg, sgg_cd, bjdong, apt, area, base_price, build_y = random.choice(sample_apts)

        # 가격 및 면적에 약간의 변동
        price_variation = random.uniform(0.92, 1.08)
        actual_price = int(round(base_price * price_variation, -2))
        floor = random.randint(2, 35)

        records.append({
            'province': prov,
            'sigungu': sgg,
            'sigungu_cd': sgg_cd,
            'bjdong': bjdong,
            'apt_name': apt,
            'deal_date': deal_d,
            'deal_amount': actual_price,
            'exclu_use_ar': area,
            'pyeong': round(area / 3.305785, 1),
            'price_per_pyeong': round(actual_price / (area / 3.305785), 1),
            'floor': floor,
            'build_year': build_y
        })

    df = pd.DataFrame(records).sort_values(by='deal_date', ascending=False).reset_index(drop=True)
    return df


def save_dataset(df: pd.DataFrame, output_dir: str | Path = "data"):
    """수집된 데이터프레임을 Parquet 및 메타데이터 JSON으로 저장합니다."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    parquet_file = out_path / "latest_7days.parquet"
    meta_file = out_path / "metadata.json"

    df.to_parquet(parquet_file, engine="pyarrow", compression="snappy", index=False)

    min_date = str(df['deal_date'].min()) if not df.empty else ""
    max_date = str(df['deal_date'].max()) if not df.empty else ""

    metadata = {
        "last_updated": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S KST"),
        "total_records": len(df),
        "date_range": [min_date, max_date]
    }

    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(df)} records to {parquet_file}")
    print(f"Updated metadata: {metadata}")


def run_collection(sample: bool = False, use_mock: bool = False):
    """실거래가 수집 파이프라인 메인 실행 함수"""
    start_date, end_date = get_recent_7days_range()
    ymd_list = get_target_ymd_list(start_date, end_date)
    api_key = os.getenv("DATA_GO_KR_API_KEY", "").strip()

    print("=== 아파트 매매 실거래가 수집 시작 ===")
    print(f"수집 대상 기간: {start_date} ~ {end_date} (계약월: {ymd_list})")

    # API 키가 없거나 use_mock 플래그인 경우 mock 데이터 생성
    if use_mock or not api_key or api_key == "your_service_key_here":
        print("[INFO] 유효한 공공데이터 API 키가 없거나 Mock 모드이므로 현실적인 샘플 데이터를 생성합니다.")
        df_final = generate_mock_data(start_date, end_date)
        save_dataset(df_final)
        return

    lawd_dict = load_lawd_codes()
    all_raw_items = []

    # 샘플 모드일 경우 서울 3개 구만 테스트
    if sample:
        targets = [
            ('서울특별시', '강남구', '11680'),
            ('서울특별시', '서초구', '11650'),
            ('서울특별시', '송파구', '11710')
        ]
    else:
        targets = []
        for prov, sggs in lawd_dict.items():
            for sgg, code in sggs.items():
                targets.append((prov, sgg, code))

    print(f"총 {len(targets)}개 시군구 대상 수집 진행...")
    for prov, sgg, code in targets:
        for ymd in ymd_list:
            items = fetch_deals_by_lawd(api_key, code, ymd)
            for item in items:
                item['province'] = prov
                item['sigungu'] = sgg
            all_raw_items.extend(items)
            time.sleep(0.05)  # API 서버 부하 방지

    if not all_raw_items:
        print("[WARN] API로부터 수집된 데이터가 없습니다. Mock 데이터를 폴백으로 생성합니다.")
        df_final = generate_mock_data(start_date, end_date)
    else:
        df_raw = pd.DataFrame(all_raw_items)
        df_final = clean_and_filter_deals(df_raw, start_date, end_date)

    save_dataset(df_final)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="전국 아파트 실거래가 수집기")
    parser.add_argument("--sample", action="store_true", help="샘플 시군구만 수집")
    parser.add_argument("--mock", action="store_true", help="Mock 데이터 생성")
    args = parser.parse_args()

    run_collection(sample=args.sample, use_mock=args.mock)
