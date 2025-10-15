
from PySide6.QtWidgets import QCalendarWidget
from PySide6.QtGui import QTextCharFormat, QColor
from PySide6.QtCore import QDate, Signal
import json
import db  # import del módulo completo para evitar import circular

class CalendarioAvisos(QCalendarWidget):
    """Calendario que colorea días y emite señal con fecha seleccionada al hacer clic."""
    fecha_clicked = Signal(str)  # emite fecha "yyyy-MM-dd" cuando el usuario hace click en un día

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setMinimumDate(QDate.currentDate().addDays(-10))
        self.setMaximumDate(QDate.currentDate().addDays(15))

        # Estructuras internas
        self._fechas_con_avisos_set = set()  # set de strings "yyyy-MM-dd" para lookup rápido
        self.festivos = []

        # Señales para recolorear al cambiar de mes
        try:
            self.currentPageChanged.connect(lambda _y, _m: self.colorear_dias())
        except Exception:
            pass

        self._cargar_datos_iniciales()
        self.colorear_dias()
        self.clicked.connect(self._on_qdate_clicked)

    # ----------------------- Carga de datos -----------------------
    def _cargar_datos_iniciales(self):
        self._cargar_fechas_con_avisos()
        self.festivos = self._cargar_festivos()

    def _cargar_fechas_con_avisos(self):
        """Carga las fechas con avisos. Usa db.obtener_fechas_con_avisos() si existe;
        si no, las calcula desde db.obtener_todos_los_avisos()."""
        fechas = []
        try:
            obtener_fechas = getattr(db, "obtener_fechas_con_avisos", None)
            if callable(obtener_fechas):
                fechas = obtener_fechas() or []
            else:
                # Fallback: derivar a partir de todos los avisos
                fechas = []
                try:
                    for a in db.obtener_todos_los_avisos():
                        f = (a.get("fechaVisita") or "").strip() if a.get("fechaVisita") is not None else ""
                        if f:
                            fechas.append(f)
                except Exception:
                    fechas = []
        except Exception:
            fechas = []
        # Normalizar a set
        self._fechas_con_avisos_set = {str(f).strip() for f in fechas if f}

    def _cargar_festivos(self):
        """Carga lista de fechas festivas desde assets/festivos.json (lista de 'yyyy-MM-dd')."""
        try:
            with open("assets/festivos.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [str(x).strip() for x in data if isinstance(x, str) and x.strip()]
        except Exception:
            pass
        return []

    # ----------------------- API pública -----------------------
    def refrescar(self):
        """Volver a cargar datos desde la base y recolorear el calendario."""
        self._cargar_datos_iniciales()
        self.colorear_dias()
        self.update()

    def fecha_seleccionada(self):
        """Devuelve la fecha seleccionada como string yyyy-MM-dd."""
        return self.selectedDate().toString("yyyy-MM-dd")

    def hay_avisos(self, fecha_str):
        """True si la fecha (yyyy-MM-dd) está en el set de avisos."""
        return fecha_str in self._fechas_con_avisos_set

    def conectar_a_planificador(self, callback):
        """Permite conectar una función (callback(fecha_str)) para abrir el planificador."""
        self.fecha_clicked.connect(callback)

    # ----------------------- Pintado -----------------------
    def colorear_dias(self):
        """Aplica formatos de color a las fechas dentro del rango min/max, según reglas:
        - Festivos y fines de semana -> gris
        - Con avisos -> amarillo
        - Sin avisos -> verde (como antes)
        """
        fmt_reset = QTextCharFormat()

        fmt_festivo = QTextCharFormat()
        fmt_festivo.setBackground(QColor("#d3d3d3"))  # gris claro

        fmt_con_avisos = QTextCharFormat()
        fmt_con_avisos.setBackground(QColor("#ffd700"))  # amarillo dorado

        fmt_sin_avisos = QTextCharFormat()
        fmt_sin_avisos.setBackground(QColor("#C6F6D5"))  # verde suave

        # Limpiar primero el rango visible (usamos min/max fijados)
        visible_start = self.minimumDate()
        visible_end = self.maximumDate()

        # Reset de formato en rango
        fecha = QDate(visible_start)
        while fecha <= visible_end:
            self.setDateTextFormat(fecha, fmt_reset)
            fecha = fecha.addDays(1)

        # Aplicar reglas
        fecha = QDate(visible_start)
        while fecha <= visible_end:
            fecha_str = fecha.toString("yyyy-MM-dd")
            if fecha_str in self.festivos or fecha.dayOfWeek() in (6, 7):
                self.setDateTextFormat(fecha, fmt_festivo)
            elif fecha_str in self._fechas_con_avisos_set:
                self.setDateTextFormat(fecha, fmt_con_avisos)
            else:
                self.setDateTextFormat(fecha, fmt_sin_avisos)
            fecha = fecha.addDays(1)

    # ----------------------- Señales -----------------------
    def _on_qdate_clicked(self, qdate):
        """Manejador cuando el usuario hace click en una fecha del calendario."""
        fecha = qdate.toString("yyyy-MM-dd")
        self.fecha_clicked.emit(fecha)
