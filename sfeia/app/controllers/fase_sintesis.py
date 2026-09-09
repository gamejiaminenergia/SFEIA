"""CONTROLLER F6: síntesis — matriz por segmento, arquetipos y contraste R0–R5."""
from __future__ import annotations

import math

from sfeia.app.models.entities import MatrizFila
from sfeia.app.services.tipificacion import tipificar

_ORDEN = {"GRANDE": 0, "MEDIANO": 1, "PEQUEÑO": 2}


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return float("nan")
    return round(num / (dx * dy), 3)


class FaseSintesis:
    def __init__(self, repo, cfg):
        self.repo = repo
        self.cfg = cfg

    def ejecutar(self, datos: dict) -> dict:
        por_codigo = datos["f-1"]["por_codigo"]

        def _f1(cod):
            return next((r for r in datos["f1"]["tabla"] if r["codigo"] == cod), {})

        def _f2(cod):
            return next((r for r in datos["f2"]["tabla"] if r["codigo"] == cod), {})

        def _f4(cod):
            return next((r for r in datos["f4"]["tabla"] if r["codigo"] == cod), {})

        def _f5(cod):
            return next((r for r in datos["f5"]["tabla"] if r["codigo"] == cod), {})

        filas: list[MatrizFila] = []
        for codigo in por_codigo:
            if codigo not in {c for codes in datos["f-1"]["muestra"].values() for c in codes}:
                continue
            a, b, d, e = _f1(codigo), _f2(codigo), _f4(codigo), _f5(codigo)
            seg = por_codigo[codigo].segmento.value
            m = {
                "pct_reg": a.get("pct_reg", 0.0),
                "pct_sicep": a.get("pct_sicep") or 0.0,
                "pct_cobertura": b.get("pct_cobertura", 0.0),
                "pct_exposicion": b.get("pct_exposicion", 0.0),
                "pct_perdidas": d.get("pct_perdidas", 0.0),
            }
            filas.append(MatrizFila(
                segmento=seg,
                agente=por_codigo[codigo].nombre,
                codigo=codigo,
                dema_gwh=a.get("dema_gwh", 0.0),
                pct_reg=m["pct_reg"],
                pct_cobertura=m["pct_cobertura"],
                pct_exposicion=m["pct_exposicion"],
                pct_sicep=round(m["pct_sicep"], 1),
                pct_perdidas=m["pct_perdidas"],
                costo_energia_cop_kwh=e.get("costo_energia_cop_kwh", 0.0),
                garantia_est_cop=e.get("garantia_exigida_cop", 0),
                provision_cartera_cop=e.get("provision_cartera_cop", 0),
                arquetipo=tipificar(codigo, seg, m),
            ))

        filas.sort(key=lambda f: (_ORDEN.get(f.segmento, 9), -f.dema_gwh))

        # ---- Contraste R0–R5 ----
        r0 = self._contraste_r0(filas)
        r1 = self._contraste_r1(filas)
        r2 = self._contraste_r2(filas)
        r3 = self._contraste_r3(filas)
        r4 = self._contraste_r4(filas, datos)
        r5 = self._contraste_r5(filas)

        resultado = {
            "matriz": filas,
            "r0": r0, "r1": r1, "r2": r2, "r3": r3, "r4": r4, "r5": r5,
        }
        datos["f6"] = resultado
        return resultado

    @staticmethod
    def _stats(rows: list[MatrizFila], key: str) -> dict:
        vals = [getattr(r, key) for r in rows]
        mean = sum(vals) / len(vals) if vals else 0.0
        med = sorted(vals)[len(vals) // 2] if vals else 0.0
        return {"n": len(vals), "prom": round(mean, 1), "mediana": round(med, 1)}

    def _contraste_r0(self, filas) -> dict:
        out = {}
        for seg in _ORDEN:
            group = [f for f in filas if f.segmento == seg]
            out[seg] = {
                "n": len(group),
                "dema_gwh": round(sum(f.dema_gwh for f in group), 1),
                "pct_noreg_prom": round(sum(100 - f.pct_reg for f in group) / len(group), 1) if group else 0,
                "cobertura_prom": round(sum(f.pct_cobertura for f in group) / len(group), 1) if group else 0,
                "exposicion_prom": round(sum(f.pct_exposicion for f in group) / len(group), 1) if group else 0,
            }
        return out

    @staticmethod
    def _contraste_r1(filas) -> dict:
        xs = [100 - f.pct_reg for f in filas]
        ys = [f.pct_exposicion for f in filas]
        return {"corr_pct_noreg_vs_exposicion": _pearson(xs, ys), "n": len(filas)}

    @staticmethod
    def _contraste_r2(filas) -> dict:
        xs = [f.pct_exposicion for f in filas]
        ys = [math.log10(max(f.garantia_est_cop, 1)) for f in filas]
        return {"corr_pct_exposicion_vs_log_garantia": _pearson(xs, ys), "n": len(filas)}

    @staticmethod
    def _contraste_r3(filas) -> dict:
        by_seg = {}
        for seg in _ORDEN:
            group = [f for f in filas if f.segmento == seg]
            by_seg[seg] = {
                "min": round(min((f.pct_sicep for f in group), default=0), 1),
                "max": round(max((f.pct_sicep for f in group), default=0), 1),
                "prom": round(sum(f.pct_sicep for f in group) / len(group), 1) if group else 0,
            }
        csic = next((f for f in filas if f.codigo == "CSIC"), None)
        return {"por_segmento": by_seg, "csic_pct_sicep": csic.pct_sicep if csic else None}

    @staticmethod
    def _contraste_r4(filas, datos) -> dict:
        meses = [r["mes"] for r in datos["f0"]["contexto"] if r.get("pbm_sobre_escasez")]
        # Agentes compradores netos en pico (descalce potencial) con alta exposición
        expuestos = [
            {"codigo": f.codigo, "segmento": f.segmento, "pct_exposicion": f.pct_exposicion}
            for f in filas if f.pct_exposicion >= 30
        ]
        return {"meses_pbm_sobre_escasez": meses, "agentes_alta_exposicion": expuestos}

    @staticmethod
    def _contraste_r5(filas) -> dict:
        xs = [f.pct_reg for f in filas]
        ys = [f.pct_perdidas for f in filas]
        return {"corr_pct_reg_vs_perdidas": _pearson(xs, ys), "n": len(filas)}