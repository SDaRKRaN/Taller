import os
import sqlite3
import pandas as pd
from datetime import datetime
from tkinter import Tk, filedialog, messagebox


def importar_excel_a_sqlite():
    root = Tk()
    root.withdraw()

    # Seleccionar archivo Excel
    ruta_excel = filedialog.askopenfilename(
        title="Seleccionar archivo Excel",
        filetypes=[("Archivos Excel", "*.xlsx *.xls")]
    )
    if not ruta_excel:
        messagebox.showinfo("Importador", "No se seleccionó ningún archivo.")
        return

    # Cargar el Excel
    try:
        df = pd.read_excel(ruta_excel)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo leer el Excel: {e}")
        return

    # Conectar o crear la base de datos
    db_path = os.path.join(os.path.dirname(__file__), "avisos.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Crear tabla si no existe
    cur.execute("""
        CREATE TABLE IF NOT EXISTS avisos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ordenInterna TEXT,
            ordenTrabajo TEXT,
            cliente TEXT,
            direccion TEXT,
            poblacion TEXT,
            telefono TEXT,
            fechaVisita TEXT,
            horaInicio TEXT,
            turno TEXT,
            estado TEXT,
            observaciones TEXT
        )
    """)

    # Insertar datos
    for _, fila in df.iterrows():
        ordenInterna = str(fila.get("ORDEN INTERNA", "")).strip()
        ordenTrabajo = str(fila.get("ORDEN TRABAJO", "")).strip()
        cliente = str(fila.get("CLIENTE", "")).strip()
        direccion = str(fila.get("DIRECCION", "")).strip()
        poblacion = str(fila.get("POBLACION", "")).strip()
        telefono = str(fila.get("TELEFONO", "")).strip()
        fecha_valida = False
        fechaVisita = ""

        try:
            fecha_raw = fila.get("FECHA VISITA", "")
            if not pd.isna(fecha_raw):
                fechaVisita = pd.to_datetime(fecha_raw).strftime("%Y-%m-%d")
                fecha_valida = True
        except Exception:
            fechaVisita = ""

        horaInicio = str(fila.get("HORA INICIO", "")).strip()
        turno = str(fila.get("TURNO", "")).strip()
        observaciones = str(fila.get("OBSERVACIONES", "")).strip()

        # 🔧 Corrección: invertir la lógica del estado
        # Antes: pendiente si había fecha (incorrecto)
        # Ahora: pendiente si NO hay fecha (correcto)
        estado_importado = "sin asignar" if fecha_valida else "pendiente"

        cur.execute("""
            INSERT INTO avisos (
                ordenInterna, ordenTrabajo, cliente, direccion, poblacion, telefono,
                fechaVisita, horaInicio, turno, estado, observaciones
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ordenInterna, ordenTrabajo, cliente, direccion, poblacion, telefono,
            fechaVisita, horaInicio, turno, estado_importado, observaciones
        ))

    # Guardar cambios
    conn.commit()
    conn.close()
    messagebox.showinfo("Importador", "Importación completada correctamente.")


if __name__ == "__main__":
    importar_excel_a_sqlite()
