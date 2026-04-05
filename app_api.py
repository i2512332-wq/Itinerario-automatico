from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import math
import os
import re
import uuid
from datetime import datetime, timedelta
from utils.pdf_generator import generate_pdf
from utils.translator import translate_itinerary # Import original logic

app = FastAPI(title="Athena Logic Engine (FastAPI)")

# --- MODELOS DE DATOS ---

class TourItemForPricing(BaseModel):
    id: str
    titulo: str
    costo_nac: float
    costo_ext: float
    costo_can: float
    costo_nac_est: float = 0
    costo_nac_nino: float = 0
    costo_ext_est: float = 0
    costo_ext_nino: float = 0
    costo_can_est: float = 0
    costo_can_nino: float = 0
    usar_margen_propio: bool = False
    margen_individual: float = 30.0

class PricingRequest(BaseModel):
    itinerario: List[Dict[str, Any]] # Flexible input
    pax_counts: Dict[str, int]
    margen_pct: float
    margen_antes_pct: float
    adj_global: Dict[str, float]
    upgrades: Dict[str, float]

class TranslateRequest(BaseModel):
    itinerario: List[Dict[str, Any]]
    notas_finales: str
    target_lang: str

# --- ENDPOINTS ---

@app.post("/pricing")
async def calculate_pricing(req: PricingRequest):
    try:
        f_m = 1 + (req.margen_pct / 100)
        f_a = 1 + (req.margen_antes_pct / 100)
        
        # Pax numbers
        c_ad_nac = req.pax_counts.get("ad_nac", 0)
        c_es_nac = req.pax_counts.get("es_nac", 0)
        c_pc_nac = req.pax_counts.get("pc_nac", 0)
        c_ni_nac = req.pax_counts.get("ni_nac", 0)
        
        c_ad_ext = req.pax_counts.get("ad_ext", 0)
        c_es_ext = req.pax_counts.get("es_ext", 0)
        c_pc_ext = req.pax_counts.get("pc_ext", 0)
        c_ni_ext = req.pax_counts.get("ni_ext", 0)
        
        c_ad_can = req.pax_counts.get("ad_can", 0)
        c_es_can = req.pax_counts.get("es_can", 0)
        c_pc_can = req.pax_counts.get("pc_can", 0)
        c_ni_can = req.pax_counts.get("ni_can", 0)

        pasajeros_nac = c_ad_nac + c_es_nac + c_pc_nac + c_ni_nac
        pasajeros_ext = c_ad_ext + c_es_ext + c_pc_ext + c_ni_ext
        pasajeros_can = c_ad_can + c_es_can + c_pc_can + c_ni_can

        total_nac = total_ext = total_can = 0.0
        total_nac_a = total_ext_a = total_can_a = 0.0
        cost_margined_nac = {"ad":0, "es":0, "pc":0, "ni":0}
        cost_margined_ext = {"ad":0, "es":0, "pc":0, "ni":0}
        cost_margined_can = {"ad":0, "es":0, "pc":0, "ni":0}

        for t in req.itinerario:
            use_m = t.get('usar_margen_propio', False)
            m_t = t.get('margen_individual', 30.0) if use_m else req.margen_pct
            f_m_t = 1 + (m_t / 100)
            
            # Extract costs with fallbacks
            cn = t.get('costo_nac', 0)
            cn_es = t.get('costo_nac_est', cn-70)
            cn_pc = t.get('costo_nac_pcd', cn-70)
            cn_ni = t.get('costo_nac_nino', cn-40)

            ce = t.get('costo_ext', 0)
            ce_es = t.get('costo_ext_est', ce-20)
            ce_pc = t.get('costo_ext_pcd', ce-20)
            ce_ni = t.get('costo_ext_nino', ce-15)

            cc = t.get('costo_can', 0)
            cc_es = t.get('costo_can_est', cc-20)
            cc_pc = t.get('costo_can_pcd', cc-20)
            cc_ni = t.get('costo_can_nino', cc-15)

            # Venta
            total_nac += (math.ceil(cn * f_m_t) * c_ad_nac)
            total_nac += (math.ceil(cn_es * f_m_t) * c_es_nac)
            total_nac += (math.ceil(cn_pc * f_m_t) * c_pc_nac)
            total_nac += (math.ceil(cn_ni * f_m_t) * c_ni_nac)
            
            total_ext += (math.ceil(ce * f_m_t) * c_ad_ext)
            total_ext += (math.ceil(ce_es * f_m_t) * c_es_ext)
            total_ext += (math.ceil(ce_pc * f_m_t) * c_pc_ext)
            total_ext += (math.ceil(ce_ni * f_m_t) * c_ni_ext)

            total_can += (math.ceil(cc * f_m_t) * c_ad_can)
            total_can += (math.ceil(cc_es * f_m_t) * c_es_can)
            total_can += (math.ceil(cc_pc * f_m_t) * c_pc_can)
            total_can += (math.ceil(cc_ni * f_m_t) * c_ni_can)

            # Antes
            total_nac_a += (math.ceil(cn * f_a) * c_ad_nac)
            total_nac_a += (math.ceil(cn_es * f_a) * c_es_nac)
            total_nac_a += (math.ceil(cn_pc * f_a) * c_pc_nac)
            total_nac_a += (math.ceil(cn_ni * f_a) * c_ni_nac)

            total_ext_a += (math.ceil(ce * f_a) * c_ad_ext)
            total_ext_a += (math.ceil(ce_es * f_a) * c_es_ext)
            total_ext_a += (math.ceil(ce_pc * f_a) * c_pc_ext)
            total_ext_a += (math.ceil(ce_ni * f_a) * c_ni_ext)

            total_can_a += (math.ceil(cc * f_a) * c_ad_can)
            total_can_a += (math.ceil(cc_es * f_a) * c_es_can)
            total_can_a += (math.ceil(cc_pc * f_a) * c_pc_can)
            total_can_a += (math.ceil(cc_ni * f_a) * c_ni_can)

            # Details
            cost_margined_nac["ad"] += math.ceil(cn * f_m_t)
            cost_margined_nac["es"] += math.ceil(cn_es * f_m_t)
            cost_margined_nac["pc"] += math.ceil(cn_pc * f_m_t)
            cost_margined_nac["ni"] += math.ceil(cn_ni * f_m_t)
            
            cost_margined_ext["ad"] += math.ceil(ce * f_m_t)
            cost_margined_ext["es"] += math.ceil(ce_es * f_m_t)
            cost_margined_ext["pc"] += math.ceil(ce_pc * f_m_t)
            cost_margined_ext["ni"] += math.ceil(ce_ni * f_m_t)

            cost_margined_can["ad"] += math.ceil(cc * f_m_t)
            cost_margined_can["es"] += math.ceil(cc_es * f_m_t)
            cost_margined_can["pc"] += math.ceil(cc_pc * f_m_t)
            cost_margined_can["ni"] += math.ceil(cc_ni * f_m_t)

        # Finals with upgrades
        up_nac = req.upgrades.get("up_nac", 0)
        up_ext = req.upgrades.get("up_ext", 0)

        res = {
            "avg_nac_pp": math.ceil((total_nac + req.adj_global.get("extra_nac", 0)) / max(1, pasajeros_nac) + up_nac),
            "avg_ext_pp": math.ceil((total_ext + req.adj_global.get("extra_ext", 0)) / max(1, pasajeros_ext) + up_ext),
            "avg_can_pp": math.ceil((total_can + req.adj_global.get("extra_can", 0)) / max(1, pasajeros_can) + up_ext),
            
            "avg_nac_antes_pp": math.ceil((total_nac_a + req.adj_global.get("extra_nac", 0)) / max(1, pasajeros_nac) + up_nac),
            "avg_ext_antes_pp": math.ceil((total_ext_a + req.adj_global.get("extra_ext", 0)) / max(1, pasajeros_ext) + up_ext),
            "avg_can_antes_pp": math.ceil((total_can_a + req.adj_global.get("extra_can", 0)) / max(1, pasajeros_can) + up_ext),
        }
        res["real_nac"] = res["avg_nac_pp"] * pasajeros_nac
        res["real_ext"] = res["avg_ext_pp"] * pasajeros_ext
        res["real_can"] = res["avg_can_pp"] * pasajeros_can
        
        res["total_nac_pp"] = (total_nac + req.adj_global.get("extra_nac", 0)) / max(1, pasajeros_nac)
        res["total_ext_pp"] = (total_ext + req.adj_global.get("extra_ext", 0)) / max(1, pasajeros_ext)
        res["total_can_pp"] = (total_can + req.adj_global.get("extra_can", 0)) / max(1, pasajeros_can)
        res["total_nac_a_pp"] = (total_nac_a + req.adj_global.get("extra_nac", 0)) / max(1, pasajeros_nac)

        def fmt(v): return f"{math.ceil(v):,.2f}"
        
        m_en = req.adj_global.get("extra_nac", 0) / max(1, pasajeros_nac)
        m_ee = req.adj_global.get("extra_ext", 0) / max(1, pasajeros_ext)
        m_ec = req.adj_global.get("extra_can", 0) / max(1, pasajeros_can)

        res["det_nac"] = {
            "Adulto": fmt(cost_margined_nac["ad"] + m_en + up_nac) if c_ad_nac > 0 else None,
            "Estudiante": fmt(cost_margined_nac["es"] + m_en + up_nac) if c_es_nac > 0 else None,
            "PCD": fmt(cost_margined_nac["pc"] + m_en + up_nac) if c_pc_nac > 0 else None,
            "Niño": fmt(cost_margined_nac["ni"] + m_en + up_nac) if c_ni_nac > 0 else None,
        }
        res["det_ext"] = {
            "Adulto": fmt(cost_margined_ext["ad"] + m_ee + up_ext) if c_ad_ext > 0 else None,
            "Estudiante": fmt(cost_margined_ext["es"] + m_ee + up_ext) if c_es_ext > 0 else None,
            "PCD": fmt(cost_margined_ext["pc"] + m_ee + up_ext) if c_pc_ext > 0 else None,
            "Niño": fmt(cost_margined_ext["ni"] + m_ee + up_ext) if c_ni_ext > 0 else None,
        }
        res["det_can"] = {
            "Adulto": fmt(cost_margined_can["ad"] + m_ec + up_ext) if c_ad_can > 0 else None,
            "Estudiante": fmt(cost_margined_can["es"] + m_ec + up_ext) if c_es_can > 0 else None,
            "PCD": fmt(cost_margined_can["pc"] + m_ec + up_ext) if c_pc_can > 0 else None,
            "Niño": fmt(cost_margined_can["ni"] + m_ec + up_ext) if c_ni_can > 0 else None,
        }
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error Pricing: {str(e)}")

@app.post("/translate")
async def api_translate(req: TranslateRequest):
    try:
        # Calls original AI logic
        translated = translate_itinerary(req.itinerario, req.notas_finales, req.target_lang)
        return translated
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error Translate: {str(e)}")

@app.post("/generate-pdf")
async def api_generate_pdf(data: dict):
    try:
        pdf_path = generate_pdf(data)
        return {"status": "success", "pdf_path": pdf_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error PDF: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
