
from datetime import datetime
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QFileDialog
from calendario import CalendarioAvisos
from pendientes import VentanaPendientes
from config import cargar_config, guardar_config
import json
import db

def _s(s):
    if s is None:
        return ""
    s = str(s).strip()
    if s.lower() in {"nan", "none", "null"}:
        return ""
    return s

def _bool_from_db(v):
    if v in (1, True, "1", "true", "TRUE", "True", "sí", "si", "SI"):
        return True
    return False

def _normalizar_aviso(av):
    tel1 = _s(av.get("telefono1"))
    tel2 = _s(av.get("telefono2"))
    telefonos = [t for t in (tel1, tel2) if t]
    return {
        "id": av.get("idAviso"),
        "orden": _s(av.get("ordenInterna") or av.get("ordenTrabajo")),
        "cliente": _s(av.get("cliente")),
        "direccion": _s(av.get("direccion")),
        "localidad": _s(av.get("localidad")),
        "cp": _s(av.get("codigoPostal")),
        "telefonos": telefonos,
        "aparato": _s(av.get("aparato")),
        "marca": _s(av.get("marca")),
        "modelo": _s(av.get("modelo")),
        "averia": _s(av.get("averia")),
        "tipoServicio": _s(av.get("tipoServicio")),
        "tipoOperacion": _s(av.get("tipoOperacion")),
        "conCargo": _bool_from_db(av.get("conCargo")),
        "importe": av.get("importe"),
        "metodoPago": _s(av.get("metodoPago")),
        "notas": _s(av.get("observacionesCobro")),  # app móvil leerá este campo
        "estado": _s(av.get("estado")),
        "fechaVisita": _s(av.get("fechaVisita")),
        "turno": _s(av.get("turno")),
        "tecnico": _s(av.get("tecnico")),
        "horaInicio": _s(av.get("horaInicio")),
        "horaFin": _s(av.get("horaFin")),
        "proveedor": _s(av.get("proveedor")),
        "estadoCita": _s(av.get("estadoCita")),
    }

def _agrupar_por_dia_y_turno(avisos):
    dias = {}
    sin_fecha = []
    for av in avisos:
        nav = _normalizar_aviso(av)
        f = nav.get("fechaVisita") or ""
        turno = (nav.get("turno") or "").lower()
        if not f:
            sin_fecha.append(nav)
            continue
        key = "mañana" if turno.startswith("ma") else "tarde" if turno.startswith("ta") else "sin_turno"
        if f not in dias:
            dias[f] = {"mañana": [], "tarde": [], "sin_turno": []}
        dias[f][key].append(nav)
    out = {"dias": dias}
    if sin_fecha:
        out["sin_fecha"] = sin_fecha
    return out

class VentanaPrincipal(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Avisos")
        self.resize(800, 600)

        self.config = cargar_config()

        # Barra superior (horizontal) con botones
        barra = QHBoxLayout()

        self.boton_horario = QPushButton(f"Horario: {self.config['horario'].capitalize()}")
        self.boton_horario.clicked.connect(self.cambiar_horario)
        barra.addWidget(self.boton_horario)

        self.btn_export_json = QPushButton("Exportar → JSON (todos)")
        self.btn_export_json.clicked.connect(self.exportar_json_todos)
        barra.addWidget(self.btn_export_json)

        # Calendario y otros controles
        self.calendario = CalendarioAvisos(parent=self)
        self.boton_asignar = QPushButton("Asignar casos")
        self.boton_asignar.hide()

        self.boton_pendientes = QPushButton("Servicios sin asignar")
        self.boton_pendientes.clicked.connect(self.abrir_pendientes)

        # Layout principal
        layout = QVBoxLayout()
        layout.addLayout(barra)
        layout.addWidget(self.calendario)
        layout.addWidget(self.boton_asignar)
        layout.addWidget(self.boton_pendientes)
        self.setLayout(layout)

        # Señales
        self.calendario.fecha_clicked.connect(self._on_fecha_clicked)
        self.calendario.selectionChanged.connect(self.actualizar_boton)
        self.boton_asignar.clicked.connect(self.asignar)

    def exportar_json_todos(self):
        avisos = db.obtener_todos_los_avisos()
        payload = {
            "version": 1,
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "total": len(avisos),
            **_agrupar_por_dia_y_turno(avisos)
        }
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar todo a JSON", "todas_las_ordenes.json", "JSON (*.json)")
        if not ruta:
            return
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Exportar", f"No se pudo exportar: {e}")
            return
        QMessageBox.information(self, "Exportar", f"Exportado correctamente a\n{ruta}")

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
