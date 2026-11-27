CROPS = {
    "wheat":     {"name_ar": "قمح",         "seed_kg_per_donum": 12, "n": 24, "p2o5": 12, "k2o": 8},
    "barley":    {"name_ar": "شعير",        "seed_kg_per_donum": 10, "n": 18, "p2o5": 10, "k2o": 6},
    "corn":      {"name_ar": "ذرة صفراء",   "seed_kg_per_donum": 6,  "n": 30, "p2o5": 14, "k2o": 12},
    "tomato":    {"name_ar": "طماطم",       "seed_gram_per_donum": 30, "n": 20, "p2o5": 18, "k2o": 24},
    "potato":    {"name_ar": "بطاطا",       "seed_kg_per_donum": 90, "n": 22, "p2o5": 20, "k2o": 28},
    "onion":     {"name_ar": "بصل",         "seed_kg_per_donum": 3,  "n": 18, "p2o5": 14, "k2o": 12},
    "sunflower": {"name_ar": "دوّار شمس",   "seed_kg_per_donum": 2,  "n": 16, "p2o5": 10, "k2o": 10},
    "alfalfa":   {"name_ar": "جت (برسيم)",  "seed_kg_per_donum": 4,  "n": 6,  "p2o5": 14, "k2o": 10},
}


def adjust_by_soil(n, p, k, soil):
    om = soil.get("organic_matter_pct")
    if om is not None:
        if om >= 2.0:
            n *= 0.85
        elif om < 1.0:
            n *= 1.15
    soil_p = soil.get("p_ppm")
    if soil_p is not None:
        if soil_p > 20:
            p *= 0.7
        elif soil_p < 8:
            p *= 1.25
    soil_k = soil.get("k_ppm")
    if soil_k is not None:
        if soil_k > 200:
            k *= 0.7
        elif soil_k < 100:
            k *= 1.25
    return n, p, k


def urea_split(n):
    return [
        {"stage": "قبل الزراعة",           "urea_46_0_0_kg": round(n * 0.3, 1)},
        {"stage": "مع أول ريّة (التفريع)", "urea_46_0_0_kg": round(n * 0.4, 1)},
        {"stage": "قبل الإثمار/السنابل",   "urea_46_0_0_kg": round(n * 0.3, 1)},
]
