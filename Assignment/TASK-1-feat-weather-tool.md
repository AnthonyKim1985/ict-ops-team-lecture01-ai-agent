# TASK-1: 날씨 도구(Skill) 구현 — `weather.py`

> **시작 브랜치:** `feat/weather-tool` (TASK-0 머지 후 `git switch -c feat/weather-tool`)
> **이 문서만 보고 개발할 수 있도록 구성됨.** 외부 참조는 맨 아래 "참조" 절에만.

## 선행 작업 (TASK-0 산출물 — 이미 존재해야 함)

- `backend/` 에 `pyproject.toml`(deps + `pythonpath=["."]`, `asyncio_mode="auto"`), `src/__init__.py`, `src/config.py`가 있다.
- `backend/test/conftest.py`가 더미 `ANTHROPIC_API_KEY`를 주입한다.
- 사용할 설정 인터페이스(원문):

  - `from src.config import settings` → `settings.request_timeout_seconds`(float, 기본 10.0) 사용.
- 의존성 `httpx`, `pytest-httpx`는 `pip install -e ".[test]"`로 설치돼 있다.

## 목표

LangChain `@tool`로 **`get_weather(city: str)`**를 구현한다. Claude Haiku가 이 도구를 호출한다. Open-Meteo를 **2단계**(지오코딩 → 예보)로 호출해 **내일** 날씨를 구조화된 dict로 반환한다.

### 핵심 설계 원칙
- **도구는 데이터만, 판단은 LLM이.** 우산 권유 같은 판단/표현은 도구가 하지 않는다. 도구는 원시 수치(기온·강수·강수확률)만 제공.
- **`weather_code`(WMO 0–99)는 도구 내부에서 한글 `weather_desc`로 매핑**한다. 원시 코드를 LLM에 해석시키면 불안정하므로.
- **내일 = `daily` 배열의 index 1** (index 0 = 오늘). `timezone=auto`로 현지 날짜 경계 보장.

## 만들 파일

```
backend/src/weather.py        ← 신규 (프로덕션 코드)
backend/test/test_weather.py  ← 신규 (테스트 — src에 두지 말 것)
```

## 반환 계약 (다운스트림 TASK-2가 그대로 의존하므로 정확히 지킬 것)

**성공 시 dict (정확히 이 7개 키):**
```python
{
  "city": "서울",            # 지오코딩이 돌려준 도시명(name)
  "date": "2026-06-20",      # 내일 날짜 (daily.time[1])
  "temp_max": 12.0,          # float, 섭씨
  "temp_min": 7.0,           # float, 섭씨
  "precipitation_mm": 5.2,   # float, mm
  "precipitation_prob": 80,  # int, %
  "weather_desc": "비",       # weather_code → 한글
}
```

**실패 시 dict (정확히 이 1개 키):**
```python
{"error": "도시 '없는도시'을(를) 찾을 수 없어요."}   # 도시 미발견
{"error": "날씨 정보를 가져오지 못했어요. 잠시 후 다시 시도해 주세요."}  # API/네트워크 오류
```

> 도구는 예외를 밖으로 던지지 않는다. 모든 실패를 위 `{"error": ...}` dict로 변환한다(LLM이 사용자에게 전달).

## Open-Meteo API 명세 (이 두 엔드포인트만 사용)

1. **지오코딩** (도시명 → 위경도)
   `GET https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=ko&format=json`
   응답 예:
   ```json
   { "results": [ { "name": "서울", "latitude": 37.566, "longitude": 126.978 } ] }
   ```
   `results`가 없거나 빈 배열이면 → 도시 미발견.

2. **예보** (위경도 → 일별 예보)
   `GET https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code&timezone=auto`
   응답 예:
   ```json
   {
     "daily": {
       "time": ["2026-06-19", "2026-06-20"],
       "temperature_2m_max": [20.0, 12.0],
       "temperature_2m_min": [14.0, 7.0],
       "precipitation_sum": [0.0, 5.2],
       "precipitation_probability_max": [10, 80],
       "weather_code": [1, 61]
     }
   }
   ```
   **index 1**(내일)을 읽는다.

