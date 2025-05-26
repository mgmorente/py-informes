import jpype
import jpype.imports
from jpype.types import *
import os
from PyPDF2 import PdfMerger
from dotenv import load_dotenv

# Cargar variables desde el archivo .env
load_dotenv()

# --- Configuración desde .env ---
LIB_PATH = os.getenv("LIB_PATH")
OUTPUT_DIR = os.getenv("OUTPUT_DIR")
JASPER_DIR = os.getenv("JASPER_DIR")

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS")
}

# --- Inicializar JVM ---
def start_jvm():
    jar_files = [os.path.join(LIB_PATH, jar) for jar in os.listdir(LIB_PATH) if jar.endswith(".jar")]
    if not jpype.isJVMStarted():
        jpype.startJVM(classpath=jar_files)

# --- Establecer conexión JDBC ---
def connect_db():
    from java.sql import DriverManager
    cfg = DB_CONFIG
    url = f"jdbc:postgresql://{cfg['host']}:{cfg['port']}/{cfg['database']}"
    return DriverManager.getConnection(url, cfg['user'], cfg['password'])

# --- Rellenar informe y exportar a PDF ---
def generar_pdf(jasper_file, params_dict, output_file, conn):
    from java.util import HashMap
    from net.sf.jasperreports.engine import JasperFillManager, JasperExportManager

    params = HashMap()
    for key, value in params_dict.items():
        if value:
            params.put(key, value)

    jasperPrint = JasperFillManager.fillReport(jasper_file, params, conn)
    JasperExportManager.exportReportToPdfFile(jasperPrint, output_file)
    print(f"Generado: {output_file}")

# --- Fusionar PDFs ---
def fusionar_pdfs(pdf_files, output_file):
    merger = PdfMerger()
    for pdf in pdf_files:
        merger.append(pdf)
    merger.write(output_file)
    merger.close()
    print(f"Combinado: {output_file}")

# --- Eliminar archivos temporales ---
def eliminar_archivos(file_list):
    for f in file_list:
        try:
            os.remove(f)
            print(f"Eliminado: {f}")
        except Exception as e:
            print(f"Error eliminando {f}: {e}")

# --- MAIN ---
if __name__ == "__main__":
    start_jvm()
    conn = connect_db()

    informes = [
        {
            "jasper": os.path.join(JASPER_DIR, "LiquidacionColaboradorHistorico.jasper"),
            "params": {
                'filtroSql': "liq.codigo = 91857",
                'nombreTabla': 'liquidacion_col_historico'
            },
            "salida": os.path.join(OUTPUT_DIR, "liquidacion.pdf")
        },
        {
            "jasper": os.path.join(JASPER_DIR, "FacturaRecibida.jasper"),
            "params": {
                'idFactura': 170909
            },
            "salida": os.path.join(OUTPUT_DIR, "factura.pdf")
        }
    ]

    # Generar los informes
    for informe in informes:
        generar_pdf(informe["jasper"], informe["params"], informe["salida"], conn)

    # Combinar PDFs
    salida_final = os.path.join(OUTPUT_DIR, "combinado.pdf")
    fusionar_pdfs([i["salida"] for i in informes], salida_final)

    # Eliminar los PDFs intermedios
    eliminar_archivos([i["salida"] for i in informes])

    jpype.shutdownJVM()
