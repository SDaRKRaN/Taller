import db

print("Probando conexión con la base de datos...")

try:
    avisos = db.obtener_avisos_pendientes()
    print(f"Se encontraron {len(avisos)} avisos pendientes.")
    if avisos:
        print("Primer aviso:")
        print(avisos[0])
    else:
        print("No hay avisos pendientes.")
except Exception as e:
    print("Error al consultar la base de datos:", e)
