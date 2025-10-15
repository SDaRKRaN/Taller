
import os
import sqlite3
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "avisos.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _row_to_dict(row: sqlite3.Row) -> Dict:
    return dict(row) if row else {}

# --- Lectura ---

def obtener_avisos_pendientes() -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            idAviso, ordenInterna, cliente, direccion, localidad, codigoPostal,
            telefono1, telefono2, aparato, marca, modelo, fechaAsignacion, averia,
            tipoServicio, conCargo, importe, metodoPago, observacionesCobro,
            estado, fechaVisita, tecnico, turno, proveedor, estadoCita, tipoOperacion,
            horaInicio, horaFin
        FROM avisos
        WHERE (estado IS NULL OR TRIM(estado) = '' OR LOWER(estado) LIKE 'pend%')
        ORDER BY fechaVisita ASC, horaInicio ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]

def obtener_avisos_por_fecha(fecha: str) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            idAviso, ordenInterna, cliente, direccion, localidad, codigoPostal,
            telefono1, telefono2, aparato, marca, modelo, fechaAsignacion, averia,
            tipoServicio, conCargo, importe, metodoPago, observacionesCobro,
            estado, fechaVisita, tecnico, turno, proveedor, estadoCita, tipoOperacion,
            horaInicio, horaFin
        FROM avisos
        WHERE fechaVisita = ?
        ORDER BY horaInicio ASC
    """, (fecha,))
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]

def obtener_todos_los_avisos() -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            idAviso, ordenInterna, cliente, direccion, localidad, codigoPostal,
            telefono1, telefono2, aparato, marca, modelo, fechaAsignacion, averia,
            tipoServicio, conCargo, importe, metodoPago, observacionesCobro,
            estado, fechaVisita, tecnico, turno, proveedor, estadoCita, tipoOperacion,
            horaInicio, horaFin
        FROM avisos
        ORDER BY fechaVisita DESC, horaInicio DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]

def obtener_avisos_sin_fecha() -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            idAviso, ordenInterna, cliente, direccion, localidad, codigoPostal,
            telefono1, telefono2, aparato, marca, modelo, fechaAsignacion, averia,
            tipoServicio, conCargo, importe, metodoPago, observacionesCobro,
            estado, fechaVisita, tecnico, turno, proveedor, estadoCita, tipoOperacion,
            horaInicio, horaFin
        FROM avisos
        WHERE fechaVisita IS NULL OR TRIM(COALESCE(fechaVisita, '')) = ''
        ORDER BY ordenInterna ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]

def obtener_fechas_con_avisos() -> List[str]:
    """Fechas con al menos un aviso (para el calendario)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT fechaVisita
        FROM avisos
        WHERE fechaVisita IS NOT NULL AND TRIM(fechaVisita) <> ''
    """)
    res = [row[0] for row in cur.fetchall()]
    conn.close()
    return res

# --- Escritura ---

# columnas válidas en la tabla (PRAGMA table_info(avisos))
_ALLOWED_COLUMNS = {
    "ordenInterna","cliente","direccion","localidad","codigoPostal",
    "telefono1","telefono2","aparato","marca","modelo","fechaAsignacion","averia",
    "tipoServicio","conCargo","importe","metodoPago","observacionesCobro",
    "estado","fechaVisita","tecnico","turno","proveedor","estadoCita","tipoOperacion",
    "horaInicio","horaFin"
}

def _normalize_update_payload(datos: dict) -> Dict:
    """
    - Mapea claves externas a columnas reales (p.ej. ordenTrabajo->ordenInterna, telefono->telefono1)
    - Elimina claves que no existan en la tabla
    """
    if not isinstance(datos, dict):
        return {}
    d = dict(datos)  # copia
    # mapear ordenTrabajo -> ordenInterna (sin pisar si ya viene ordenInterna)
    if "ordenTrabajo" in d and "ordenInterna" not in d:
        d["ordenInterna"] = d["ordenTrabajo"]
        d.pop("ordenTrabajo", None)
    # mapear telefono -> telefono1 si fuese necesario
    if "telefono" in d and "telefono1" not in d and "telefono2" not in d:
        d["telefono1"] = d.pop("telefono")
    # filtrar solo columnas permitidas (dejamos fuera idAviso y cualquier otra)
    return {k: v for k, v in d.items() if k in _ALLOWED_COLUMNS or k in ("idAviso","ordenInterna")}

def actualizar_aviso(datos: dict):
    if not datos:
        return
    payload = _normalize_update_payload(datos)

    conn = get_connection()
    cur = conn.cursor()

    id_aviso = payload.get("idAviso")
    orden = payload.get("ordenInterna")
    if not id_aviso and not orden:
        conn.close()
        raise ValueError("Falta idAviso o ordenInterna/ordenTrabajo")

    # construir SET excluyendo identificadores
    campos = [k for k in payload.keys() if k not in ("idAviso", "ordenInterna")]
    if not campos:
        conn.close()
        return  # nada que actualizar

    set_clause = ", ".join([f"{c}=?" for c in campos])
    valores = [payload[k] for k in campos]

    if id_aviso:
        sql = f"UPDATE avisos SET {set_clause} WHERE idAviso=?"
        valores.append(id_aviso)
    else:
        sql = f"UPDATE avisos SET {set_clause} WHERE ordenInterna=?"
        valores.append(orden)

    cur.execute(sql, valores)
    conn.commit()
    conn.close()

def actualizar_aviso_campos_basicos(
    ordenInterna: str,
    cliente: Optional[str] = None,
    horaInicio: Optional[str] = None,
    horaFin: Optional[str] = None,
    tecnico: Optional[str] = None,
    turno: Optional[str] = None,
    fechaVisita: Optional[str] = None
):
    if not ordenInterna:
        raise ValueError("Falta ordenInterna")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE avisos
        SET cliente = COALESCE(?, cliente),
            horaInicio = ?,
            horaFin = ?,
            tecnico = ?,
            turno = ?,
            fechaVisita = ?
        WHERE ordenInterna = ?
    """, (cliente, horaInicio, horaFin, tecnico, turno, fechaVisita, ordenInterna))
    conn.commit()
    conn.close()

def marcar_realizado(ordenInterna: str):
    if not ordenInterna:
        raise ValueError("Falta ordenInterna")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE avisos SET estado='realizado' WHERE ordenInterna=?", (ordenInterna,))
    conn.commit()
    conn.close()

def marcar_anulado(ordenInterna: str, motivo: Optional[str] = None):
    """
    Marca un aviso como 'anulado'. Si se pasa motivo, lo añade a observacionesCobro.
    """
    if not ordenInterna:
        raise ValueError("Falta ordenInterna")
    conn = get_connection()
    cur = conn.cursor()
    if motivo:
        cur.execute(
            """
            UPDATE avisos
               SET estado='anulado',
                   observacionesCobro = TRIM(COALESCE(observacionesCobro,'') || CASE WHEN ? <> '' THEN ' | Anulado: ' || ? ELSE '' END)
             WHERE ordenInterna=?
            """, (motivo, motivo, ordenInterna)
        )
    else:
        cur.execute("UPDATE avisos SET estado='anulado' WHERE ordenInterna=?", (ordenInterna,))
    conn.commit()
    conn.close()

def marcar_desanulado(ordenInterna: str):
    """
    Revierte un aviso anulado a 'pendiente'.
    """
    if not ordenInterna:
        raise ValueError("Falta ordenInterna")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE avisos SET estado='pendiente' WHERE ordenInterna=?", (ordenInterna,))
    conn.commit()
    conn.close()