## WMO weather_code → 한글 매핑 (도구 내부)

핵심 코드만 매핑하고, 미정의 코드는 강수량 기반 기본값으로 처리한다.

| code | 한글 | code | 한글 |
|---|---|---|---|
| 0 | 맑음 | 51,53,55 | 이슬비 |
| 1 | 대체로 맑음 | 61,63,65 | 비 |
| 2 | 구름 조금 | 71,73,75 | 눈 |
| 3 | 흐림 | 80,81,82 | 소나기 |
| 45,48 | 안개 | 95,96,99 | 뇌우 |

미정의 코드: `precipitation_mm > 0`이면 `"비"`, 아니면 `"흐림"`.

---

## 단계별 작업 (TDD)

### Step 1: 실패 테스트 작성 — `backend/test/test_weather.py`

> `pytest-httpx`의 `httpx_mock` 픽스처를 쓴다. 등록한 응답은 **요청 순서대로(FIFO)** 소비되므로, 성공 케이스는 지오코딩 응답 → 예보 응답 순으로 등록한다. `get_weather`는 `@tool`이므로 `await get_weather.ainvoke({"city": ...})`로 호출한다.

```python
import pytest

from src.weather import get_weather


@pytest.mark.asyncio
async def test_get_weather_success(httpx_mock):
    # 1) 지오코딩 응답 (FIFO: 먼저 등록)
    httpx_mock.add_response(
        url__startswith="https://geocoding-api.open-meteo.com/v1/search",
        json={"results": [{"name": "서울", "latitude": 37.566, "longitude": 126.978}]},
    )
    # 2) 예보 응답
    httpx_mock.add_response(
        url__startswith="https://api.open-meteo.com/v1/forecast",
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

    assert result["city"] == "서울"
    assert result["date"] == "2026-06-20"        # 내일 = index 1
    assert result["temp_max"] == 12.0
    assert result["temp_min"] == 7.0
    assert result["precipitation_mm"] == 5.2
    assert result["precipitation_prob"] == 80
    assert result["weather_desc"] == "비"         # code 61 → 비


@pytest.mark.asyncio
async def test_get_weather_city_not_found(httpx_mock):
    httpx_mock.add_response(
        url__startswith="https://geocoding-api.open-meteo.com/v1/search",
        json={"results": []},   # 빈 결과
    )

    result = await get_weather.ainvoke({"city": "없는도시"})

    assert "error" in result
    assert "없는도시" in result["error"]


@pytest.mark.asyncio
async def test_get_weather_api_error(httpx_mock):
    # 지오코딩 성공
    httpx_mock.add_response(
        url__startswith="https://geocoding-api.open-meteo.com/v1/search",
        json={"results": [{"name": "서울", "latitude": 37.566, "longitude": 126.978}]},
    )
    # 예보 500 오류
    httpx_mock.add_response(
        url__startswith="https://api.open-meteo.com/v1/forecast",
        status_code=500,
    )

    result = await get_weather.ainvoke({"city": "서울"})

    assert "error" in result
```

> **만약** 설치된 `pytest-httpx` 버전이 `url__startswith` 매처를 지원하지 않으면, `url=` 매처를 제거하고 응답을 **순서대로(FIFO)** 등록하기만 해도 된다(지오코딩이 항상 먼저 호출됨). 즉 `httpx_mock.add_response(json=...)`를 순서대로 두 번 호출.

### Step 2: 테스트 실패 확인

```bash
cd backend && pytest test/test_weather.py -v
```
기대: `ImportError`/`ModuleNotFoundError` 또는 수집 실패 (`weather.py` 없음).

### Step 3: 구현 — `backend/src/weather.py`

