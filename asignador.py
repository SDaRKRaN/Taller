# asignador.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt
import db

def abrir_asignador(fecha: str | None = None):
    """
    Abre una ventana con los avisos de la fecha seleccionada.
    Si no hay avisos para esa fecha, carga los pendientes.
    """
    dialogo = QDialog()
    titulo = f"Asignación de avisos ({fecha or 'pendientes'})"
    dialogo.setWindowTitle(titulo)
    layout = QVBoxLayout()

    etiqueta = QLabel(f"Avisos para la fecha {fecha or 'pendientes'}:")
    layout.addWidget(etiqueta)

    lista = QListWidget()
    layout.addWidget(lista)

    try:
        avisos = []

        # 1️⃣ Intentar cargar por fecha si la hay
        if fecha:
            print(f"🔎 Buscando avisos con fechaVisita = {fecha}")
            avisos = db.obtener_avisos_por_fecha(fecha)

        # 2️⃣ Si no hay o no se pasó fecha, cargar pendientes
        if not avisos:
            print("ℹ️ No se encontraron avisos por fecha. Cargando pendientes...")
            avisos = db.obtener_avisos_pendientes()

        print(f"✅ Se obtuvieron {len(avisos)} avisos desde la base de datos.")

        if not avisos:
            lista.addItem("No hay avisos para mostrar.")
        else:
            for aviso in avisos:
                texto = (
                    f"{aviso.get('ordenInterna', '')} | "
                    f"{aviso.get('cliente', '')} | "
                    f"{aviso.get('localidad', '')} | "
                    f"{aviso.get('estado', '')}"
                )
                item = QListWidgetItem(texto)
                item.setData(Qt.UserRole, aviso)
                lista.addItem(item)

            # Mostrar en la etiqueta el total
            etiqueta.setText(f"{len(avisos)} avisos encontrados ({fecha or 'pendientes'})")

    except Exception as e:
        lista.addItem(f"❌ Error cargando avisos: {e}")
        print("⚠️ Error en abrir_asignador:", e)

    dialogo.setLayout(layout)
    dialogo.exec()
