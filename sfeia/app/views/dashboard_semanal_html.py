"""VIEW: dashboard HTML autocontenido de la recomendación semanal.

Recibe el payload de `FaseSemanal` y produce `docs/recomendacion_semanal.html`:
UN solo archivo (HTML + CSS + JS inline, sin CDN ni build) que abre sin
internet. Los datos viajan embebidos como JSON (`window.SEMANAL`) y las
gráficas SVG las dibuja el JS propio (helpers `chartLine`/`chartHist`). Todo
el texto estático se escapa (nombres de agentes vienen de BD) y el render es
determinista (mismo payload → mismo HTML byte a byte, requisito N0.2).
"""
from __future__ import annotations

import html
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

# ------------------------------------------------------------------ gate info
GATE_INFO = [
    ("V1_bootstrap", "Ventaja comprobada sobre el mercado (no es azar)", "p_valor"),
    ("V2_n_efectivo", "Base suficiente de agentes de referencia", "n_efectivo"),
    ("V3_holdout", "Consistencia en el período de comprobación", "persistencia"),
    ("V4_replicacion", "El desempeño se mantiene fuera del análisis", "ratio_replicacion"),
    ("V5_dsr", "Resultado corregido por las opciones evaluadas", "dsr"),
    ("E1_gana_segmento", "Días que gana al promedio del mercado", "pct_gana_segmento"),
    ("E2_sin_kill_switch", "Freno de seguridad no activado", "kill_switch"),
    ("E3_ev_historico", "Ganancia esperada positiva", "ev_historico"),
    ("E4_capacidad", "Tamaño operable en el mercado", "supera_capacidad"),
]


def _esc(v) -> str:
    return html.escape(str(v)) if v is not None else "—"


def _fmt(v, dec: int = 2, suf: str = "") -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.{dec}f}".replace(",", " ") + suf
    return f"{v}{suf}"


def _valor_gate(fila: dict | None, clave: str) -> str:
    if not fila:
        return "—"
    v = fila.get(clave)
    if clave == "p_valor":
        return "—" if v is None else f"{v * 100.0:.1f} %"
    if clave == "n_efectivo":
        return "—" if v is None else str(int(v))
    if clave == "persistencia":
        return "—" if v is None else f"{v:.0f} %"
    if clave == "ratio_replicacion":
        return "—" if v is None else f"{v:.2f}"
    if clave == "dsr":
        return "—" if v is None else f"{v * 100.0:.0f} %"
    if clave == "pct_gana_segmento":
        return "—" if v is None else f"{v:.1f} %"
    if clave in ("kill_switch", "supera_capacidad"):
        return "sí" if v else "no"
    if clave == "ev_historico":
        return "—" if v is None else f"{v:.2f}"
    return _esc(v)


