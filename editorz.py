# editor.py
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QDateEdit, QMessageBox
)
from PySide6.QtCore import QDate
from db import actualizar_aviso

class EditorAviso(QDialog):
    def __init__(self, aviso):
        super().__init__()
        self.setWindowTitle(f"Editar aviso {aviso.get('ordenTrabajo', '')}")
        self.resize(500, 400)
        self.aviso = aviso

        layout = QFormLayout()

        self.direccion = QLineEdit(aviso.get('direccion', ''))
        self.localidad = QLineEdit(aviso.get('localidad', ''))
        self.telefono = QLineEdit(aviso.get('telefono', ''))
        self.proveedor = QLineEdit(aviso.get('proveedor', ''))

        self.tipoOperacion = QComboBox()
        self.tipoOperacion.addItems(["Recogida", "Entrega"])
        self.tipoOperacion.setCurrentText(aviso.get('tipoOperacion', 'Recogida'))

        self.estado = QComboBox()
        self.estado.addItems(["pendiente", "cancelado", "reactivable"])
        self.estado.setCurrentText(aviso.get('estado', 'pendiente'))

        self.fechaVisita = QDateEdit()
        fecha_str = aviso.get('fechaVisita', '')
        fecha_qdate = QDate.fromString(fecha_str, "yyyy-MM-dd") if fecha_str else QDate.currentDate()
        self.fechaVisita.setDate(fecha_qdate)
        self.fechaVisita.setCalendarPopup(True)

        layout.addRow("Dirección:", self.direccion)
        layout.addRow("Localidad:", self.localidad)
        layout.addRow("Teléfono:", self.telefono)
        layout.addRow("Proveedor:", self.proveedor)
        layout.addRow("Tipo operación:", self.tipoOperacion)
        layout.addRow("Estado:", self.estado)
        layout.addRow("Fecha visita:", self.fechaVisita)

        self.boton_guardar = QPushButton("Guardar cambios")
        self.boton_guardar.clicked.connect(self.guardar)
        layout.addRow(self.boton_guardar)

        self.setLayout(layout)

    def guardar(self):
        datos_actualizados = {
            "direccion": self.direccion.text(),
            "localidad": self.localidad.text(),
            "telefono": self.telefono.text(),
            "proveedor": self.proveedor.text(),
            "tipoOperacion": self.tipoOperacion.currentText(),
            "estado": self.estado.currentText(),
            "fechaVisita": self.fechaVisita.date().toString("yyyy-MM-dd"),
            "ordenTrabajo": self.aviso.get("ordenTrabajo")
        }

        if not datos_actualizados["ordenTrabajo"]:
            QMessageBox.warning(self, "Error", "No se puede guardar: falta el número de orden.")
            return

        # Validar que la fecha no caiga en fin de semana
        fecha_nueva = datos_actualizados.get("fechaVisita")
        if fecha_nueva:
            try:
                dia_sem = datetime.strptime(fecha_nueva, "%Y-%m-%d").isoweekday()
                if dia_sem in (6, 7):
                    QMessageBox.warning(self, "Validación", "No se permiten asignaciones en fines de semana (sábado o domingo).")
                    return
            except Exception:
                QMessageBox.warning(self, "Validación", "Fecha visita inválida.")
                return

        actualizar_aviso(datos_actualizados)
        self.accept()
