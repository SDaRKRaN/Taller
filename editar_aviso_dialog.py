from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QTimeEdit, QComboBox,
    QMessageBox, QVBoxLayout, QDialogButtonBox, QDateEdit
)
from PySide6.QtCore import QTime, QDate
import db

def _es_fecha_valida(s):
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except Exception:
        return False

def _es_hora_valida(s):
    try:
        datetime.strptime(s, "%H:%M")
        return True
    except Exception:
        return False

class EditarAvisoDialog(QDialog):
    def __init__(self, aviso, guardar_callback, parent=None):
        super().__init__(parent)
        self.aviso = aviso.copy() if aviso else {}
        self.guardar_callback = guardar_callback

        if not self.aviso.get("ordenTrabajo") and self.aviso.get("ordenInterna"):
            self.aviso["ordenTrabajo"] = self.aviso.get("ordenInterna")

        self.setWindowTitle(f"Editar aviso {self.aviso.get('ordenTrabajo', '')}")
        self.setModal(True)
        self._build_ui()
        self._load_aviso()

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.form = QFormLayout()
        self.layout.addLayout(self.form)

        self.input_cliente = QLineEdit()
        self.input_direccion = QLineEdit()
        self.input_localidad = QLineEdit()
        self.input_telefono = QLineEdit()
        self.input_proveedor = QLineEdit()

        self.combo_tipoOperacion = QComboBox()
        self.combo_tipoOperacion.addItems(["", "recogida", "entrega", "verificación"])

        self.combo_estado = QComboBox()
        self.combo_estado.addItems(["", "pendiente", "cancelado", "reactivable"])

        self.input_fechaVisita = QDateEdit()
        self.input_fechaVisita.setDisplayFormat("yyyy-MM-dd")
        self.input_fechaVisita.setCalendarPopup(True)

        self.combo_turno = QComboBox()
        self.combo_turno.addItems(["", "mañana", "tarde"])

        self.input_hora_inicio = QTimeEdit()
        self.input_hora_inicio.setDisplayFormat("HH:mm")
        self.input_hora_fin = QTimeEdit()
        self.input_hora_fin.setDisplayFormat("HH:mm")

        self.input_observaciones = QLineEdit()
        self.input_observaciones.setPlaceholderText("Notas internas, detalles del cliente, etc.")

        self.input_cobro = QLineEdit()
        self.input_cobro.setPlaceholderText("Ej: 45.00")

        self.form.addRow("Cliente:", self.input_cliente)
        self.form.addRow("Dirección:", self.input_direccion)
        self.form.addRow("Localidad:", self.input_localidad)
        self.form.addRow("Teléfono:", self.input_telefono)
        self.form.addRow("Proveedor:", self.input_proveedor)
        self.form.addRow("Tipo operación:", self.combo_tipoOperacion)
        self.form.addRow("Estado:", self.combo_estado)
        self.form.addRow("Fecha visita:", self.input_fechaVisita)
        self.form.addRow("Turno:", self.combo_turno)
        self.form.addRow("Hora inicio:", self.input_hora_inicio)
        self.form.addRow("Hora fin:", self.input_hora_fin)
        self.form.addRow("Observaciones:", self.input_observaciones)
        self.form.addRow("Cobro (€):", self.input_cobro)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.on_guardar)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def _load_aviso(self):
        a = self.aviso
        self.input_cliente.setText(a.get("cliente", "") or "")
        self.input_direccion.setText(a.get("direccion", "") or "")
        self.input_localidad.setText(a.get("localidad", "") or "")
        self.input_telefono.setText(a.get("telefono", a.get("telefono1", "")) or "")
        self.input_proveedor.setText(a.get("proveedor", "") or "")
        self.combo_tipoOperacion.setCurrentText(a.get("tipoOperacion", "") or "")
        self.combo_estado.setCurrentText(a.get("estado", "") or "")
        self.input_observaciones.setText(a.get("observaciones", "") or "")
        self.input_cobro.setText(str(a.get("cobro", "")) or "")

        fecha = a.get("fechaVisita")
        if fecha and _es_fecha_valida(fecha):
            y, m, d = map(int, fecha.split("-"))
            self.input_fechaVisita.setDate(QDate(y, m, d))
        else:
            self.input_fechaVisita.setDate(QDate.currentDate())

        self.combo_turno.setCurrentText(a.get("turno", "") or "")

        if a.get("horaInicio"):
            try:
                h, m = map(int, a["horaInicio"].split(":"))
                self.input_hora_inicio.setTime(QTime(h, m))
            except Exception:
                self.input_hora_inicio.setTime(QTime(12, 0))
        else:
            self.input_hora_inicio.setTime(QTime(12, 0))

        if a.get("horaFin"):
            try:
                h, m = map(int, a["horaFin"].split(":"))
                self.input_hora_fin.setTime(QTime(h, m))
            except Exception:
                self.input_hora_fin.setTime(QTime(12, 0))
        else:
            self.input_hora_fin.setTime(QTime(12, 0))

    def _horas_desde_inputs(self):
        hi = self.input_hora_inicio.time().toString("HH:mm")
        hf = self.input_hora_fin.time().toString("HH:mm")
        return hi, hf
    def on_guardar(self):
        cliente = self.input_cliente.text().strip()
        direccion = self.input_direccion.text().strip()
        localidad = self.input_localidad.text().strip()
        telefono = self.input_telefono.text().strip()
        proveedor = self.input_proveedor.text().strip()
        tipoOperacion = self.combo_tipoOperacion.currentText().strip()
        estado = self.combo_estado.currentText().strip()
        observaciones = self.input_observaciones.text().strip()
        cobro_raw = self.input_cobro.text().strip()

        fechaVisita = self.input_fechaVisita.date().toString("yyyy-MM-dd") if self.input_fechaVisita.date().isValid() else None
        turno = self.combo_turno.currentText().strip() or None
        hi, hf = self._horas_desde_inputs()

        if turno and not hi and not hf:
            if turno == "mañana":
                hi, hf = "09:00", "13:00"
            elif turno == "tarde":
                hi, hf = "15:00", "19:00"

        if not fechaVisita:
            estado = "sin asignar"
            turno = None
            hi = None
            hf = None

        if hi and hf and hi >= hf:
            QMessageBox.warning(self, "Validación", "Hora inicio debe ser anterior a hora fin")
            return
        if fechaVisita and not _es_fecha_valida(fechaVisita):
            QMessageBox.warning(self, "Validación", "Fecha visita inválida")
            return
        if hi and not _es_hora_valida(hi):
            QMessageBox.warning(self, "Validación", "Hora inicio inválida")
            return
        if hf and not _es_hora_valida(hf):
            QMessageBox.warning(self, "Validación", "Hora fin inválida")
            return

        if fechaVisita:
            try:
                dia_sem = datetime.strptime(fechaVisita, "%Y-%m-%d").isoweekday()
                if dia_sem in (6, 7):
                    QMessageBox.warning(self, "Validación", "No se permiten asignaciones en fin de semana")
                    return
            except Exception:
                QMessageBox.warning(self, "Validación", "Fecha inválida")
                return

        try:
            cobro = float(cobro_raw) if cobro_raw else None
            if cobro is not None and cobro < 0:
                raise ValueError
        except Exception:
            QMessageBox.warning(self, "Validación", "El campo 'Cobro' debe ser un número positivo")
            return

        identificador = self.aviso.get("ordenTrabajo") or self.aviso.get("ordenInterna")
        if not identificador:
            QMessageBox.critical(self, "Error", "Falta identificador de la orden")
            return

        datos = {
            "ordenTrabajo": identificador,
            "cliente": cliente or None,
            "direccion": direccion or None,
            "localidad": localidad or None,
            "telefono": telefono or None,
            "proveedor": proveedor or None,
            "tipoOperacion": tipoOperacion or None,
            "estado": estado or None,
            "fechaVisita": fechaVisita,
            "turno": turno,
            "horaInicio": hi,
            "horaFin": hf,
            "observaciones": observaciones or None,
            "cobro": cobro
        }

        try:
            self.guardar_callback(datos)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar: {e}")
            return

        try:
            p = self.parent()
            while p is not None:
                if hasattr(p, "calendario") and callable(getattr(p.calendario, "refrescar", None)):
                    try:
                        p.calendario.refrescar()
                    except Exception:
                        pass
                    break
                p = getattr(p, "parent", lambda: None)()
        except Exception:
            pass

        self.accept()