# ------------------------------------------------------------------ CSS
_CSS = """
:root{--ok:#15803d;--ok-bg:#dcfce7;--warn:#b45309;--warn-bg:#fef3c7;--bad:#b91c1c;--bad-bg:#fee2e2;
      --ink:#111827;--mut:#6b7280;--line:#e5e7eb;--card:#ffffff;--bg:#f3f4f6;}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--ink);line-height:1.45}
.wrap{max-width:1120px;margin:0 auto;padding:16px 20px 48px}
h1{font-size:1.35rem;margin:0 0 2px}
h2{font-size:1.05rem;margin:28px 0 8px;border-bottom:2px solid var(--line);padding-bottom:4px}
h3{font-size:.95rem;margin:0 0 6px}
.meta{color:var(--mut);font-size:.85rem;margin-bottom:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
/* veredicto */
.veredicto{border-radius:14px;padding:20px 22px;margin:10px 0 18px;display:flex;align-items:center;gap:20px;flex-wrap:wrap}
.veredicto.ok{background:var(--ok-bg);border:2px solid var(--ok)}
.veredicto.bad{background:var(--bad-bg);border:2px solid var(--bad)}
.badge{font-size:1.7rem;font-weight:800;letter-spacing:.06em;padding:10px 22px;border-radius:10px;color:#fff;white-space:nowrap}
.badge.ok{background:var(--ok)}
.badge.bad{background:var(--bad)}
.razon{flex:1;min-width:260px;font-size:1rem}
/* kpis */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.kpi{background:var(--card);border:1px solid var(--line);border-left:6px solid var(--mut);border-radius:10px;padding:12px 14px}
.kpi.ok{border-left-color:var(--ok)}
.kpi.warn{border-left-color:#d97706}
.kpi.bad{border-left-color:var(--bad)}
.kpi .v{font-size:1.5rem;font-weight:700}
.kpi .l{font-size:.82rem;color:var(--mut)}
.kpi .n{font-size:.74rem;color:var(--mut);margin-top:4px}
/* regimen chips */
.chips{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}
.chip{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:6px 14px;font-size:.86rem}
.chip b{font-weight:700}
/* graficas */
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:14px;margin-top:12px}
.chart-svg svg{width:100%;height:auto;display:block}
.legend{display:flex;flex-wrap:wrap;gap:12px;margin-top:6px;font-size:.8rem;color:var(--mut)}
.legend .lg{display:inline-flex;align-items:center;gap:5px}
.legend i{display:inline-block;width:12px;height:4px;border-radius:2px}
.chart-empty{color:var(--mut);font-style:italic;padding:30px;text-align:center;background:#fafafa;border-radius:8px}
/* tablas */
table{width:100%;border-collapse:collapse;font-size:.86rem;background:var(--card)}
th,td{border:1px solid var(--line);padding:6px 9px;text-align:left}
th{background:#f9fafb;font-weight:600}
.gate-ok{color:var(--ok);font-weight:700}
.gate-bad{color:var(--bad);font-weight:700}
.gate-na{color:var(--mut)}
/* perfil */
.bar{position:relative;background:#f3f4f6;border-radius:6px;height:22px;min-width:120px;overflow:hidden}
.bar-fill{position:absolute;top:0;bottom:0;left:0;border-radius:6px}
.bar-v{position:absolute;right:6px;top:1px;font-size:.78rem;font-weight:600}
.bar-fill.azul{background:#2563eb}.bar-fill.verde{background:#16a34a}
/* warnings y conclusiones */
.warn-list li{margin:4px 0;padding:8px 12px;background:var(--warn-bg);border-left:4px solid #d97706;border-radius:6px;font-size:.9rem;list-style:none}
.concl li{margin:6px 0;padding:8px 12px;background:#eff6ff;border-left:4px solid #2563eb;border-radius:6px;font-size:.92rem}
footer{color:var(--mut);font-size:.78rem;margin-top:30px;border-top:1px solid var(--line);padding-top:10px}
@media print{.veredicto,.kpis,.charts,.grid2{break-inside:avoid}}
"""

