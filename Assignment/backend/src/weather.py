import httpx
from langchain_core.tools import tool

from src.config import settings

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Open-Meteo 지오코딩은 한글 도시명을 누락/오매칭한다(예: '서울'→0개, '부산'→대도시 누락).
# 주요 한국 도시는 영문명으로 정규화해 조회한다. LLM이 한글을 넘겨도 결정론적으로 동작.
_CITY_ALIASES = {
    "서울": "Seoul",
    "부산": "Busan",
    "인천": "Incheon",
    "대구": "Daegu",
    "대전": "Daejeon",
    "광주": "Gwangju",
    "울산": "Ulsan",
    "세종": "Sejong",
    "수원": "Suwon",
    "성남": "Seongnam",
    "용인": "Yongin",
    "고양": "Goyang",
    "창원": "Changwon",
    "청주": "Cheongju",
    "전주": "Jeonju",
    "천안": "Cheonan",
    "제주": "Jeju",
    "춘천": "Chuncheon",
    "강릉": "Gangneung",
    "포항": "Pohang",
}

_WMO_DESC = {
    0: "맑음",
    1: "대체로 맑음",
    2: "구름 조금",
    3: "흐림",
    45: "안개",
    48: "안개",
    51: "이슬비",
    53: "이슬비",
    55: "이슬비",
    61: "비",
    63: "비",
    65: "비",
    71: "눈",
    73: "눈",
    75: "눈",
    80: "소나기",
    81: "소나기",
    82: "소나기",
    95: "뇌우",
    96: "뇌우",
    99: "뇌우",
}


def _describe(code: int, precipitation_mm: float) -> str:
    if code in _WMO_DESC:
        return _WMO_DESC[code]
    return "비" if precipitation_mm > 0 else "흐림"


@tool
async def get_weather(city: str) -> dict:
    """주어진 도시의 '내일' 날씨(기온, 강수량, 강수확률, 날씨 상태)를 조회한다.
    사용자가 특정 도시의 날씨를 물을 때 호출한다."""
    try:
        query = _CITY_ALIASES.get(city.strip(), city.strip())
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            geo_resp = await client.get(
                GEOCODING_URL,
                params={"name": query, "count": 10, "language": "ko", "format": "json"},
            )
            geo_resp.raise_for_status()

            results = geo_resp.json().get("results") or []
            if not results:
                return {"error": f"도시 '{city}'을(를) 찾을 수 없어요."}

            # Open-Meteo는 인구순 정렬이 아니라 동명의 소도시가 1위로 올 수 있다
            # (예: 'Jeju' 에티오피아). 가장 인구가 많은 주요 도시를 고른다.
            place = max(results, key=lambda r: r.get("population") or 0)
            forecast_resp = await client.get(
                FORECAST_URL,
                params={
                    "latitude": place["latitude"],
                    "longitude": place["longitude"],
                    "daily": (
                        "temperature_2m_max,temperature_2m_min,"
                        "precipitation_sum,precipitation_probability_max,weather_code"
                    ),
                    "timezone": "auto",
                },
            )
            forecast_resp.raise_for_status()

            daily = forecast_resp.json()["daily"]
            tomorrow_index = 1
            precipitation_mm = float(daily["precipitation_sum"][tomorrow_index])
            weather_code = int(daily["weather_code"][tomorrow_index])

            return {
                "city": place.get("name", city),
                "date": daily["time"][tomorrow_index],
                "temp_max": float(daily["temperature_2m_max"][tomorrow_index]),
                "temp_min": float(daily["temperature_2m_min"][tomorrow_index]),
                "precipitation_mm": precipitation_mm,
                "precipitation_prob": int(daily["precipitation_probability_max"][tomorrow_index]),
                "weather_desc": _describe(weather_code, precipitation_mm),
            }
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return {"error": "날씨 정보를 가져오지 못했어요. 잠시 후 다시 시도해 주세요."}
