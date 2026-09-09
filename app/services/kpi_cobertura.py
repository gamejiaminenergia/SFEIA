"""KPIs de cobertura/exposición a partir de C04 (F2)."""
from __future__ import annotations


def resumen_cobertura(rows: list[dict]) -> dict[str, dict]:
    """Agrega C04 (por agente/mes) a un valor por agente para la ventana.

    C04: % cobertura = CompCont/Dema; % exposición = CompBolsNaci/Dema.
    """
    agregado: dict[str, dict] = {}
    for r in rows:
        agente = r["agente"]
        d = agregado.setdefault(agente, {"dema_gwh": 0.0, "cont_gwh": 0.0, "bolsa_gwh": 0.0})
        d["dema_gwh"] += float(r["dema_gwh"] or 0.0)
        d["cont_gwh"] += float(r["cont_gwh"] or 0.0)
        d["bolsa_gwh"] += float(r["bolsa_gwh"] or 0.0)
    out: dict[str, dict] = {}
    for agente, d in agregado.items():
        dema = d["dema_gwh"]
        out[agente] = {
            "dema_gwh": round(d["dema_gwh"], 1),
            "pct_cobertura": round(d["cont_gwh"] / dema * 100, 1) if dema else 0.0,
            "pct_exposicion": round(d["bolsa_gwh"] / dema * 100, 1) if dema else 0.0,
        }
    return out