# ------------------------------------------------------------------ JS
_JS = r"""
(function(){
"use strict";
var D=window.SEMANAL; if(!D) return;
function n(v){return (typeof v==='number'&&isFinite(v))?v:null;}
function fmt(v,d){d=(d===undefined)?1:d;if(v===null||v===undefined||isNaN(v))return '\u2014';
  return v.toLocaleString('es-CO',{minimumFractionDigits:d,maximumFractionDigits:d});}
function svgOpen(w,h){return '<svg viewBox="0 0 '+w+' '+h+'" xmlns="http://www.w3.org/2000/svg">';}
function vacio(id){var b=document.getElementById(id+'-box');if(b)b.innerHTML='<div class="chart-empty">Sin datos</div>';}

function chartLine(id,cfg){
  var box=document.getElementById(id+'-box'); if(!box) return;
  var W=760,H=280,PL=58,PR=16,PT=14,PB=30;
  var xs=cfg.x||[], sers=cfg.series||[];
  var allV=[];
  sers.forEach(function(se){se.values.forEach(function(v){if(n(v)!==null)allV.push(v);});});
  if(!allV.length){ box.innerHTML='<div class="chart-empty">Sin datos</div>'; return; }
  var ymin=Math.min.apply(null,allV), ymax=Math.max.apply(null,allV);
  if(cfg.ylim){ymin=cfg.ylim[0];ymax=cfg.ylim[1];}
  else if(ymin===ymax){ymin-=1;ymax+=1;}
  if(cfg.yfloor!==undefined&&ymin>cfg.yfloor)ymin=cfg.yfloor;
  if(cfg.yceil!==undefined&&ymax<cfg.yceil)ymax=cfg.yceil;
  var pad=(ymax-ymin)*0.08; ymin-=pad; ymax+=pad;
  function x(i){return PL+((xs.length<=1)?(W-PL-PR)/2:i*(W-PL-PR)/(xs.length-1));}
  function y(v){return PT+(H-PT-PB)*(1-(v-ymin)/(ymax-ymin));}
  function clampY(v){return Math.max(PT,Math.min(H-PT-0.5,y(v)));}
  var s='';
  if(cfg.band&&cfg.band.lo!==null&&cfg.band.lo!==undefined){
    var yTop=clampY(cfg.band.hi), yBot=clampY(cfg.band.lo);
    s+='<rect x="'+PL+'" y="'+yTop+'" width="'+(W-PL-PR)+'" height="'+(yBot-yTop)+'" fill="'+cfg.band.color+'" opacity="0.22"/>';
  }
  if(cfg.hlines){cfg.hlines.forEach(function(h){
    s+='<line x1="'+PL+'" y1="'+y(h.y)+'" x2="'+(W-PR)+'" y2="'+y(h.y)+'" stroke="'+h.color+'" stroke-dasharray="4 4" stroke-width="1"/>';
    s+='<text x="'+(W-PR+3)+'" y="'+(y(h.y)+3)+'" font-size="9" fill="'+h.color+'">'+h.label+'</text>';
  });}
  for(var t=0;t<=4;t++){var v=ymin+(ymax-ymin)*t/4, yy=y(v);
    s+='<line x1="'+PL+'" y1="'+yy+'" x2="'+(W-PR)+'" y2="'+yy+'" stroke="#e5e7eb" stroke-width="1"/>';
    s+='<text x="'+(PL-6)+'" y="'+(yy+4)+'" font-size="10" text-anchor="end" fill="#6b7280">'+fmt(v,1)+'</text>';}
  var idxs=[0,Math.floor((xs.length-1)/2),xs.length-1];
  idxs.forEach(function(i){if(i>=0&&i<xs.length){
    var anc=(i===0)?'start':((i===xs.length-1)?'end':'middle');
    s+='<text x="'+x(i)+'" y="'+(H-PB+16)+'" font-size="10" text-anchor="'+anc+'" fill="#6b7280">'+String(xs[i]).slice(5)+'</text>';}});
  sers.forEach(function(se){
    var d='',started=false;
    se.values.forEach(function(v,i){var vv=n(v);
      if(vv===null){started=false;return;}
      var xx=x(i), yy=y(vv);
      d+=(started?'L':'M')+xx.toFixed(1)+' '+yy.toFixed(1)+' ';started=true;});
    if(d){
      s+='<path d="'+d+'" fill="'+(cfg.fill?se.color:'none')+'" '+(cfg.fill?'opacity="0.30"':'stroke="'+se.color+'" stroke-width="2"')+'/>';
      s+='<path d="'+d+'" fill="none" stroke="'+se.color+'" stroke-width="2"/>';
    }
    if(se.values.length<=20){se.values.forEach(function(v,i){var vv=n(v);if(vv===null)return;
      s+='<circle cx="'+x(i)+'" cy="'+y(vv)+'" r="3" fill="'+se.color+'"/>';});}
  });
  box.innerHTML=svgOpen(W,H)+s+'</svg>';
  var leg=document.getElementById(id+'-legend');
  if(leg){
    var items=sers.map(function(se){return '<span class="lg"><i style="background:'+se.color+'"></i>'+se.name+'</span>';});
    if(cfg.band&&cfg.band.lo!==null&&cfg.band.lo!==undefined){
      items.push('<span class="lg"><i style="background:'+cfg.band.color+';opacity:.35"></i>'+cfg.band.label+'</span>');}
    leg.innerHTML=items.join('');
  }
}

function chartHist(id,cfg){
  var box=document.getElementById(id+'-box'); if(!box) return;
  var vals=(cfg.values||[]).filter(function(v){return n(v)!==null;});
  if(!vals.length){ box.innerHTML='<div class="chart-empty">Sin datos</div>'; return; }
  var W=760,H=280,PL=58,PR=16,PT=14,PB=30;
  var mn=Math.min.apply(null,vals), mx=Math.max.apply(null,vals);
  if(mn===mx){mn-=1;mx+=1;}
  var nbins=Math.min(12,Math.max(6,Math.ceil(vals.length/3)));
  var bw=(mx-mn)/nbins;
  var counts=[],i; for(i=0;i<nbins;i++)counts.push(0);
  vals.forEach(function(v){var k=Math.min(nbins-1,Math.floor((v-mn)/bw));counts[k]++;});
  var cmax=Math.max.apply(null,counts);
  function xv(v){return PL+(v-mn)*(W-PL-PR)/(mx-mn);}
  function yc(c){return PT+(H-PT-PB)*(1-c/cmax);}
  var s='';
  for(var t=0;t<=4;t++){var yy=PT+(H-PT-PB)*t/4;
    s+='<line x1="'+PL+'" y1="'+yy+'" x2="'+(W-PR)+'" y2="'+yy+'" stroke="#e5e7eb"/>';
    s+='<text x="'+(PL-6)+'" y="'+(yy+4)+'" font-size="10" text-anchor="end" fill="#6b7280">'+Math.round(cmax*t/4)+'</text>';}
  var bwPix=(W-PL-PR)/nbins;
  for(i=0;i<nbins;i++){s+='<rect x="'+(PL+i*bwPix+1)+'" y="'+yc(counts[i])+'" width="'+(bwPix-2)+'" height="'+(PT+(H-PT-PB)-yc(counts[i]))+'" fill="'+cfg.color+'" opacity="0.75"/>';}
  if(mn<0&&mx>0){s+='<line x1="'+PL+'" y1="'+yc(0)+'" x2="'+(W-PR)+'" y2="'+yc(0)+'" stroke="#374151" stroke-width="1.5"/>';}
  if(cfg.p5!==null&&cfg.p5!==undefined){s+='<line x1="'+xv(cfg.p5)+'" y1="'+PT+'" x2="'+xv(cfg.p5)+'" y2="'+(H-PB)+'" stroke="#b45309" stroke-dasharray="4 4"/>';
    s+='<text x="'+xv(cfg.p5)+'" y="'+(PT+10)+'" font-size="9" fill="#b45309">p5</text>';}
  if(cfg.p95!==null&&cfg.p95!==undefined){s+='<line x1="'+xv(cfg.p95)+'" y1="'+PT+'" x2="'+xv(cfg.p95)+'" y2="'+(H-PB)+'" stroke="#b45309" stroke-dasharray="4 4"/>';
    s+='<text x="'+xv(cfg.p95)+'" y="'+(PT+10)+'" font-size="9" fill="#b45309">p95</text>';}
  ['mn','mx'].forEach(function(k,i){var vv=(k==='mn')?mn:mx;
    s+='<text x="'+xv(vv)+'" y="'+(H-PB+16)+'" font-size="10" text-anchor="'+(i?'end':'start')+'" fill="#6b7280">'+fmt(vv,1)+'</text>';});
  box.innerHTML=svgOpen(W,H)+s+'</svg>';
}

var S=D.series||{};
var dias=S.dias||[];
if(dias.length){
  chartLine('g-margen',{x:dias,series:[
    {name:'Estrategia imitada',color:'#2563eb',values:S.margen_imitacion||[]},
    {name:'Agentes de referencia',color:'#16a34a',values:S.margen_maestros||[]},
    {name:'Promedio del mercado',color:'#d97706',values:S.margen_segmento||[]}]});
  chartLine('g-dd',{x:dias,series:[{name:'Pérdida acumulada',color:'#dc2626',values:S.drawdown||[]}],fill:true,yfloor:0});
  var hlines=[];
  (S.bins_spread||[]).forEach(function(b){var hi=b[2];if(hi!==null&&isFinite(hi)&&Math.abs(hi)<999999){hlines.push({y:hi,label:b[0],color:'#9ca3af'});}});
  chartLine('g-spread',{x:dias,series:[{name:'Brecha bolsa \u2212 contrato',color:'#7c3aed',values:S.spread||[]}],
    band:(S.rango_spread?{lo:S.rango_spread[0],hi:S.rango_spread[1],color:'#16a34a',label:'Rango histórico del modelo'}:null),
    hlines:hlines});
  chartLine('g-emb',{x:dias,series:[{name:'Embalses SIN',color:'#0891b2',values:S.embalses||[]}],ylim:[0,100],
    hlines:[{y:70,label:'70 %',color:'#16a34a'},{y:30,label:'30 %',color:'#dc2626'}]});
  chartHist('g-dist',{values:S.margen_imitacion||[],p5:(D.topn&&D.topn.p5!==undefined)?D.topn.p5:null,
    p95:(D.topn&&D.topn.p95!==undefined)?D.topn.p95:null,color:'#2563eb'});
}else{
  ['g-margen','g-dd','g-spread','g-emb','g-dist'].forEach(function(id){var b=document.getElementById(id+'-box');if(b)b.innerHTML='<div class="chart-empty">Sin datos</div>';});
}
})();
"""

