"""Repositorio de acceso a datos elecdb (MODEL).

Ejecuta las queries aisladas en sql/ contra PostgreSQL. Todas las consultas
están parametrizadas y filtran por fecha. La vista nunca consulta la BD.

Solo expone los métodos del flujo activo (segmentación, agregación diaria
y límite de datos para las ventanas del asistente).
"""
from __future__ import annotations

from pathlib import Path

import psycopg2
import psycopg2.extras

SQL_DIR = Path(__file__).resolve().parent.parent.parent / "sql"


def _split_sentencias(sql: str) -> list[str]:
    """Divide un script SQL en sentencias, ignorando ';' en comentarios y literales."""
    sentencias: list[str] = []
    actual: list[str] = []
    en_comentario = False
    en_comilla_simple = False
    en_comilla_doble = False
    i = 0
    n = len(sql)
    while i < n:
        c = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""
        if en_comentario:
            if c == "\n":
                en_comentario = False
            actual.append(c)
        elif en_comilla_simple:
            actual.append(c)
            if c == "'" and nxt == "'":
                actual.append(nxt)
                i += 1
            elif c == "'":
                en_comilla_simple = False
        elif en_comilla_doble:
            actual.append(c)
            if c == '"':
                en_comilla_doble = False
        elif c == "-" and nxt == "-":
            en_comentario = True
            actual.append(c)
        elif c == "'":
            en_comilla_simple = True
            actual.append(c)
        elif c == '"':
            en_comilla_doble = True
            actual.append(c)
        elif c == ";":
            sentencias.append("".join(actual))
            actual = []
        else:
            actual.append(c)
        i += 1
    if "".join(actual).strip():
        sentencias.append("".join(actual))
    return [s.strip() for s in sentencias if s.strip()]


def _tiene_sql(s: str) -> bool:
    """True si la sentencia contiene SQL real (no solo comentarios/espacios)."""
    cuerpo = "\n".join(line for line in s.splitlines() if not line.strip().startswith("--"))
    return bool(cuerpo.strip())


class RepoElecdb:
    """Fuente de datos de mercado (elecdb). Inyección vía constructor."""

    def __init__(self, dsn: str):
        self.dsn = dsn

    def _conectar(self):
        return psycopg2.connect(self.dsn)

    def _ejecutar_archivo(self, nombre: str, params: dict) -> list[list[dict]]:
        """Ejecuta cada statement de un archivo sql/ y devuelve sus resultados.

        Un archivo puede contener varias sentencias separadas por ';'. El
        splitter ignora ';' dentro de comentarios (--) y de literales.
        Todas las sentencias reciben los mismos parámetros.
        """
        sql = (SQL_DIR / nombre).read_text(encoding="utf-8")
        conn = self._conectar()
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            resultados: list[list[dict]] = []
            for s in _split_sentencias(sql):
                if not _tiene_sql(s):
                    continue
                cur.execute(s, params)
                resultados.append([dict(r) for r in cur.fetchall()])
            cur.close()
            return resultados
        finally:
            conn.close()

    # ---- F-1: segmentación de la población ----
    def segmentacion_poblacion(self, ini: str, fin: str) -> list[dict]:
        return self._ejecutar_archivo("f-1_segmentacion.sql", {"ini": ini, "fin": fin})[0]

    # ---- D1: agregación diaria por agente + precios de sistema ----
    def diario(self, ini: str, fin: str) -> list[dict]:
        return self._ejecutar_archivo("d1_diario.sql", {"ini": ini, "fin": fin})[0]

    # ---- D1 (auxiliar): límite de datos para las ventanas del asistente ----
    def fecha_max_sistema(self) -> str:
        """Última fecha con precios de sistema (límite para las ventanas)."""
        fila = self._ejecutar_archivo("d1_max_fecha.sql", {})[0][0]
        return str(fila["max_fecha"])

    # ---- D1 (auxiliar): histórico completo de precios (frecuencia de escasez) ----
    def historial_precios(self) -> list[dict]:
        """Todas las filas de fact_daily_sistema (precios diarios, 2015 → hoy)."""
        return self._ejecutar_archivo("d1_historial_precios.sql", {})[0]

    # ---- D1 (auxiliar): contexto hidrológico diario (nivel de embalses) ----
    def contexto_hidrologia(self, ini: str, fin: str) -> list[dict]:
        """Nivel agregado de embalses del SIN por día (régimen hidrológico)."""
        return self._ejecutar_archivo("d1_contexto_hidrologia.sql", {"ini": ini, "fin": fin})[0]