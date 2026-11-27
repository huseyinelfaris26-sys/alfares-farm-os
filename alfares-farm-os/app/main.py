import io
import os

import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image
from transformers import pipeline

from app.treatments import treatment_for

app = FastAPI(title="AlFares Farm OS Disease Service")

MODEL_ID = os.getenv(
    "HF_MODEL_ID", "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"
)
clf = None


@app.on_event("startup")
def load_model():
    global clf
    device = 0 if torch.cuda.is_available() else -1
    clf = pipeline("image-classification", model=MODEL_ID, device=device)


@app.post("/diagnose")
async def diagnose(file: UploadFile = File(...)):
    try:
        img = Image.open(io.BytesIO(await file.read())).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="ملف الصورة غير صالح") from exc

    preds = clf(img, top_k=3)
    top = preds[0]
    advice = treatment_for(top["label"])
    return {
        "diagnosis": {
            "class": top["label"],
            "confidence_pct": round(top["score"] * 100, 1),
        },
        "alternatives": [
            {"class": p["label"], "confidence_pct": round(p["score"] * 100, 1)}
            for p in preds[1:]
        ],
        **advice,
    }


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_ID}
