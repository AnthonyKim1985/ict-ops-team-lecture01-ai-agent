import pytest

from src.weather import get_weather


@pytest.mark.asyncio
async def test_get_weather_success(httpx_mock):
    httpx_mock.add_response(
        json={"results": [{"name": "서울", "latitude": 37.566, "longitude": 126.978}]},
    )
    httpx_mock.add_response(
        json={
            "daily": {
                "time": ["2026-06-19", "2026-06-20"],
                "temperature_2m_max": [20.0, 12.0],
                "temperature_2m_min": [14.0, 7.0],
                "precipitation_sum": [0.0, 5.2],
                "precipitation_probability_max": [10, 80],
                "weather_code": [1, 61],
            }
        },
    )

    result = await get_weather.ainvoke({"city": "서울"})

    assert result == {
        "city": "서울",
        "date": "2026-06-20",
        "temp_max": 12.0,
        "temp_min": 7.0,
        "precipitation_mm": 5.2,
        "precipitation_prob": 80,
        "weather_desc": "비",
    }


@pytest.mark.asyncio
async def test_get_weather_city_not_found(httpx_mock):
    httpx_mock.add_response(
        json={"results": []},
    )

    result = await get_weather.ainvoke({"city": "없는도시"})

    assert result == {"error": "도시 '없는도시'을(를) 찾을 수 없어요."}


@pytest.mark.asyncio
async def test_get_weather_api_error(httpx_mock):
    httpx_mock.add_response(
        json={"results": [{"name": "서울", "latitude": 37.566, "longitude": 126.978}]},
    )
    httpx_mock.add_response(
        status_code=500,
    )

    result = await get_weather.ainvoke({"city": "서울"})

    assert result == {"error": "날씨 정보를 가져오지 못했어요. 잠시 후 다시 시도해 주세요."}
