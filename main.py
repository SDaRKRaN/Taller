from datetime import datetime
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QMessageBox
from calendario import CalendarioAvisos
from pendientes import VentanaPendientes
from config import cargar_config, guardar_config

class VentanaPrincipal(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Avisos")
        self.resize(800, 600)

        self.config = cargar_config()

        self.calendario = CalendarioAvisos(parent=self)
        self.boton_asignar = QPushButton("Asignar casos")
        self.boton_asignar.hide()

        self.boton_horario = QPushButton(f"Horario: {self.config['horario'].capitalize()}")
        self.boton_horario.clicked.connect(self.cambiar_horario)

        self.boton_pendientes = QPushButton("Servicios sin asignar")
        self.boton_pendientes.clicked.connect(self.abrir_pendientes)

        layout = QVBoxLayout()
        layout.addWidget(self.boton_horario)
        layout.addWidget(self.calendario)
        layout.addWidget(self.boton_asignar)
        layout.addWidget(self.boton_pendientes)
        self.setLayout(layout)

        # conectar señal personalizada del calendario para abrir planificador al hacer click
        self.calendario.fecha_clicked.connect(self._on_fecha_clicked)
        # actualizar visibilidad del botón asignar cuando cambie selección
        self.calendario.selectionChanged.connect(self.actualizar_boton)
        self.boton_asignar.clicked.connect(self.asignar)

    def _on_fecha_clicked(self, fecha):
        # import diferido para evitar import circular
        from planificador import abrir_planificador
        abrir_planificador(fecha, parent=self)

    def actualizar_boton(self):
        fecha_str = self.calendario.fecha_seleccionada()
        if not fecha_str:
            self.boton_asignar.hide()
            return
        # comprobar fin de semana: isoweekday 6=sábado, 7=domingo
        try:
            dia_sem = datetime.strptime(fecha_str, "%Y-%m-%d").isoweekday()
            if dia_sem in (6, 7):
                self.boton_asignar.hide()
                return
        except Exception:
            # si formato inesperado, ocultar por seguridad
            self.boton_asignar.hide()
            return

        # mostrar solo si hay avisos y no es fin de semana
        if self.calendario.hay_avisos(fecha_str):
            self.boton_asignar.show()
        else:
            self.boton_asignar.hide()

    def asignar(self):
        fecha_str = self.calendario.fecha_seleccionada()
        if not fecha_str:
            QMessageBox.information(self, "Asignar", "Selecciona una fecha válida antes de asignar.")
            return
        try:
            dia_sem = datetime.strptime(fecha_str, "%Y-%m-%d").isoweekday()
            if dia_sem in (6, 7):
                QMessageBox.warning(self, "Asignar", "No se permiten asignaciones en fines de semana (sábado o domingo).")
                return
        except Exception:
            QMessageBox.warning(self, "Asignar", "Fecha inválida.")
            return

        # import diferido por seguridad
        from planificador import abrir_planificador
        abrir_planificador(fecha_str, parent=self)
        self.boton_asignar.hide()

    def cambiar_horario(self):
        nuevo = "verano" if self.config["horario"] == "invierno" else "invierno"
        self.config["horario"] = nuevo
        guardar_config(self.config)
        self.boton_horario.setText(f"Horario: {nuevo.capitalize()}")

    def abrir_pendientes(self):
        # Intentar pasar parent; si la clase no acepta parent, caer al fallback sin parent
        try:
            ventana = VentanaPendientes(parent=self)
        except TypeError:
            ventana = VentanaPendientes()
        # Preferimos modal si existe exec, si falla usamos show
        try:
            ventana.exec()
        except Exception:
            try:
                ventana.show()
            except Exception:
                pass

    def refrescar(self):
        """Exponer método público para que diálogos hijos puedan pedir refresco del calendario."""
        try:
            self.calendario.refrescar()
        except Exception:
            pass

if __name__ == "__main__":
    app = QApplication([])
    ventana = VentanaPrincipal()
    ventana.show()
    app.exec()
