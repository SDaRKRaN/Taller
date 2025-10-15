
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QWidget, QMenu, QFileDialog, QMessageBox, QApplication,
    QFormLayout, QDateEdit, QComboBox, QTimeEdit, QLineEdit, QFrame, QDialogButtonBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QFontMetrics
import json
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

class PlanificadorDia(QDialog):
    def __init__(self, fecha, parent=None):
        super().__init__(parent)
        self.fecha = fecha
        self.setWindowTitle(f"Planificador {fecha}")
        self.resize(1000, 650)
        self._build_ui()
        self._cargar_avisos()

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        header = QLabel(f"Planificador para {self.fecha}")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-weight:bold; font-size:16px; margin:8px;")
        self.layout.addWidget(header)

        toolbar = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("Buscar por orden, cliente, dirección o técnico...")
        self.search.textChanged.connect(self._cargar_avisos); toolbar.addWidget(self.search)

        self.filter_turno = QComboBox(); self.filter_turno.addItem("Todos los turnos",""); self.filter_turno.addItem("mañana","mañana"); self.filter_turno.addItem("tarde","tarde")
        self.filter_turno.currentIndexChanged.connect(self._cargar_avisos); toolbar.addWidget(self.filter_turno)

        self.filter_tecnico = QComboBox(); self.filter_tecnico.addItem("Todos los técnicos",""); toolbar.addWidget(self.filter_tecnico)

        self.btn_asignar_masivo = QPushButton("Asignar selección"); self.btn_asignar_masivo.clicked.connect(self._asignar_seleccionados); toolbar.addWidget(self.btn_asignar_masivo)
        self.btn_export = QPushButton("Exportar CSV"); self.btn_export.clicked.connect(self._exportar_seleccionados_csv); toolbar.addWidget(self.btn_export)
        self.btn_refrescar = QPushButton("Refrescar"); self.btn_refrescar.clicked.connect(self._cargar_avisos); toolbar.addWidget(self.btn_refrescar)
        self.layout.addLayout(toolbar)

        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setFrameShadow(QFrame.Sunken); self.layout.addWidget(line)

        self.lista = QListWidget()
        self.lista.setSelectionMode(QListWidget.ExtendedSelection)
        self.lista.itemDoubleClicked.connect(self._on_item_double)
        self.lista.itemActivated.connect(self._on_item_activated)
        self.lista.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lista.customContextMenuRequested.connect(self._on_context_menu)
        self.lista.setUniformItemSizes(True)
        self.lista.setAlternatingRowColors(True)
        self.lista.setStyleSheet("QListWidget { outline: 0; } QListWidget::item { padding: 6px; }")
        self.layout.addWidget(self.lista)

        footer = QHBoxLayout()
        self.lbl_count = QLabel("")
        footer.addWidget(self.lbl_count); footer.addStretch()
        self.btn_editar = QPushButton("Editar seleccionado"); self.btn_editar.clicked.connect(self._editar_seleccion); footer.addWidget(self.btn_editar)
        self.btn_exportar = QPushButton("Exportar seleccionados (JSON)"); self.btn_exportar.clicked.connect(self._exportar_seleccionados); footer.addWidget(self.btn_exportar)
        self.layout.addLayout(footer)

    def _cargar_avisos(self):
        self.lista.clear()
        texto = (self.search.text() or "").strip().lower()
        turno_filtrado = self.filter_turno.currentData() or ""
        tecnico_filtrado = self.filter_tecnico.currentData() or ""

        try:
            avisos = db.obtener_avisos_por_fecha(self.fecha)
        except Exception:
            avisos = []

        tecnicos = sorted({(_clean(a.get("tecnico"))) for a in avisos if _clean(a.get("tecnico"))})
        self.filter_tecnico.blockSignals(True); self.filter_tecnico.clear(); self.filter_tecnico.addItem("Todos los técnicos","")
        for t in tecnicos:
            if t: self.filter_tecnico.addItem(t, t)
        self.filter_tecnico.blockSignals(False)

        mostrados = 0
        for aviso in avisos:
            if aviso.get("ordenTrabajo") is None and aviso.get("ordenInterna"):
                aviso["ordenTrabajo"] = aviso.get("ordenInterna")

            orden = _clean(aviso.get("ordenTrabajo") or aviso.get("ordenInterna"))
            cliente = _clean(aviso.get("cliente"))
            direccion = _clean(aviso.get("direccion"))
            hi = _clean(aviso.get("horaInicio")); hf = _clean(aviso.get("horaFin"))
            turno = _clean(aviso.get("turno")); tecnico = _clean(aviso.get("tecnico"))
            estado = _clean(aviso.get("estado")); tipoOperacion = _clean(aviso.get("tipoOperacion"))
            telefono = _clean(aviso.get("telefono") or aviso.get("telefono1") or aviso.get("telefono2"))

            if turno_filtrado and turno_filtrado != turno: continue
            if tecnico_filtrado and tecnico_filtrado != tecnico: continue
            if texto:
                hay = (texto in orden.lower() or texto in cliente.lower() or texto in direccion.lower()
                       or texto in tecnico.lower() or texto in tipoOperacion.lower() or texto in (telefono or "").lower())
                if not hay: continue

            item_widget = QWidget(); hl = QHBoxLayout(item_widget); hl.setContentsMargins(8,6,8,6); hl.setSpacing(8)
            vleft = QVBoxLayout(); lbl_orden = QLabel(orden or ""); f = QFont(); f.setBold(True); f.setPointSize(f.pointSize()+1); lbl_orden.setFont(f); vleft.addWidget(lbl_orden)
            lbl_cliente = QLabel(cliente or "sin cliente"); vleft.addWidget(lbl_cliente); hl.addLayout(vleft, 2)

            vmid = QVBoxLayout()
            lbl_dir = QLabel(direccion or ""); lbl_dir.setStyleSheet("color:#444;"); vmid.addWidget(lbl_dir)
            meta_parts = []
            if tipoOperacion: meta_parts.append(tipoOperacion.capitalize())
            if estado: meta_parts.append(estado.capitalize())
            if turno or hi or hf: meta_parts.append(f"{turno} {hi}–{hf}".strip())
            if tecnico: meta_parts.append(f"T: {tecnico}")
            if telefono: meta_parts.append(f"Tel: {telefono}")
            lbl_meta = QLabel(" | ".join(meta_parts)); lbl_meta.setStyleSheet("color:#666; font-size:11px;"); vmid.addWidget(lbl_meta); hl.addLayout(vmid, 6)

            vright = QVBoxLayout()
            btn_quick = QPushButton("Editar"); btn_quick.setFixedWidth(80); btn_quick.clicked.connect(lambda _c, a=aviso: self._abrir_editor(a)); vright.addWidget(btn_quick)
            btn_ok = QPushButton("Realizado"); btn_ok.setFixedWidth(80); btn_ok.clicked.connect(lambda _c, a=aviso: self._marcar_realizado(a)); vright.addWidget(btn_ok)
            btn_desasignar = QPushButton("Desasignar"); btn_desasignar.setFixedWidth(80); btn_desasignar.clicked.connect(lambda _c, a=aviso: self._desasignar_aviso(a)); vright.addWidget(btn_desasignar)
            hl.addLayout(vright, 1)

            lbl_orden.setText(_ellipsize(lbl_orden.text(), lbl_orden.fontMetrics(), 260))
            lbl_cliente.setText(_ellipsize(lbl_cliente.text(), lbl_cliente.fontMetrics(), 260))
            lbl_dir.setText(_ellipsize(lbl_dir.text(), lbl_dir.fontMetrics(), 520))
            lbl_meta.setText(_ellipsize(lbl_meta.text(), lbl_meta.fontMetrics(), 520))

            item = QListWidgetItem(); h = max(item_widget.sizeHint().height(), 56); sz = item_widget.sizeHint(); sz.setHeight(h); item.setSizeHint(sz)
            item.setData(Qt.UserRole, aviso); self.lista.addItem(item); self.lista.setItemWidget(item, item_widget)
            mostrados += 1

        self.lbl_count.setText(f"Mostrando {mostrados} de {len(avisos)} avisos ({self.fecha})")

    def _get_selected_aviso_dicts(self):
        return [it.data(Qt.UserRole) for it in self.lista.selectedItems()]

    def _on_item_double(self, item):
        aviso = item.data(Qt.UserRole)
        if aviso: self._abrir_editor(aviso)

    def _on_item_activated(self, item):
        aviso = item.data(Qt.UserRole)
        if aviso: self._abrir_editor(aviso)

    def _editar_seleccion(self):
        items = self._get_selected_aviso_dicts()
        if not items: QMessageBox.information(self, "Editar", "Selecciona al menos un aviso"); return
        self._abrir_editor(items[0])

    def _abrir_editor(self, aviso):
        if aviso.get("ordenTrabajo") is None and aviso.get("ordenInterna"):
            aviso["ordenTrabajo"] = aviso.get("ordenInterna")

        aviso_para_dialogo = dict(aviso)
        obs = aviso.get("observacionesCobro")
        if obs:
            aviso_para_dialogo.setdefault("notas", obs)
            aviso_para_dialogo.setdefault("observaciones", obs)
        if False:
            aviso_para_dialogo["notas"] = aviso.get("observacionesCobro")

        def guardar_cb(datos):
            merged = aviso.copy(); merged.update(datos)
            if "ordenTrabajo" in merged and "ordenInterna" not in merged:
                merged["ordenInterna"] = merged["ordenTrabajo"]
            # Mapear 'notas' -> 'observacionesCobro' si viene del diálogo
            if "notas" in merged and "observacionesCobro" not in merged:
                merged["observacionesCobro"] = merged.pop("notas")
            elif "observaciones" in merged and "observacionesCobro" not in merged:
                merged["observacionesCobro"] = merged.pop("observaciones")
            try:
                db.actualizar_aviso(merged)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error guardando aviso: {e}"); return
            self._cargar_avisos(); self._notificar_refresco_parent()

        dlg = EditarAvisoDialog(aviso_para_dialogo, guardar_cb, parent=self)
        dlg.exec()

    def _asignar_seleccionados(self):
        items = self._get_selected_aviso_dicts()
        if not items:
            QMessageBox.information(self, "Asignar", "Selecciona avisos para asignar"); return

        dlg = QDialog(self); dlg.setWindowTitle("Asignar a seleccionados")
        form = QFormLayout(dlg)
        date_edit = QDateEdit(QDate.fromString(self.fecha, "yyyy-MM-dd")); date_edit.setDisplayFormat("yyyy-MM-dd"); date_edit.setCalendarPopup(True)
        combo_turno = QComboBox(); combo_turno.addItems(["", "mañana", "tarde"])
        time_inicio = QTimeEdit(); time_inicio.setDisplayFormat("HH:mm")
        time_fin = QTimeEdit(); time_fin.setDisplayFormat("HH:mm")
        form.addRow("Fecha:", date_edit); form.addRow("Turno:", combo_turno)
        form.addRow("Hora inicio (opcional):", time_inicio); form.addRow("Hora fin (opcional):", time_fin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); form.addRow(buttons)
        buttons.accepted.connect(dlg.accept); buttons.rejected.connect(dlg.reject)

        if dlg.exec() != QDialog.Accepted: return

        fecha_nueva = date_edit.date().toString("yyyy-MM-dd")
        try:
            dia_sem = datetime.strptime(fecha_nueva, "%Y-%m-%d").isoweekday()
            if dia_sem in (6, 7): QMessageBox.warning(self, "Asignar", "No se permiten asignaciones en fines de semana (sábado o domingo)."); return
        except Exception: QMessageBox.warning(self, "Asignar", "Fecha inválida."); return

        turno = combo_turno.currentText() or None
        hi = time_inicio.time().toString("HH:mm") if time_inicio.time().isValid() else None
        hf = time_fin.time().toString("HH:mm") if time_fin.time().isValid() else None

        errores = []
        for aviso in items:
            try:
                orden_key = aviso.get("ordenTrabajo") or aviso.get("ordenInterna")
                db.actualizar_aviso_campos_basicos(
                    ordenInterna=orden_key, cliente=None, horaInicio=hi, horaFin=hf, tecnico=None, turno=turno, fechaVisita=fecha_nueva
                )
            except Exception as e:
                errores.append(f"{orden_key}: {e}")

        self._cargar_avisos(); self._notificar_refresco_parent()
        if errores:
            QMessageBox.warning(self, "Asignar", "Algunos avisos no se actualizaron:\n" + "\n".join(errores))
        else:
            QMessageBox.information(self, "Asignar", "Asignación completada")

    def _exportar_seleccionados(self):
        items = self._get_selected_aviso_dicts()
        if not items: QMessageBox.information(self, "Exportar", "Selecciona avisos para exportar"); return
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar a JSON", "export_aviso.json", "JSON Files (*.json)")
        if not ruta: return
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Exportar", f"Exportados {len(items)} avisos a {ruta}")
        except Exception as e:
            QMessageBox.critical(self, "Exportar", f"Error exportando: {e}")

    def _exportar_seleccionados_csv(self):
        items = self._get_selected_aviso_dicts()
        if not items: QMessageBox.information(self, "Exportar", "Selecciona avisos para exportar"); return
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar a CSV", "planificador.csv", "CSV Files (*.csv)")
        if not ruta: return
        try:
            with open(ruta, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["orden", "cliente", "direccion", "horaInicio", "horaFin", "turno", "tecnico", "telefono", "estado", "tipoOperacion"])
                for aviso in items:
                    w.writerow([
                        _clean(aviso.get("ordenTrabajo") or aviso.get("ordenInterna")),
                        _clean(aviso.get("cliente","")),
                        _clean(aviso.get("direccion","")),
                        _clean(aviso.get("horaInicio","")),
                        _clean(aviso.get("horaFin","")),
                        _clean(aviso.get("turno","")),
                        _clean(aviso.get("tecnico","")),
                        _clean(aviso.get("telefono") or aviso.get("telefono1","") or aviso.get("telefono2","")),
                        _clean(aviso.get("estado","")),
                        _clean(aviso.get("tipoOperacion",""))
                    ])
            QMessageBox.information(self, "Exportar", "Exportado correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Exportar", f"Error exportando: {e}")

    def _on_context_menu(self, pos):
        item = self.lista.itemAt(pos)
        if not item: return
        aviso = item.data(Qt.UserRole)
        menu = QMenu(self)
        act_editar = menu.addAction("Editar")
        act_asignar = menu.addAction("Asignar")
        act_marcar_ok = menu.addAction("Marcar como realizado")
        act_copiar_dir = menu.addAction("Copiar dirección")
        act_desasignar = menu.addAction("Desasignar")
        accion = menu.exec(self.lista.mapToGlobal(pos))
        if accion == act_editar:
            self._abrir_editor(aviso)
        elif accion == act_asignar:
            self.lista.clearSelection(); row = self.lista.row(item); self.lista.item(row).setSelected(True)
            self._asignar_seleccionados()
        elif accion == act_marcar_ok:
            try:
                orden_key = aviso.get("ordenTrabajo") or aviso.get("ordenInterna")
                try:
                    db.marcar_realizado(orden_key)
                except Exception:
                    aviso_copy = aviso.copy(); aviso_copy["estado"] = "realizado"; db.actualizar_aviso(aviso_copy)
                self._cargar_avisos(); self._notificar_refresco_parent()
            except Exception: pass
        elif accion == act_copiar_dir:
            clipboard = QApplication.clipboard(); clipboard.setText(aviso.get("direccion", "") or "")
        elif accion == act_desasignar:
            self._desasignar_aviso(aviso)

    def _desasignar_aviso(self, aviso):
        if not aviso: return
        identificador = aviso.get("ordenTrabajo") or aviso.get("ordenInterna")
        if not identificador:
            QMessageBox.critical(self, "Desasignar", "Falta identificador de la orden. No se puede desasignar."); return
        confirm = QMessageBox.question(self, "Desasignar", f"¿Deseas devolver la orden {identificador} a 'sin asignar'?\nSe eliminará la fecha y la asignación.")
        if confirm != QMessageBox.Yes: return
        try:
            aviso_copy = aviso.copy()
            for k in ("fechaVisita","turno","horaInicio","horaFin","tecnico"): aviso_copy[k] = None
            aviso_copy["estado"] = "sin asignar"
            try:
                db.actualizar_aviso(aviso_copy)
            except Exception:
                try:
                    db.actualizar_aviso_campos_basicos(
                        ordenInterna=identificador, cliente=None, horaInicio=None, horaFin=None, tecnico=None, turno=None, fechaVisita=None
                    )
                    aviso_estado = {"ordenTrabajo": identificador, "estado": "sin asignar"}
                    try: db.actualizar_aviso(aviso_estado)
                    except Exception: pass
                except Exception: pass
            QMessageBox.information(self, "Desasignar", f"Orden {identificador} devuelta a sin asignar.")
        except Exception as e:
            QMessageBox.critical(self, "Desasignar", f"No se pudo desasignar: {e}")
        finally:
            self._cargar_avisos(); self._notificar_refresco_parent()

    def _marcar_realizado(self, aviso):
        try:
            orden_key = aviso.get("ordenTrabajo") or aviso.get("ordenInterna")
            db.marcar_realizado(orden_key)
        except Exception:
            aviso_copy = aviso.copy(); aviso_copy["estado"] = "realizado"
            try: db.actualizar_aviso(aviso_copy)
            except Exception: pass
        self._cargar_avisos(); self._notificar_refresco_parent()

    def _notificar_refresco_parent(self):
        try:
            p = self.parent()
            while p is not None:
                if hasattr(p, "calendario") and callable(getattr(p.calendario, "refrescar", None)):
                    try: p.calendario.refrescar()
                    except Exception: pass
                    break
                p = getattr(p, "parent", lambda: None)()
        except Exception: pass

def abrir_planificador(fecha, parent=None):
    dlg = PlanificadorDia(fecha, parent=parent); dlg.exec(); return dlg
