from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="AlFares Farm OS Weather Service")

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"

ARABIC_CODES = {
    0: "صافٍ", 1: "صافٍ جزئياً", 2: "غائم جزئياً", 3: "غائم",
    45: "ضباب", 48: "ضباب متجمد", 51: "رذاذ خفيف", 61: "مطر خفيف",
    63: "مطر متوسط", 65: "مطر غزير", 71: "ثلج خفيف", 80: "زخات مطر",
    95: "عاصفة رعدية", 96: "عاصفة رعدية مع برد",
}


def irrigation_advice(et0_mm: float, rain_mm: float) -> str:
    net = et0_mm - rain_mm
    if net <= 1:
        return "لا حاجة للري اليوم؛ الأمطار تكفي."
    if net <= 3:
        return "ري خفيف (~15 م³/دونم) حسب نوع التربة."
    if net <= 5:
        return "ري متوسط (~25 م³/دونم)."
    return "تبخر عالٍ؛ يُنصح بالري (~35 م³/دونم) ويُفضّل فجراً أو مساءً."


@app.get("/weather")
def weather(lat: float = Query(...), lon: float = Query(...), days: int = Query(3, ge=1, le=7)):
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                 "et0_fao_evapotranspiration,wind_speed_10m_max,relative_humidity_2m_mean",
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "timezone": "auto",
        "forecast_days": days,
    }
    try:
        r = httpx.get(OPEN_METEO, params=params, timeout=30)
        r.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"خطأ في جلب بيانات الطقس: {exc}") from exc
    d = r.json()
    current = d.get("current", {})
    daily = d.get("daily", {})
    forecast = [
        {
            "date": daily["time"][i],
            "temp_max_c": daily["temperature_2m_max"][i],
            "temp_min_c": daily["temperature_2m_min"][i],
            "rain_mm": daily["precipitation_sum"][i],
            "et0_mm": daily["et0_fao_evapotranspiration"][i],
            "humidity_pct": daily["relative_humidity_2m_mean"][i],
            "wind_max_kmh": daily["wind_speed_10m_max"][i],
            "condition": ARABIC_CODES.get(daily.get("weather_code", [None])[i], "غير محدد"),
            "irrigation_advice": irrigation_advice(
                daily["et0_fao_evapotranspiration"][i], daily["precipitation_sum"][i]
            ),
        }
        for i in range(len(daily.get("time", [])))
    ]
    return {
        "location": {"lat": lat, "lon": lon},
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "current": {
            "temp_c": current.get("temperature_2m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "wind_kmh": current.get("wind_speed_10m"),
            "condition": ARABIC_CODES.get(current.get("weather_code"), "غير محدد"),
        },
        "forecast": forecast,
    }


@app.get("/health")
def health():
    return {"status": "ok"}
