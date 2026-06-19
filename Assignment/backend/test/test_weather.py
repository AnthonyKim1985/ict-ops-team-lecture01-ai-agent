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
async def test_get_weather_normalizes_korean_city_to_english(httpx_mock):
    # 한글 도시명은 Open-Meteo 지오코딩에서 누락/오매칭된다(예: '서울'→0개).
    # 도구가 영문명으로 정규화해 조회해야 한다 — LLM에 의존하지 않는 결정론적 보장.
    httpx_mock.add_response(
        json={
            "results": [
                {"name": "서울특별시", "latitude": 37.566, "longitude": 126.978, "population": 9776000}
            ]
        },
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

    await get_weather.ainvoke({"city": "서울"})

    geo_request = httpx_mock.get_requests()[0]
    assert geo_request.url.params["name"] == "Seoul"


@pytest.mark.asyncio
async def test_get_weather_picks_most_populous_when_names_collide(httpx_mock):
    # Open-Meteo 지오코딩은 인구순 정렬이 아니라서, 동명 도시가 있으면
    # 엉뚱한 소도시(예: 'Jeju' 에티오피아, population=None)가 1위로 올 수 있다.
    # 가장 인구가 많은(=주요) 도시를 골라야 한다.
    httpx_mock.add_response(
        json={
            "results": [
                {"name": "Jeju", "latitude": 8.41667, "longitude": 39.633, "population": None},
                {"name": "제주시", "latitude": 33.50972, "longitude": 126.52, "population": 620000},
            ]
        },
    )
    httpx_mock.add_response(
        json={
            "daily": {
                "time": ["2026-06-19", "2026-06-20"],
                "temperature_2m_max": [25.0, 27.0],
                "temperature_2m_min": [18.0, 20.0],
                "precipitation_sum": [0.0, 0.0],
                "precipitation_probability_max": [0, 10],
                "weather_code": [0, 1],
            }
        },
    )

    result = await get_weather.ainvoke({"city": "Jeju"})

    assert result["city"] == "제주시"


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
