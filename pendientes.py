
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QMenu, QMessageBox, QWidget, QLabel, QLineEdit, QComboBox,
    QFileDialog, QDateEdit, QFormLayout, QDialogButtonBox, QInputDialog
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QFontMetrics
import csv
import db
from editar_aviso_dialog import EditarAvisoDialog

def _clean(s):
    s = "" if s is None else str(s).strip()
    return "" if s.lower() in {"nan", "none", "null", "na"} else " ".join(s.split())

def _ellipsize(text: str, metrics: QFontMetrics, max_px: int) -> str:
    try:
        return metrics.elidedText(text, Qt.ElideRight, max_px)
    except Exception:
        return text if len(text) <= 120 else text[:119] + "…"

class VentanaPendientes(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Servicios sin asignar")
        self.resize(900, 600)
        self.layout = QVBoxLayout(self)
        self._build_toolbar()
        self._build_list()
        self._build_footer()
        self._cargar()

    def _build_toolbar(self):
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar por orden, cliente o dirección...")
        self.search.textChanged.connect(self._cargar)
        toolbar.addWidget(self.search)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Todos (oculta anulados)", "")
        self.filter_combo.addItem("sin asignar", "sin asignar")
        self.filter_combo.addItem("pendiente", "pendiente")
        self.filter_combo.addItem("realizado", "realizado")
        self.filter_combo.addItem("anulado", "anulado")
        self.filter_combo.currentIndexChanged.connect(self._cargar)
        toolbar.addWidget(self.filter_combo)

        self.btn_asignar_masivo = QPushButton("Asignar selección")
        self.btn_asignar_masivo.clicked.connect(self._asignar_masivo)
        toolbar.addWidget(self.btn_asignar_masivo)

        self.btn_export = QPushButton("Exportar CSV")
        self.btn_export.clicked.connect(self._exportar_csv)
        toolbar.addWidget(self.btn_export)

        self.btn_refrescar = QPushButton("Refrescar")
        self.btn_refrescar.clicked.connect(self._cargar)
        toolbar.addWidget(self.btn_refrescar)

        self.layout.addLayout(toolbar)

    def _build_list(self):
        self.lista = QListWidget()
        self.lista.setSelectionMode(QListWidget.ExtendedSelection)
        self.lista.itemDoubleClicked.connect(self._on_item_double)
        self.lista.itemActivated.connect(self._on_item_activated)
        self.lista.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lista.customContextMenuRequested.connect(self._menu_contextual)
        self.lista.setUniformItemSizes(True)
        self.lista.setAlternatingRowColors(True)
        self.lista.setStyleSheet("QListWidget { outline: 0; } QListWidget::item { padding: 6px; }")
        self.layout.addWidget(self.lista)

    def _build_footer(self):
        footer = QHBoxLayout()
        self.lbl_count = QLabel("")
        footer.addWidget(self.lbl_count)
        footer.addStretch()
        self.layout.addLayout(footer)

    def _cargar(self):
        self.lista.clear()
        q = (self.search.text() or "").strip().lower()
        estado_filtrado = self.filter_combo.currentData() or ""

        avisos_base = []
        try:
            obtener_sin_fecha = getattr(db, "obtener_avisos_sin_fecha", None)
            if callable(obtener_sin_fecha):
                avisos_base = obtener_sin_fecha()
            else:
                avisos_base = []
                try:
                    pend = db.obtener_avisos_pendientes()
                except Exception:
                    pend = []
                id_vistos = set()
                for a in pend:
                    key = a.get("idAviso") or (a.get("ordenTrabajo") or a.get("ordenInterna"))
                    if key not in id_vistos:
                        avisos_base.append(a); id_vistos.add(key)
                try:
                    todos = db.obtener_todos_los_avisos()
                except Exception:
                    todos = []
                for a in todos:
                    fecha = (_clean(a.get("fechaVisita")))
                    if not fecha:
                        key = a.get("idAviso") or (a.get("ordenTrabajo") or a.get("ordenInterna"))
                        if key not in id_vistos:
                            avisos_base.append(a); id_vistos.add(key)
        except Exception:
            avisos_base = []

        filtrados_estado = []
        for a in avisos_base:
            estado = _clean(a.get("estado")).lower()
            if not estado_filtrado and (estado.startswith("anul") or estado.startswith("canc")):
                continue
            if estado_filtrado and estado != estado_filtrado:
                continue
            filtrados_estado.append(a)

        total_filtrado_pre_busqueda = len(filtrados_estado)

        mostrados = 0
        for aviso in filtrados_estado:
            if aviso.get("ordenTrabajo") is None and aviso.get("ordenInterna"):
                aviso["ordenTrabajo"] = aviso.get("ordenInterna")

            orden = _clean(aviso.get("ordenTrabajo") or aviso.get("ordenInterna"))
            cliente = _clean(aviso.get("cliente"))
            direccion = _clean(aviso.get("direccion"))
            estado = _clean(aviso.get("estado"))
            tipo = _clean(aviso.get("tipoOperacion"))
            telefono = _clean(aviso.get("telefono") or aviso.get("telefono1") or aviso.get("telefono2"))

            if q:
                hay = (q in orden.lower() or q in cliente.lower() or q in direccion.lower()
                       or q in tipo.lower() or q in telefono.lower())
                if not hay:
                    continue

            item_widget = QWidget()
            hl = QHBoxLayout(item_widget); hl.setContentsMargins(8,6,8,6); hl.setSpacing(8)

            vleft = QVBoxLayout()
            lbl_orden = QLabel(orden); f = QFont(); f.setBold(True); f.setPointSize(f.pointSize()+1); lbl_orden.setFont(f)
            vleft.addWidget(lbl_orden)
            lbl_cliente = QLabel(cliente or "sin cliente"); vleft.addWidget(lbl_cliente)
            hl.addLayout(vleft, 3)

            vmid = QVBoxLayout()
            lbl_dir = QLabel(direccion or ""); lbl_dir.setStyleSheet("color:#444;"); vmid.addWidget(lbl_dir)
            meta = f"{(tipo.capitalize() if tipo else '')}  [{estado}]".strip()
            lbl_meta = QLabel(meta); lbl_meta.setStyleSheet("color:#666; font-size:11px;"); vmid.addWidget(lbl_meta)
            hl.addLayout(vmid, 5)

            vright = QVBoxLayout()
            lbl_tel = QLabel(telefono or ""); vright.addWidget(lbl_tel)
            btn_quick = QPushButton("Editar"); btn_quick.setFixedWidth(80)
            btn_quick.clicked.connect(lambda _c, a=aviso: self._abrir_editor(a)); vright.addWidget(btn_quick)

            is_anulado = estado.lower().startswith("anul")
            btn_toggle = QPushButton("Desanular" if is_anulado else "Anular")
            btn_toggle.setFixedWidth(80)
            if is_anulado:
                btn_toggle.clicked.connect(lambda _c, a=aviso: self._desanular_aviso(a))
            else:
                btn_toggle.clicked.connect(lambda _c, a=aviso: self._anular_aviso(a))
            vright.addWidget(btn_toggle)

            hl.addLayout(vright, 2)

            lbl_orden.setText(_ellipsize(lbl_orden.text(), lbl_orden.fontMetrics(), 260))
            lbl_cliente.setText(_ellipsize(lbl_cliente.text(), lbl_cliente.fontMetrics(), 260))
            lbl_dir.setText(_ellipsize(lbl_dir.text(), lbl_dir.fontMetrics(), 520))
            lbl_meta.setText(_ellipsize(lbl_meta.text(), lbl_meta.fontMetrics(), 520))
            lbl_tel.setText(_ellipsize(lbl_tel.text(), lbl_tel.fontMetrics(), 240))

            item = QListWidgetItem()
            h = max(item_widget.sizeHint().height(), 56)
            sz = item_widget.sizeHint(); sz.setHeight(h); item.setSizeHint(sz)
            item.setData(Qt.UserRole, aviso)
            self.lista.addItem(item); self.lista.setItemWidget(item, item_widget)
            mostrados += 1

        self.lbl_count.setText(f"Mostrando {mostrados} de {total_filtrado_pre_busqueda} servicios sin asignar")

    def _on_item_double(self, item):
        if not item: return
        aviso = item.data(Qt.UserRole)
        if aviso: self._abrir_editor(aviso)

    def _on_item_activated(self, item):
        if not item: return
        aviso = item.data(Qt.UserRole)
        if aviso: self._abrir_editor(aviso)

    def _menu_contextual(self, pos):
        item = self.lista.itemAt(pos)
        if not item: return
        aviso = item.data(Qt.UserRole)
        menu = QMenu(self)
        act_editar = menu.addAction("Editar / Reprogramar")
        act_asignar = menu.addAction("Asignar fecha")
        is_anulado = _clean(aviso.get("estado")).lower().startswith("anul")
        act_toggle = menu.addAction("Desanular" if is_anulado else "Anular aviso")
        act_export = menu.addAction("Exportar seleccion")
        accion = menu.exec(self.lista.mapToGlobal(pos))
        if accion == act_editar:
            self._abrir_editor(aviso)
        elif accion == act_asignar:
            self._asignar_individual(aviso)
        elif accion == act_toggle:
            if is_anulado:
                self._desanular_aviso(aviso)
            else:
                self._anular_aviso(aviso)
        elif accion == act_export:
            self._exportar_items([aviso])

    def _anular_aviso(self, aviso):
        if not aviso: return
        identificador = aviso.get("ordenTrabajo") or aviso.get("ordenInterna")
        if not identificador:
            QMessageBox.warning(self, "Anular", "Falta identificador de orden."); return
        motivo, ok = QInputDialog.getText(self, "Anular aviso", "Motivo (opcional):")
        if not ok: return
        resp = QMessageBox.question(self, "Confirmar", f"¿Anular la orden {identificador}?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resp != QMessageBox.Yes: return
        try:
            if hasattr(db, "marcar_anulado") and callable(getattr(db, "marcar_anulado")):
                db.marcar_anulado(identificador, (motivo or "").strip() or None)
            else:
                payload = {"ordenInterna": identificador, "estado": "anulado"}
                mot = (motivo or "").strip()
                if mot:
                    payload["observacionesCobro"] = (aviso.get("observacionesCobro") or "") + f" | Anulado: {mot}"
                db.actualizar_aviso(payload)
            QMessageBox.information(self, "Anulado", f"Orden {identificador} anulada.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo anular: {e}")
        finally:
            self._cargar(); self._notificar_refresco_parent()

    def _desanular_aviso(self, aviso):
        if not aviso: return
        identificador = aviso.get("ordenTrabajo") or aviso.get("ordenInterna")
        if not identificador:
            QMessageBox.warning(self, "Desanular", "Falta identificador de orden."); return
        try:
            if hasattr(db, "marcar_desanulado") and callable(getattr(db, "marcar_desanulado")):
                db.marcar_desanulado(identificador)
            else:
                db.actualizar_aviso({"ordenInterna": identificador, "estado": "pendiente"})
            QMessageBox.information(self, "Desanulado", f"Orden {identificador} desanulada (vuelve a 'pendiente').")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo desanular: {e}")
        finally:
            self._cargar(); self._notificar_refresco_parent()

    def _abrir_editor(self, aviso):
        if aviso.get("ordenTrabajo") is None and aviso.get("ordenInterna"):
            aviso["ordenTrabajo"] = aviso.get("ordenInterna")

        aviso_para_dialogo = dict(aviso)
        obs = aviso.get("observacionesCobro")
        if obs:
            aviso_para_dialogo.setdefault("notas", obs)
            aviso_para_dialogo.setdefault("observaciones", obs)

        def guardar_cb(datos):
            datos = dict(datos)
            # prioridad: notas -> observaciones -> observacionesCobro
            if "notas" in datos and "observacionesCobro" not in datos:
                datos["observacionesCobro"] = datos.pop("notas")
            elif "observaciones" in datos and "observacionesCobro" not in datos:
                datos["observacionesCobro"] = datos.pop("observaciones")
            orden = datos.get("ordenTrabajo") or datos.get("ordenInterna")
            if not orden:
                QMessageBox.critical(self, "Error", "Falta identificador de la orden. No se puede guardar."); return
            try:
                db.actualizar_aviso(datos)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}"); return
            self._cargar(); self._notificar_refresco_parent()

        dlg = EditarAvisoDialog(aviso_para_dialogo, guardar_cb, parent=self)
        dlg.exec()

    def _asignar_individual(self, aviso):
        dlg = QDialog(self); dlg.setWindowTitle("Asignar fecha")
        frm = QFormLayout(dlg)
        date_edit = QDateEdit(); date_edit.setDisplayFormat("yyyy-MM-dd"); date_edit.setCalendarPopup(True); date_edit.setDate(QDate.currentDate())
        combo_turno = QComboBox(); combo_turno.addItems(["", "mañana", "tarde"])
        frm.addRow("Fecha:", date_edit); frm.addRow("Turno:", combo_turno)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); frm.addRow(buttons)
        buttons.accepted.connect(dlg.accept); buttons.rejected.connect(dlg.reject)
        if dlg.exec() != QDialog.Accepted: return
        fecha = date_edit.date().toString("yyyy-MM-dd")
        try:
            dia_sem = datetime.strptime(fecha, "%Y-%m-%d").isoweekday()
            if dia_sem in (6, 7): QMessageBox.warning(self, "Asignar", "No se permiten asignaciones en fines de semana."); return
        except Exception: QMessageBox.warning(self, "Asignar", "Fecha inválida."); return
        turno = combo_turno.currentText() or None
        try:
            db.actualizar_aviso_campos_basicos(
                ordenInterna=aviso.get("ordenTrabajo") or aviso.get("ordenInterna"),
                cliente=None, horaInicio=None, horaFin=None, tecnico=None, turno=turno, fechaVisita=fecha
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo asignar: {e}"); return
        self._cargar(); self._notificar_refresco_parent()

    def _asignar_masivo(self):
        items = self.lista.selectedItems()
        if not items:
            QMessageBox.information(self, "Asignar", "Selecciona uno o más servicios para asignar."); return
        dlg = QDialog(self); dlg.setWindowTitle("Asignar fecha a selección")
        frm = QFormLayout(dlg)
        date_edit = QDateEdit(); date_edit.setDisplayFormat("yyyy-MM-dd"); date_edit.setCalendarPopup(True); date_edit.setDate(QDate.currentDate())
        combo_turno = QComboBox(); combo_turno.addItems(["", "mañana", "tarde"])
        frm.addRow("Fecha:", date_edit); frm.addRow("Turno:", combo_turno)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); frm.addRow(buttons)
        buttons.accepted.connect(dlg.accept); buttons.rejected.connect(dlg.reject)
        if dlg.exec() != QDialog.Accepted: return
        fecha = date_edit.date().toString("yyyy-MM-dd")
        try:
            dia_sem = datetime.strptime(fecha, "%Y-%m-%d").isoweekday()
            if dia_sem in (6, 7): QMessageBox.warning(self, "Asignar", "No se permiten asignaciones en fines de semana."); return
        except Exception: QMessageBox.warning(self, "Asignar", "Fecha inválida."); return
        turno = combo_turno.currentText() or None
        errores = []
        for it in items:
            aviso = it.data(Qt.UserRole); orden_key = aviso.get("ordenTrabajo") or aviso.get("ordenInterna")
            try:
                db.actualizar_aviso_campos_basicos(
                    ordenInterna=orden_key, cliente=None, horaInicio=None, horaFin=None, tecnico=None, turno=turno, fechaVisita=fecha
                )
            except Exception as e:
                errores.append(f"{orden_key}: {e}")
        self._cargar(); self._notificar_refresco_parent()
        if errores:
            QMessageBox.warning(self, "Asignar masivo", "Algunas asignaciones fallaron:\n" + "\n".join(errores))
        else:
            QMessageBox.information(self, "Asignar masivo", "Asignación completada.")

    def _exportar_items(self, avisos):
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar seleccion", "pendientes.csv", "CSV Files (*.csv)")
        if not ruta: return
        try:
            with open(ruta, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["orden", "cliente", "direccion", "telefono", "tipoOperacion", "estado"])
                for aviso in avisos:
                    telefono = _clean(aviso.get("telefono") or aviso.get("telefono1") or aviso.get("telefono2"))
                    w.writerow([
                        _clean(aviso.get("ordenTrabajo") or aviso.get("ordenInterna")),
                        _clean(aviso.get("cliente","")),
                        _clean(aviso.get("direccion","")),
                        telefono,
                        _clean(aviso.get("tipoOperacion","")),
                        _clean(aviso.get("estado",""))
                    ])
            QMessageBox.information(self, "Exportar", "Exportado correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Exportar", f"Error exportando: {e}")

    def _exportar_csv(self):
        avisos = []
        for i in range(self.lista.count()):
            item = self.lista.item(i); aviso = item.data(Qt.UserRole)
            if aviso: avisos.append(aviso)
        if not avisos:
            QMessageBox.information(self, "Exportar", "No hay avisos para exportar."); return
        self._exportar_items(avisos)

    def _notificar_refresco_parent(self):
        try:
            p = self.parent()
            while p is not None:
                if hasattr(p, "refrescar") and callable(p.refrescar):
                    try: p.refrescar()
                    except Exception: pass
                    break
                p = getattr(p, "parent", lambda: None)()
        except Exception: pass