```python
import httpx
from langchain_core.tools import tool

from src.config import settings

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather_code → 한글 설명
_WMO_DESC = {
    0: "맑음", 1: "대체로 맑음", 2: "구름 조금", 3: "흐림",
    45: "안개", 48: "안개",
    51: "이슬비", 53: "이슬비", 55: "이슬비",
    61: "비", 63: "비", 65: "비",
    71: "눈", 73: "눈", 75: "눈",
    80: "소나기", 81: "소나기", 82: "소나기",
    95: "뇌우", 96: "뇌우", 99: "뇌우",
}


def _describe(code: int, precipitation_mm: float) -> str:
    if code in _WMO_DESC:
        return _WMO_DESC[code]
    return "비" if precipitation_mm > 0 else "흐림"


@tool
async def get_weather(city: str) -> dict:
    """주어진 도시의 '내일' 날씨(기온, 강수량, 강수확률, 날씨 상태)를 조회한다.
    사용자가 특정 도시의 날씨를 물을 때 호출한다."""
    timeout = settings.request_timeout_seconds
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 1) 지오코딩: 도시명 → 위경도
            geo_resp = await client.get(
                GEOCODING_URL,
                params={"name": city, "count": 1, "language": "ko", "format": "json"},
            )
            geo_resp.raise_for_status()
            results = geo_resp.json().get("results") or []
            if not results:
                return {"error": f"도시 '{city}'을(를) 찾을 수 없어요."}

            place = results[0]
            lat, lon = place["latitude"], place["longitude"]
            resolved_name = place.get("name", city)

            # 2) 예보: 위경도 → 일별 예보
            fc_resp = await client.get(
                FORECAST_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "temperature_2m_max,temperature_2m_min,"
                             "precipitation_sum,precipitation_probability_max,weather_code",
                    "timezone": "auto",
                },
            )
            fc_resp.raise_for_status()
            daily = fc_resp.json()["daily"]

            i = 1  # 내일 = index 1
            precipitation_mm = float(daily["precipitation_sum"][i])
            code = int(daily["weather_code"][i])

            return {
                "city": resolved_name,
                "date": daily["time"][i],
                "temp_max": float(daily["temperature_2m_max"][i]),
                "temp_min": float(daily["temperature_2m_min"][i]),
                "precipitation_mm": precipitation_mm,
                "precipitation_prob": int(daily["precipitation_probability_max"][i]),
                "weather_desc": _describe(code, precipitation_mm),
            }
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        return {"error": "날씨 정보를 가져오지 못했어요. 잠시 후 다시 시도해 주세요."}
```

### Step 4: 테스트 통과 확인

```bash
cd backend && pytest test/test_weather.py -v
```
기대: 3 passed.

### Step 5: 전체 테스트 회귀 확인

```bash
cd backend && pytest -v
```
기대: TASK-0 스모크 2개 + weather 3개 = 모두 통과.

### Step 6: 커밋

```bash
git add backend/src/weather.py backend/test/test_weather.py
git commit -m "feat: Open-Meteo 2단계 날씨 도구(get_weather) 구현 + 단위 테스트"
```

---

## 완료 기준 (Definition of Done)

- [ ] `pytest test/test_weather.py` → 3 passed (성공/도시없음/API오류)
- [ ] `get_weather`는 성공 시 정확히 7키 dict, 실패 시 `{"error": ...}` 반환
- [ ] `weather_code` → 한글 `weather_desc` 매핑 동작 (code 61 → "비")
- [ ] 내일(index 1) 데이터를 읽음
- [ ] 도구가 예외를 밖으로 던지지 않음(모두 error dict로 변환)
- [ ] 전체 `pytest` 회귀 통과, 커밋 완료

## 다음 태스크에 넘기는 인터페이스 (TASK-2가 의존)

- `from src.weather import get_weather` — LangChain `@tool`, **async**. 호출은 `await get_weather.ainvoke({"city": ...})`.
- 성공 반환: `{"city","date","temp_max","temp_min","precipitation_mm","precipitation_prob","weather_desc"}` (위 계약).
- 실패 반환: `{"error": "..."}`.

---

## 참조 (외부 문서/스킬 — 필요 시에만)

- `PLAN.md` §5.1(날씨 도구 상세), §10(리스크: 도시 미발견/타임아웃).
- Open-Meteo 공식 문서: geocoding-api.open-meteo.com, api.open-meteo.com (요청 시 파라미터 확인용).
- `langchain-fundamentals` 스킬 — `@tool` 데코레이터 동작이 헷갈릴 때만.