_HEAD = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Recomendación semanal · SFEIA</title>
<style>{_CSS}</style>
</head>
<body><div class="wrap">
"""


def _header(p: dict) -> str:
    v = p["ventanas"]
    return (
        f"<h1>Recomendación semanal de operación · SFEIA</h1>"
        f"<div class='meta'>Segmento <b>{_esc(p['segmento'])}</b> · Estrategia <b>{_esc(p['estrategia'])}</b>"
        f" · Semana evaluada {_esc(v['impacto']['ini'])} → {_esc(v['impacto']['fin'])}"
        f" · Generado {_esc(p['generado'])}</div>"
    )


def _veredicto(p: dict) -> str:
    clase = "ok" if p["operar"] else "bad"
    return (
        f"<div class='veredicto {clase}'>"
        f"<div class='badge {clase}'>{_esc(p['veredicto'])}</div>"
        f"<div class='razon'><b>¿Por qué?</b> {_esc(p['razon'])}</div>"
        f"</div>"
    )


def _kpis(p: dict) -> str:
    decs = {"mediana_margen": 1, "pct_gana_segmento": 1, "dsr": 0, "bootstrap_p": 1,
            "n_efectivo": 0, "drawdown_max": 1, "ev_historico": 2, "embalses": 1}
    cards = []
    for k in p["kpis"]:
        dec = decs.get(k["id"], 2)
        cards.append(
            f"<div class='kpi {_esc(k['estado'])}'>"
            f"<div class='v'>{_fmt(k['valor'], dec)} <small>{_esc(k['unidad'])}</small></div>"
            f"<div class='l'>{_esc(k['etiqueta'])}</div>"
            f"<div class='n'>{_esc(k['nota'])}</div>"
            f"</div>"
        )
    return "<h2>La estrategia en números (última semana)</h2><div class='kpis'>" + "".join(cards) + "</div>"


def _regimen(p: dict) -> str:
    r = p["regimen"]
    h = p.get("historial_escasez", {}) or {}
    chips = [
        ("Brecha bolsa–contratos (último día)", _fmt(r.get("spread_ultimo"), 1, " COP/kWh")),
        ("Situación de precios", r.get("bin_actual")),
        ("Nivel de embalses", _fmt(r.get("nivel_embalses_ultimo"), 1, " %") + f" · {r.get('tendencia_embalses')}"),
        ("Escasez histórica", _fmt(h.get("pct_dias_escasez"), 2, " % de los días")),
        ("Días de escasez (semana evaluada)", f"{r.get('dias_escasez_impacto', 0)} de {r.get('n_dias_impacto', 0)}"),
    ]
    return ("<h2>Contexto del mercado</h2>"
            "<p class='meta'>La brecha bolsa–contratos indica qué tan cara está la bolsa frente a los contratos; "
            "cuando supera el precio de escasez, comprar en bolsa castiga fuerte al comercializador. "
            "Los embalses altos suelen anticipar bolsa baja.</p>"
            "<div class='chips'>" + "".join(
                f"<span class='chip'><b>{_esc(l)}:</b> {_esc(v)}</span>" for l, v in chips
            ) + "</div>")


def _graficas() -> str:
    cartas = [
        ("Resultado diario: la estrategia vs. el promedio del mercado", "g-margen",
         "COP/kWh por día. Azul: la estrategia imitada; verde: las empresas de referencia; ámbar: el promedio del mercado."),
        ("Pérdida acumulada (peor caída de la semana)", "g-dd",
         "COP/kWh acumulados. Cuánto se habría perdido desde el mejor momento de la semana."),
        ("Brecha de precios bolsa–contratos y rango del modelo", "g-spread",
         "COP/kWh. La banda verde es el rango de precios con el que se entrenó el modelo; fuera de ella, se reduce la exposición a bolsa."),
        ("Nivel de embalses del SIN", "g-emb",
         "% agregado. Referencia: arriba de 70 % holgado, debajo de 30 % crítico."),
        ("Distribución de resultados diarios", "g-dist",
         "Cuántos días de la semana dieron cada nivel de resultado (p5/p95 marcan días malos y buenos)."),
    ]
    piezas = []
    for titulo, cid, nota in cartas:
        piezas.append(
            f"<div class='card'><h3>{titulo}</h3><div class='chart-svg' id='{cid}-box'></div>"
            f"<div class='legend' id='{cid}-legend'></div>"
            f"<div class='meta'>{nota}</div></div>"
        )
    return "<h2>Gráficas</h2><div class='grid2 charts'>" + "".join(piezas) + "</div>"


def _barra(v: float, color: str) -> str:
    if v is None:
        return "<div class='bar'><span class='bar-v'>—</span></div>"
    w = min(100.0, max(0.0, v))
    return (f"<div class='bar'><div class='bar-fill {color}' style='width:{w:.1f}%'></div>"
            f"<span class='bar-v'>{v:.1f}</span></div>")


def _perfil(p: dict) -> str:
    perf = p.get("perfil") or {}
    rec = perf.get("recomendado") or {}
    real = perf.get("maestros_realizado") or {}
    defensivo = perf.get("es_defensivo", False)
    filas = []
    for key, etiqueta in [
        ("pct_cobertura", "Compras con contratos (% de la demanda)"),
        ("pct_exposicion", "Compras en bolsa (% de la demanda)"),
        ("pct_noreg", "Clientes no regulados (% de la demanda)"),
        ("pct_sicep", "Compras SICEP (% de la demanda)"),
    ]:
        filas.append(
            f"<tr><td>{etiqueta}</td>"
            f"<td>{_barra(rec.get(key), 'azul')}</td>"
            f"<td>{_barra(real.get(key), 'verde')}</td></tr>"
        )
    nota = (" <b>El precio de hoy está fuera del rango histórico del modelo: la recomendación es defensiva "
            "(menos bolsa, más contratos).</b>" if defensivo else "")
    arq = perf.get("arquetipo_ganador")
    extra = ""
    if arq:
        extra = ("<p class='meta'>La mejor estrategia según el nivel de precios de cada día (control del sistema): "
                 + "; ".join(f"<b>{_esc(a)}</b> cuando el mercado está {_esc(b)}" for b, a in sorted(arq.items())) + ".</p>")
    return (
        "<h2>Cómo operar (perfil recomendado)</h2><div class='card'>"
        f"<p class='meta'>Porcentajes sobre su demanda diaria.{nota} «Recomendado» es lo que el sistema sugiere "
        f"operar hoy; «Agentes de referencia» es lo que hicieron en promedio las empresas imitadas la última "
        f"semana. Contratos SICEP (recomendado): {_esc(rec.get('tiene_sicep'))}.</p>"
        "<table><tr><th>Variable</th><th>Recomendado (usted)</th><th>Agentes de referencia</th></tr>"
        + "".join(filas) + "</table>" + extra + "</div>"
    )


def _umbral_gate(k: str, umb: dict) -> str:
    if k == "V1_bootstrap":
        return "azar ≤ 5 %"
    if k == "V2_n_efectivo":
        return f"≥ {umb.get('min_n_efectivo', 3)} empresas"
    if k == "V3_holdout":
        return f"≥ {umb.get('min_persistencia', 50.0):.0f} %"
    if k == "V4_replicacion":
        return f"≥ {umb.get('min_replicacion', 0.5):.1f}"
    if k == "V5_dsr":
        return "≥ 95 %"
    if k == "E1_gana_segmento":
        return f"≥ {umb.get('min_pct_gana_segmento', 60.0):.0f} % de los días"
    if k == "E2_sin_kill_switch":
        return "no activado"
    if k == "E3_ev_historico":
        return "≥ 0 COP/kWh"
    if k == "E4_capacidad":
        return f"≤ {umb.get('capacidad_max_pct', 5.0):.0f} % del mercado"
    return "—"


def _tabla_gates(p: dict) -> str:
    g = p.get("gates") or {}
    umb = p.get("umbrales") or {}
    filas = ["<tr><th>¿La estrategia cumple…?</th><th>Meta</th><th>Estrategia elegida</th><th>Mejor alternativa</th></tr>"]

    def _celda(ev, fila):
        if ev is None:
            return "<td class='gate-na'>—</td>"
        pasa = ev["gates"].get(k)
        marca = ("✓" if pasa else "✗") if pasa is not None else "–"
        clase = "gate-ok" if pasa else ("gate-bad" if pasa is False else "gate-na")
        valor = _valor_gate(fila, campo)
        nota = ""
        if k == "V3_holdout" and pasa and fila and fila.get("persistencia") is None:
            nota = " <small>(no evaluada)</small>"
        return f"<td class='{clase}'>{marca} {valor}{nota}</td>"

    for k, nombre, campo in GATE_INFO:
        ev_t = g.get("topn")
        ev_a = g.get("arquetipo")
        filas.append(
            f"<tr><td>{nombre}</td><td class='meta'>{_umbral_gate(k, umb)}</td>"
            + _celda(ev_t, p.get("topn")) + _celda(ev_a, p.get("arquetipo")) + "</tr>"
        )
    return ("<h2>¿En qué se basa esta recomendación?</h2><div class='card'>"
            "<p class='meta'>El sistema solo recomienda operar cuando la estrategia demuestra una ventaja "
            "comprobada sobre el promedio del mercado (✓ en todos los criterios). Un solo ✗ basta para "
            "recomendar no operar.</p><table>" + "".join(filas) + "</table></div>")


def _tabla_maestros(p: dict) -> str:
    ms = p.get("maestros") or []
    if not ms:
        return ("<h2>Agentes de referencia (los que se imitan)</h2><div class='card'>"
                "<p class='meta'>Sin empresas de referencia (el análisis completo no corrió en esta ventana).</p></div>")
    filas = ["<tr><th>#</th><th>Código</th><th>Empresa</th><th>Días analizados</th>"
             "<th>Resultado medio (COP/kWh)</th><th>Ventaja sobre el mercado</th>"
             "<th>% días con pérdida</th><th>Peor caída</th></tr>"]
    for m in ms:
        filas.append(
            f"<tr><td>{_esc(m['posicion'])}</td><td><b>{_esc(m['codigo'])}</b></td><td>{_esc(m['nombre'])}</td>"
            f"<td>{_esc(m['n_dias'])}</td><td>{_fmt(m['mediana_margen'], 1)}</td>"
            f"<td>{_fmt(m['mediana_relativa'], 1)}</td><td>{_fmt(m['pct_dias_perdida'], 1, ' %')}</td>"
            f"<td>{_fmt(m['drawdown_max'], 1)}</td></tr>"
        )
    return ("<h2>Agentes de referencia (los que se imitan)</h2><div class='card'>"
            "<p class='meta'>La recomendación imita el comportamiento de las empresas de su mismo tamaño a las "
            "que mejor les fue con esta estrategia en los últimos 90 días.</p><table>" + "".join(filas) + "</table></div>")


def _alternativa(p: dict) -> str:
    alt = p.get("alternativa")
    if not alt:
        return ""
    return (
        "<h2>Si aun así quiere operar esta semana</h2><div class='card'>"
        f"<p>La estrategia analizada no mostró ventaja comprobada. La opción menos mala observada fue "
        f"<b>{_esc(alt['segmento'])} · {_esc(alt['estrategia'])}</b> (ventaja sobre el mercado de "
        f"{_fmt(alt['mediana_relativa_top'], 1)} COP/kWh, resultado medio "
        f"{_fmt(alt['mediana_imitacion'], 1)} COP/kWh) con las empresas de referencia: "
        + ", ".join(f"<b>{_esc(c)}</b>" for c in alt["codigos"])
        + ". Aun así no cumple todos los criterios: la regla del sistema sigue siendo no operar.</p></div>"
    )


def _advertencias(p: dict) -> str:
    advs = p.get("advertencias") or []
    items = "".join(f"<li>{_esc(a)}</li>" for a in advs)
    return "<h2>Notas honestas</h2><ul class='warn-list'>" + items + "</ul>"


def _conclusiones(p: dict) -> str:
    concl = p.get("conclusiones") or []
    items = "".join(f"<li>{_esc(c)}</li>" for c in concl)
    return "<h2>Qué hacer esta semana</h2><ol class='concl'>" + items + "</ol>"


def render(p: dict) -> str:
    """Renderiza el dashboard completo (HTML + CSS + JS inline). Determinista."""
    datos = json.dumps(p, ensure_ascii=False, sort_keys=True, default=str).replace("</", "<\\/")
    partes = [
        _HEAD,
        _header(p),
        _veredicto(p),
        _perfil(p),
        _kpis(p),
        _regimen(p),
        _graficas(),
        _tabla_gates(p),
        _tabla_maestros(p),
        _alternativa(p),
        _advertencias(p),
        _conclusiones(p),
        "<footer>Generado por SFEIA · recomendación automática basada en el comportamiento histórico de "
        "agentes del MEM colombiano · cifras estimadas con precios de referencia del sistema (no son "
        "liquidaciones reales) · no constituye asesoría financiera ni legal.</footer>",
        "<script>window.SEMANAL = " + datos + ";</script>",
        "<script>" + _JS + "</script>",
        "</div></body></html>",
    ]
    return "\n".join(partes)


def guardar(p: dict, cfg: dict) -> Path:
    destino = BASE_DIR / cfg["asistente"].get("semanal", {}).get(
        "salida_html", "docs/recomendacion_semanal.html")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(render(p), encoding="utf-8")
    return destino
