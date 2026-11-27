import datetime as dt
import os

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from sentinelhub import (
    CRS, BBox, DataCollection, MimeType, SentinelHubRequest, SHConfig,
    bbox_to_dimensions,
)

app = FastAPI(title="AlFares Farm OS NDVI Service (Sentinel-2)")

EVALSCRIPT = """
//VERSION=3
function setup() {
  return { input: ["B04", "B08", "dataMask"], output: { bands: 2 } };
}
function evaluatePixel(sample) {
  var ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04 + 0.0001);
  return [ndvi, sample.dataMask];
}
"""

config = SHConfig()
config.sh_client_id = os.getenv("SH_CLIENT_ID", "")
config.sh_client_secret = os.getenv("SH_CLIENT_SECRET", "")


def interpret(ndvi: float) -> str:
    if ndvi < 0.2:
        return "نبات ضعيف جداً أو تربة مكشوفة — راجع الري والتسميد فوراً."
    if ndvi < 0.4:
        return "غطاء نباتي ضعيف — احتمال إجهاد مائي أو آفات."
    if ndvi < 0.6:
        return "نمو متوسط."
    return "غطاء نباتي قوي وصحي."


@app.get("/ndvi")
def ndvi(
    lat: float = Query(...),
    lon: float = Query(...),
    buffer_m: int = Query(250, ge=50, le=2000),
    days_back: int = Query(30, ge=5, le=180),
):
    if not config.sh_client_id:
        raise HTTPException(
            status_code=400,
            detail="يجب ضبط SH_CLIENT_ID و SH_CLIENT_SECRET في ملف .env (حساب مجاني في copernicus.eu)",
        )
    buf_deg = buffer_m / 111000.0
    bbox = BBox([lon - buf_deg, lat - buf_deg, lon + buf_deg, lat + buf_deg], CRS.WGS84)
    size = bbox_to_dimensions(bbox, resolution=10)
    if size[0] * size[1] > 2500 * 2500:
        raise HTTPException(status_code=400, detail="المساحة كبيرة جداً؛ قلّل buffer_m")

    end = dt.datetime.utcnow()
    start = end - dt.timedelta(days=days_back)

    request = SentinelHubRequest(
        evalscript=EVALSCRIPT,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A,
                time_interval=(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")),
                mosaicking_order="leastCC",
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=bbox,
        size=size,
        config=config,
    )
    try:
        data = request.get_data()[0]
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"فشل الاتصال بخدمة Sentinel Hub: {exc}") from exc

    ndvi_band = data[..., 0]
    mask = data[..., 1] > 0
    valid = ndvi_band[mask]
    if valid.size == 0:
        raise HTTPException(status_code=404, detail="لا توجد صور قمر صناعي صالحة لهذه الفترة")

    mean_ndvi = float(valid.mean())
    return {
        "period": {"from": start.strftime("%Y-%m-%d"), "to": end.strftime("%Y-%m-%d")},
        "pixels": int(valid.size),
        "ndvi_mean": round(mean_ndvi, 3),
        "ndvi_min": round(float(valid.min()), 3),
        "ndvi_max": round(float(valid.max()), 3),
        "interpretation": interpret(mean_ndvi),
    }


@app.get("/health")
def health():
    return {"status": "ok", "configured": bool(config.sh_client_id)}
