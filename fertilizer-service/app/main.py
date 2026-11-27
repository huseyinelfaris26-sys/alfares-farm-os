import os

from fastapi import FastAPI, HTTPException, Query

from app.crops import CROPS, adjust_by_soil, urea_split

app = FastAPI(title="AlFares Farm OS Fertilizer & Seed Service")

DONUM_SIZE_M2 = float(os.getenv("DONUM_SIZE_M2", "2500"))


@app.get("/donum-size")
def donum_size():
    return {"donum_size_m2": DONUM_SIZE_M2}


@app.get("/crops")
def crops():
    return [
        {"id": cid, "name_ar": c["name_ar"], "seed_kg_per_donum": c.get("seed_kg_per_donum")}
        for cid, c in CROPS.items()
    ]


@app.get("/plan")
def plan(
    crop: str = Query(..., description="معرّف المحصول مثل wheat أو tomato"),
    area_donum: float = Query(1.0, gt=0),
    organic_matter_pct: float | None = Query(None, ge=0, le=15),
    p_ppm: float | None = Query(None, ge=0),
    k_ppm: float | None = Query(None, ge=0),
    crop_area_m2: float | None = Query(None, gt=0, description="مساحة منطقة الزراعة داخل الدونم"),
):
    key = crop.lower().strip()
    if key not in CROPS:
        raise HTTPException(status_code=404, detail=f"المحصول غير معروف. المتاح: {', '.join(CROPS)}")
    c = CROPS[key]

    eff_donum = area_donum
    if crop_area_m2 is not None:
        eff_donum = area_donum * (crop_area_m2 / DONUM_SIZE_M2)

    n, p, k = adjust_by_soil(
        c["n"], c["p2o5"], c["k2o"],
        {"organic_matter_pct": organic_matter_pct, "p_ppm": p_ppm, "k_ppm": k_ppm},
    )

    seed = None
    if "seed_kg_per_donum" in c:
        seed = {"unit": "kg", "amount": round(c["seed_kg_per_donum"] * eff_donum, 1)}
    elif "seed_gram_per_donum" in c:
        seed = {"unit": "g", "amount": round(c["seed_gram_per_donum"] * eff_donum, 1)}

    dap_kg = round(p * eff_donum, 1)
    mop_kg = round(k * eff_donum, 1)

    return {
        "crop": {"id": key, "name_ar": c["name_ar"]},
        "area_donum": area_donum,
        "donum_size_m2": DONUM_SIZE_M2,
        "seed": seed,
        "fertilizer_per_area": {
            "N_kg": round(n * eff_donum, 1),
            "P2O5_kg": round(p * eff_donum, 1),
            "K2O_kg": round(k * eff_donum, 1),
        },
        "products": {
            "DAP_18_46_0_kg": dap_kg,
            "MOP_0_0_50_kg": mop_kg,
            "urea_schedule": [
                {**s, "urea_46_0_0_kg": round(s["urea_46_0_0_kg"] * eff_donum, 1)}
                for s in urea_split(n)
            ],
        },
        "note": "الأرقام إرشادية وتُعدّل حسب تحليل التربة المخبري والري المحلي.",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
