import streamlit as st
import pandas as pd
from datetime import date
import uuid
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
# CONEXIÓN A GOOGLE SHEETS
# ----------------------------
# Creamos la conexión usando los secretos de Streamlit
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10) # Cache de 10 segundos para que sea rápido
def cargar_productos():
    try:
        df = pd.read_excel("data.xlsx", sheet_name="HOJA 1")
        return df["PRODUCTO"].dropna().astype(str).tolist()
    except Exception:
        return ["Producto de ejemplo"]

PRODUCTOS = cargar_productos()

def cargar_historial():
    try:
        # Leer de la hoja
        df = conn.read(worksheet="Sheet1", ttl=0) # ttl=0 para que siempre traiga datos frescos
        if df.empty:
            return pd.DataFrame(columns=["id", "fecha", "producto", "stock_inicial", "entradas", "salidas", "stock_final"])
        return df
    except Exception as e:
        # Si la hoja está vacía o hay error, devolvemos df vacío
        return pd.DataFrame(columns=["id", "fecha", "producto", "stock_inicial", "entradas", "salidas", "stock_final"])

def guardar_dataframe(df):
    # Escribir todo el DataFrame actualizado en Google Sheets
    conn.update(worksheet="Sheet1", data=df)

# ----------------------------
# LÓGICA DE LA APP (Igual que antes, pero guardando en la nube)
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
        if not historial_actual.empty and 'producto' in historial_actual.columns:
            df_prod = historial_actual[historial_actual["producto"] == producto]
            if not df_prod.empty:
                stock_actual = int(pd.to_numeric(df_prod["stock_final"], errors='coerce').fillna(0).sum())
        
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
            df_actual = cargar_historial()
            entrada_real = entradas
            if actualizar_inicial and nuevo_stock_base != stock_actual:
                entrada_real += (nuevo_stock_base - stock_actual)
            
            nuevo = pd.DataFrame([{
                "id": str(uuid.uuid4()), "fecha": str(fecha), "producto": producto,
                "stock_inicial": stock_actual, "entradas": entrada_real,
                "salidas": salidas, "stock_final": stock_final
            }])
            df_final = pd.concat([df_actual, nuevo], ignore_index=True)
            guardar_dataframe(df_final)
            
            st.success(f"✅ Guardado en Google Sheets para **{producto}**")
            st.balloons()
            st.session_state.form_version += 1
            st.rerun()

# --- PESTAÑA HISTORIAL (Igual que antes, usando cargar_historial y guardar_dataframe) ---
with tab_historial:
    historial = cargar_historial()
    if historial.empty:
        st.info("Aún no hay registros.")
    else:
        # ... (Copia aquí toda la lógica de búsqueda y edición que ya tenías)
        # Solo asegúrate de que al editar/eliminar uses guardar_dataframe(df_actual) al final.
        st.write("Historial cargado correctamente desde Google Sheets.")
        st.dataframe(historial)

# --- PESTAÑA CONSOLIDADO (Igual que antes) ---
with tab_consolidado:
    historial = cargar_historial()
    if not historial.empty:
        # ... (Copia aquí la lógica del groupby que ya tenías)
        st.write("Consolidado generado.")
