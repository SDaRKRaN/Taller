from flask import Flask, render_template, request, redirect
import pandas as pd
import sqlite3

app = Flask(__name__)

DB_PATH = "avisos.db"
EXCEL_PATH = "RutasDatos.xlsx"

# 🔧 Asegura que la tabla existe
def asegurar_tabla():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS avisos (
        idAviso INTEGER PRIMARY KEY AUTOINCREMENT,
        ordenInterna TEXT UNIQUE,
        cliente TEXT,
        direccion TEXT,
        localidad TEXT,
        codigoPostal TEXT,
        telefono1 TEXT,
        telefono2 TEXT,
        aparato TEXT,
        marca TEXT,
        modelo TEXT,
        fechaAsignacion TEXT,
        averia TEXT,
        tipoServicio TEXT,
        conCargo BOOLEAN,
        importe REAL,
        metodoPago TEXT,
        observacionesCobro TEXT,
        estado TEXT,
        fechaVisita TEXT,
        tecnico TEXT,
        turno TEXT
    );
    """)
    conn.commit()
    conn.close()

# 🔍 Verifica si el aviso ya existe
def verificar_duplicado(orden):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM avisos WHERE ordenInterna = ?", (str(orden),))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

# 📋 Carga y marca duplicados
def cargar_excel():
    asegurar_tabla()
    df = pd.read_excel(EXCEL_PATH)
    df['duplicado'] = df['reparacion'].apply(verificar_duplicado)
    return df.to_dict(orient='records')

# 🏠 Página principal con filtros
@app.route("/")
def index():
    localidad = request.args.get("localidad", "").lower()
    tecnico = request.args.get("tecnico", "").lower()
    avisos = cargar_excel()

    if localidad:
        avisos = [a for a in avisos if localidad in a['LOCALIDAD'].lower()]
    if tecnico:
        avisos = [a for a in avisos if tecnico in str(a.get('tecnico', '')).lower()]

    return render_template("index.html", avisos=avisos)

# 📥 Importación de avisos seleccionados
@app.route("/importar", methods=["POST"])
def importar():
    seleccionados = request.form.getlist("seleccion")
    df = pd.read_excel(EXCEL_PATH)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for _, row in df.iterrows():
        if str(row['reparacion']) in seleccionados:
            try:
                cursor.execute("""
                    INSERT INTO avisos (
                        ordenInterna, cliente, direccion, localidad, codigoPostal,
                        telefono1, telefono2, aparato, marca, modelo,
                        fechaAsignacion, averia, tipoServicio, conCargo, importe,
                        metodoPago, observacionesCobro, estado, fechaVisita, tecnico, turno
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(row['reparacion']),
                    f"{row['NOMBRE']} {row.get('apel1', '')}",
                    row['DIRECCION'], row['LOCALIDAD'], str(row['CODIGOPOSTAL']),
                    str(row['TELE1']), str(row.get('TELE2', '')),
                    str(row['aparato']), row['marca'], row['modelo'],
                    str(row['fecha1']), row['averia2'],
                    "Recogida", 0, None, None, None,
                    "pendiente", "", "", ""
                ))
            except sqlite3.IntegrityError:
                pass

    conn.commit()
    conn.close()
    return redirect("/")

# 📝 Ficha editable por aviso (desde base de datos)
@app.route("/editar/<orden>")
def editar(orden):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM avisos WHERE ordenInterna = ?", (str(orden),))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return f"Aviso {orden} no encontrado en la base de datos", 404

    columnas = [desc[0] for desc in cursor.description]
    aviso = dict(zip(columnas, row))
    conn.close()
    return render_template("editar.html", aviso=aviso)

# 💾 Guardar cambios en la base
@app.route("/guardar/<orden>", methods=["POST"])
def guardar(orden):
    cliente = request.form.get("cliente")
    direccion = request.form.get("direccion")
    localidad = request.form.get("localidad")
    aparato = request.form.get("aparato")
    marca = request.form.get("marca")
    modelo = request.form.get("modelo")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE avisos SET
            cliente = ?, direccion = ?, localidad = ?,
            aparato = ?, marca = ?, modelo = ?
        WHERE ordenInterna = ?
    """, (cliente, direccion, localidad, aparato, marca, modelo, str(orden)))
    conn.commit()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
