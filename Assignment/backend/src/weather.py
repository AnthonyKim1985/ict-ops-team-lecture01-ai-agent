import httpx
from langchain_core.tools import tool

from src.config import settings

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

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
    """주어진 도시의 내일 날씨 데이터를 조회한다."""
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            geo_resp = await client.get(
                GEOCODING_URL,
                params={"name": city, "count": 1, "language": "ko", "format": "json"},
            )
            geo_resp.raise_for_status()

            results = geo_resp.json().get("results") or []
            if not results:
                return {"error": f"도시 '{city}'을(를) 찾을 수 없어요."}

            place = results[0]
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
