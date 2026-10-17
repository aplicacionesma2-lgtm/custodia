import streamlit as st
import pandas as pd
from datetime import date
import uuid
import gspread
from google.oauth2.service_account import Credentials
from streamlit_gsheets import GSheetsConnection

# ----------------------------
# CONFIGURACIÓN Y ESTILOS
# ----------------------------
st.set_page_config(page_title="📦 Control de Stock", page_icon="📦", layout="centered")

st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    .card { background-color: white; padding: 1.2rem; border-radius: 1.2rem; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 1rem; }
    h1, h2, h3 { color: #2c3e50; text-align: center; }
    .stButton > button { background-color: #ff6b6b; color: white; border-radius: 2rem; padding: 0.6rem 1.5rem; font-weight: bold; border: none; width: 100%; }
    .stButton > button:hover { background-color: #ee5a24; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ----------------------------
# CONEXIÓN A GOOGLE SHEETS (Vía gspread directo)
# ----------------------------
@st.cache_resource
def conectar_sheets():
    # Leemos las credenciales desde los secrets de Streamlit Cloud
    creds_dict = dict(st.secrets["connections"]["gsheets"])
    # El spreadsheet de los secrets (URL)
    url = creds_dict.pop("spreadsheet", "")
    # Limpiamos el diccionario para que Credentials no se queje de llaves extra
    creds_dict.pop("worksheet", None)
    
    # Autenticación
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    # Abrimos el archivo de Google Sheets
    spreadsheet = client.open_by_url(url)
    
    try:
        # Buscamos la pestaña "Sheet1" (así se llama en tu captura)
        sheet = spreadsheet.worksheet("Sheet1")
    except gspread.exceptions.WorksheetNotFound:
        # Si por alguna razón no existe, la crea y le pone los encabezados
        sheet = spreadsheet.add_worksheet(title="Sheet1", rows=1000, cols=10)
        sheet.append_row(["id", "fecha", "producto", "stock_inicial", "entradas", "salidas", "stock_final"])
    
    return sheet

# ----------------------------
# CARGA DE PRODUCTOS DESDE EXCEL
# ----------------------------
@st.cache_data
def cargar_productos():
    try:
        df = pd.read_excel("data.xlsx", sheet_name="HOJA 1")
        return df["PRODUCTO"].dropna().astype(str).str.strip().tolist()
    except Exception as e:
        return ["Producto de ejemplo"]

PRODUCTOS = cargar_productos()

# ----------------------------
# FUNCIONES DE HISTORIAL CON GSPREAD
# ----------------------------
def cargar_historial():
    try:
        sheet = conectar_sheets()
        # Traemos todos los registros como lista de diccionarios
        records = sheet.get_all_records()
        if not records:
            return pd.DataFrame(columns=["id", "fecha", "producto", "stock_inicial", "entradas", "salidas", "stock_final"])
        
        df = pd.DataFrame(records)
        # Aseguramos que las columnas numéricas sean números y los textos sean textos limpios
        df["producto"] = df["producto"].astype(str).str.strip()
        df["stock_inicial"] = pd.to_numeric(df["stock_inicial"], errors="coerce").fillna(0).astype(int)
        df["entradas"] = pd.to_numeric(df["entradas"], errors="coerce").fillna(0).astype(int)
        df["salidas"] = pd.to_numeric(df["salidas"], errors="coerce").fillna(0).astype(int)
        df["stock_final"] = pd.to_numeric(df["stock_final"], errors="coerce").fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"Error al leer Google Sheets: {e}")
        return pd.DataFrame(columns=["id", "fecha", "producto", "stock_inicial", "entradas", "salidas", "stock_final"])

def guardar_nuevo_registro(fecha, producto, stock_inicial, entradas, salidas, stock_final):
    try:
        sheet = conectar_sheets()
        # Agrega una fila nueva al final de la hoja
        sheet.append_row([str(uuid.uuid4()), str(fecha), producto, int(stock_inicial), int(entradas), int(salidas), int(stock_final)])
    except Exception as e:
        st.error(f"Error al guardar en Google Sheets: {e}")

def actualizar_registro_existente(row_index, df_actual):
    try:
        sheet = conectar_sheets()
        # Convertimos el dataframe de nuevo a lista de listas (incluyendo encabezados)
        # row_index es el número de fila en Google Sheets (1 es el encabezado, 2 es el primer dato)
        data = [df_actual.columns.values.tolist()] + df_actual.values.tolist()
        sheet.update(values=data, range_name=f"A1:G{len(data)}")
    except Exception as e:
        st.error(f"Error al actualizar Google Sheets: {e}")

# ----------------------------
# LÓGICA DE LA APP
# ----------------------------
if "form_version" not in st.session_state:
    st.session_state.form_version = 0
v = st.session_state.form_version

st.markdown("<h1>📦 Control de Stock</h1>", unsafe_allow_html=True)
tab_registro, tab_historial, tab_consolidado = st.tabs(["📝 Registrar", "📜 Historial", "📊 Consolidado"])

# --- PESTAÑA REGISTRAR ---
with tab_registro:
    historial_actual = cargar_historial()
    
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📅 Fecha y Producto")
        fecha = st.date_input("Selecciona la fecha", value=date.today(), key=f"fecha_{v}")
        producto = st.selectbox("Selecciona el producto", PRODUCTOS, key=f"producto_{v}")
        
        stock_actual = 0
        if not historial_actual.empty:
            # Filtramos por el producto
            df_prod = historial_actual[historial_actual["producto"] == producto.strip()]
            if not df_prod.empty:
                stock_actual = int(df_prod["stock_final"].sum())
        
        st.info(f"📦 **Stock actual en sistema:** {stock_actual} unidades")
        actualizar_inicial = st.checkbox("🔄 Registrar/Actualizar Stock Inicial", key=f"chk_inicial_{v}")
        
        nuevo_stock_base = stock_actual
        if actualizar_inicial:
            nuevo_stock_base = st.number_input("Escribe la cantidad física real:", min_value=0, step=1, value=stock_actual, key=f"stock_base_{v}")
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📊 Movimientos del día")
        entradas = st.number_input("Entradas (➕)", min_value=0, step=1, value=0, key=f"entradas_{v}")
        salidas = st.number_input("Salidas (➖)", min_value=0, step=1, value=0, key=f"salidas_{v}")
        stock_final = nuevo_stock_base + entradas - salidas
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("✅ Stock Final Proyectado")
    st.metric(label="Resultado", value=f"{stock_final} unidades")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("💾 Guardar registro en la nube"):
        if stock_final < 0:
            st.error(f"🚨 ¡Ojo! Tienes {nuevo_stock_base} y quieres sacar {salidas}.")
        elif entradas == 0 and salidas == 0 and not actualizar_inicial:
            st.warning("⚠️ No hay movimientos que guardar.")
        else:
            entrada_real = entradas
            if actualizar_inicial and nuevo_stock_base != stock_actual:
                entrada_real += (nuevo_stock_base - stock_actual)
            
            guardar_nuevo_registro(fecha, producto, stock_actual, entrada_real, salidas, stock_final)
            
            st.success(f"✅ Guardado en Google Sheets para **{producto}**")
            st.balloons()
            st.session_state.form_version += 1
            st.rerun()

# --- PESTAÑA HISTORIAL ---
with tab_historial:
    historial = cargar_historial()

    if historial.empty:
        st.info("Aún no hay registros.")
    else:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("🔍 Buscar registros")
            col1, col2 = st.columns(2)
            with col1:
                fecha_busqueda = st.date_input("Buscar por fecha", value=None, key="buscar_fecha")
            with col2:
                prod_busqueda = st.selectbox("Buscar por producto", ["Todos"] + PRODUCTOS, key="buscar_prod")
            st.markdown('</div>', unsafe_allow_html=True)

        filtrado = historial.copy()
        if fecha_busqueda is not None:
            filtrado = filtrado[filtrado["fecha"] == str(fecha_busqueda)]
        if prod_busqueda != "Todos":
            filtrado = filtrado[filtrado["producto"] == prod_busqueda]

        if filtrado.empty:
            st.warning("🔎 No se encontraron registros con esos filtros.")
        else:
            filtrado = filtrado.sort_values("fecha", ascending=False)
            st.markdown(f"**{len(filtrado)} registro(s) encontrado(s)**")

            for idx, row in filtrado.iterrows():
                # El índice real en la hoja de cálculo es idx + 2 (1 por el header, 1 por índice 0)
                row_gsheets = idx + 2 
                
                with st.expander(f"📅 {row['fecha']} | 📦 {row['producto']} | Final: {int(row['stock_final'])}"):
                    st.write(f"**Stock inicial:** {int(row['stock_inicial'])}")
                    st.write(f"**Entradas:** ➕ {int(row['entradas'])}")
                    st.write(f"**Salidas:** ➖ {int(row['salidas'])}")
                    st.write(f"**Stock final:** ✅ {int(row['stock_final'])}")

                    # EDICIÓN Y ELIMINACIÓN (Para no hacer el código eterno, usaremos actualización por lote)
                    if st.button("🗑️ Eliminar este registro", key=f"del_{row['id']}"):
                        sheet = conectar_sheets()
                        sheet.delete_rows(row_gsheets)
                        st.success("🗑️ Registro eliminado")
                        st.rerun()

# --- PESTAÑA CONSOLIDADO ---
with tab_consolidado:
    historial = cargar_historial()
    if not historial.empty:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📊 Resumen Total por Producto")
        
        consolidado = historial.groupby("producto", as_index=False).agg({
            "stock_inicial": "sum",
            "entradas": "sum",
            "salidas": "sum",
            "stock_final": "sum"
        })
        
        consolidado.columns = ["Producto", "Total Inicial", "Total Entradas", "Total Salidas", "Stock Final Actual"]
        consolidado = consolidado.sort_values("Producto")
        
        st.dataframe(consolidado, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Aún no hay datos para consolidar.")
