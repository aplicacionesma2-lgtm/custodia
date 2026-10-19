import streamlit as st
import pandas as pd
from datetime import date
import uuid
import gspread
from google.oauth2.service_account import Credentials

# ----------------------------
# CONFIGURACIÓN Y ESTILOS
# ----------------------------
st.set_page_config(page_title="📦 Control de Custodia", page_icon="📦", layout="centered")

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
# LISTA DE RESPONSABLES
# ----------------------------
RESPONSABLES = [
    "Luis Hora", "Diego Chujutalli", "Nayeli Montes", 
    "Beiker Diaz", "Camila Montalvo", "Oscar Peve", "Ronald Briceño"
]

# ----------------------------
# CONEXIÓN A GOOGLE SHEETS
# ----------------------------
@st.cache_resource
def conectar_sheets():
    creds_dict = dict(st.secrets["connections"]["gsheets"])
    url = creds_dict.pop("spreadsheet", "")
    creds_dict.pop("worksheet", None)
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_url(url)

def obtener_hoja(nombre_hoja, headers):
    spreadsheet = conectar_sheets()
    try:
        return spreadsheet.worksheet(nombre_hoja)
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=nombre_hoja, rows=1000, cols=10)
        sheet.append_row(headers)
        return sheet

# ----------------------------
# CARGA DE DATOS
# ----------------------------
def sincronizar_datos(forzar=False):
    if forzar or "df_historial" not in st.session_state or "lista_productos" not in st.session_state:
        try:
            sheet_prod = obtener_hoja("Productos", ["id", "nombre"])
            records_prod = sheet_prod.get_all_records()
            st.session_state.lista_productos = [str(r["nombre"]).strip() for r in records_prod if "nombre" in r] if records_prod else []

            headers = ["id", "fecha", "producto", "stock_inicial", "entradas", "salidas", "stock_final", "responsable"]
            sheet_hist = obtener_hoja("Sheet1", headers)
            records_hist = sheet_hist.get_all_records()
            
            if records_hist:
                df = pd.DataFrame(records_hist)
                df["producto"] = df["producto"].astype(str).str.strip()
                
                if "responsable" not in df.columns:
                    df["responsable"] = ""
                    
                df["responsable"] = df["responsable"].astype(str).str.strip().replace('', 'Sin asignar')
                df["fecha"] = df["fecha"].astype(str).str.strip()

                for col in ["stock_inicial", "entradas", "salidas", "stock_final"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
                st.session_state.df_historial = df
            else:
                st.session_state.df_historial = pd.DataFrame(columns=headers)
                
            st.success("Datos sincronizados con Google Sheets")
        except Exception as e:
            st.error(f"Error al conectar: {e}")

if "df_historial" not in st.session_state:
    with st.spinner("Conectando con la nube..."):
        sincronizar_datos()

# ----------------------------
# FUNCIONES DE GUARDADO Y EDICIÓN (LA CURA)
# ----------------------------
def guardar_nuevo_registro(fecha, producto, stock_inicial, entradas, salidas, stock_final, responsable):
    try:
        headers = ["id", "fecha", "producto", "stock_inicial", "entradas", "salidas", "stock_final", "responsable"]
        sheet = obtener_hoja("Sheet1", headers)
        nuevo_id = str(uuid.uuid4())
        
        # En lugar de contar filas vacías, usamos los registros reales para saber dónde escribir
        records = sheet.get_all_records()
        ultima_fila_real = len(records) + 2 # +1 por el header, +1 porque empieza en 1
        
        nueva_data = [nuevo_id, str(fecha), producto, int(stock_inicial), int(entradas), int(salidas), int(stock_final), responsable]
        sheet.update(values=[nueva_data], range_name=f"A{ultima_fila_real}:H{ultima_fila_real}")
        
        nuevo_df = pd.DataFrame([{"id": nuevo_id, "fecha": str(fecha), "producto": producto, "stock_inicial": int(stock_inicial), "entradas": int(entradas), "salidas": int(salidas), "stock_final": int(stock_final), "responsable": responsable}])
        st.session_state.df_historial = pd.concat([st.session_state.df_historial, nuevo_df], ignore_index=True)
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

def actualizar_registro(registro_id, fecha, producto, entradas, salidas, stock_final, responsable):
    try:
        sheet = obtener_hoja("Sheet1", [])
        cell = sheet.find(registro_id)
        if cell:
            row = cell.row
            sheet.update_cell(row, 2, str(fecha))
            sheet.update_cell(row, 3, producto)
            sheet.update_cell(row, 5, int(entradas))
            sheet.update_cell(row, 6, int(salidas))
            sheet.update_cell(row, 7, int(stock_final))
            sheet.update_cell(row, 8, responsable) 
            
            idx = st.session_state.df_historial[st.session_state.df_historial["id"] == registro_id].index
            if not idx.empty:
                st.session_state.df_historial.at[idx[0], "fecha"] = str(fecha)
                st.session_state.df_historial.at[idx[0], "producto"] = producto
                st.session_state.df_historial.at[idx[0], "entradas"] = int(entradas)
                st.session_state.df_historial.at[idx[0], "salidas"] = int(salidas)
                st.session_state.df_historial.at[idx[0], "stock_final"] = int(stock_final)
                st.session_state.df_historial.at[idx[0], "responsable"] = responsable
            return True
        return False
    except Exception as e:
        st.error(f"Error al actualizar: {e}")
        return False

def crear_producto(nombre):
    try:
        sheet = obtener_hoja("Productos", ["id", "nombre"])
        sheet.append_row([str(uuid.uuid4()), str(nombre).strip()])
        st.session_state.lista_productos.append(str(nombre).strip())
        return True
    except Exception as e:
        st.error(f"Error al crear producto: {e}")
        return False

def editar_producto(nombre_antiguo, nombre_nuevo):
    try:
        sheet = obtener_hoja("Productos", ["id", "nombre"])
        cell = sheet.find(nombre_antiguo)
        if cell:
            sheet.update_cell(cell.row, 2, nombre_nuevo.strip())
            st.session_state.lista_productos = [nombre_nuevo.strip() if p == nombre_antiguo else p for p in st.session_state.lista_productos]
            return True
        return False
    except Exception as e:
        st.error(f"Error al editar: {e}")
        return False

def eliminar_producto(nombre):
    try:
        sheet = obtener_hoja("Productos", ["id", "nombre"])
        cell = sheet.find(nombre)
        if cell:
            sheet.delete_rows(cell.row)
            st.session_state.lista_productos.remove(nombre)
            return True
        return False
    except Exception as e:
        st.error(f"Error al eliminar: {e}")
        return False

# ----------------------------
# INTERFAZ
# ----------------------------
st.markdown("<h1>📦 Control de Custodia</h1>", unsafe_allow_html=True)

if "form_version" not in st.session_state:
    st.session_state.form_version = 0
v = st.session_state.form_version

if st.button("🔄 Sincronizar / Refrescar datos"):
    sincronizar_datos(forzar=True)
    st.rerun()

tab_registro, tab_historial, tab_consolidado, tab_productos = st.tabs([
    "📝 Registrar", "📜 Historial", "📊 Consolidado", "🛠️ Productos"
])

# --- PESTAÑA REGISTRAR ---
with tab_registro:
    PRODUCTOS = st.session_state.lista_productos
    historial_actual = st.session_state.df_historial
    
    if not PRODUCTOS:
        st.warning("⚠️ No hay productos registrados. Ve a la pestaña '🛠️ Productos' para agregar uno.")
    else:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("📅 Fecha, Producto y Responsable")
            fecha = st.date_input("Selecciona la fecha", value=date.today(), key=f"fecha_{v}")
            producto = st.selectbox("Selecciona el producto", PRODUCTOS, key=f"producto_{v}")
            responsable = st.selectbox("Responsable de la custodia", RESPONSABLES, key=f"resp_{v}")
            
            stock_actual = 0
            if not historial_actual.empty:
                df_prod = historial_actual[historial_actual["producto"] == producto]
                if not df_prod.empty:
                    stock_actual = int(df_prod["stock_final"].sum())
            
            st.info(f"📦 **Stock actual en sistema:** {stock_actual} unidades")
            actualizar_inicial = st.checkbox("🔄 Registrar/Actualizar Stock Inicial (Solo primera vez o correcciones)", key=f"chk_inicial_{v}")
            
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
                stock_inicial_real = nuevo_stock_base if actualizar_inicial else 0
                stock_final_real = stock_actual + (nuevo_stock_base - stock_actual if actualizar_inicial else 0) + entradas - salidas
                
                if guardar_nuevo_registro(fecha, producto, stock_inicial_real, entradas, salidas, stock_final_real, responsable):
                    st.success(f"✅ Guardado para **{producto}** por **{responsable}**")
                    st.balloons()
                    st.session_state.form_version += 1
                    st.rerun()

# --- PESTAÑA HISTORIAL ---
with tab_historial:
    PRODUCTOS = st.session_state.lista_productos
    historial = st.session_state.df_historial

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
                row_gsheets = idx + 2 
                resp_mostrar = row.get('responsable', 'Sin asignar')
                if not resp_mostrar or resp_mostrar == 'nan': 
                    resp_mostrar = "Sin asignar"
                
                with st.expander(f"📅 {row['fecha']} | 📦 {row['producto']} | 👤 {resp_mostrar} | Final: {int(row['stock_final'])}"):
                    st.write(f"**Responsable:** 👤 {resp_mostrar}")
                    st.write(f"**Stock inicial:** {int(row['stock_inicial'])}")
                    st.write(f"**Entradas:** ➕ {int(row['entradas'])}")
                    st.write(f"**Salidas:** ➖ {int(row['salidas'])}")
                    st.write(f"**Stock final:** ✅ {int(row['stock_final'])}")

                    col_edit, col_del = st.columns(2)
                    with col_edit:
                        if st.button("✏️ Editar", key=f"edit_{row['id']}"):
                            st.session_state["editando_id"] = row['id']
                    with col_del:
                        if st.button("🗑️ Eliminar", key=f"del_{row['id']}"):
                            sheet = obtener_hoja("Sheet1", [])
                            sheet.delete_rows(row_gsheets)
                            st.session_state.df_historial = st.session_state.df_historial[st.session_state.df_historial["id"] != row["id"]]
                            st.success("🗑️ Registro eliminado")
                            st.rerun()

                    if st.session_state.get("editando_id") == row['id']:
                        st.markdown("---")
                        st.markdown("### ✏️ Editando Registro")
                        
                        edit_fecha = st.date_input("Fecha", value=pd.to_datetime(row["fecha"]).date(), key=f"ed_fecha_{row['id']}")
                        idx_prod = PRODUCTOS.index(row["producto"]) if row["producto"] in PRODUCTOS else 0
                        edit_producto = st.selectbox("Producto", PRODUCTOS, index=idx_prod, key=f"ed_prod_{row['id']}")
                        
                        idx_resp = RESPONSABLES.index(resp_mostrar) if resp_mostrar in RESPONSABLES else 0
                        edit_responsable = st.selectbox("Responsable", RESPONSABLES, index=idx_resp, key=f"ed_resp_{row['id']}")
                        
                        edit_entradas = st.number_input("Entradas (➕)", min_value=0, step=1, value=int(row["entradas"]), key=f"ed_ent_{row['id']}")
                        edit_salidas = st.number_input("Salidas (➖)", min_value=0, step=1, value=int(row["salidas"]), key=f"ed_sal_{row['id']}")
                        
                        nuevo_final = int(row["stock_inicial"]) + edit_entradas - edit_salidas
                        st.info(f"Nuevo Stock Final calculado: **{nuevo_final}**")

                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.button("💾 Guardar Cambios", key=f"save_{row['id']}"):
                                if nuevo_final < 0:
                                    st.error("El stock final no puede ser negativo.")
                                else:
                                    if actualizar_registro(row['id'], edit_fecha, edit_producto, edit_entradas, edit_salidas, nuevo_final, edit_responsable):
                                        st.success("✅ Registro actualizado en la nube")
                                        st.session_state.pop("editando_id", None)
                                        st.rerun()
                        with col_cancel:
                            if st.button("❌ Cancelar", key=f"cancel_{row['id']}"):
                                st.session_state.pop("editando_id", None)
                                st.rerun()

# --- PESTAÑA CONSOLIDADO ---
with tab_consolidado:
    historial = st.session_state.df_historial
    if not historial.empty:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📊 Resumen Total por Producto")
        
        consolidado = historial.groupby("producto").agg(
            stock_inicial=("stock_inicial", "max"),
            entradas=("entradas", "sum"),
            salidas=("salidas", "sum"),
            stock_final=("stock_final", "last")
        ).reset_index()
        
        consolidado.columns = ["Producto", "Total Inicial", "Total Entradas", "Total Salidas", "Stock Final Actual"]
        consolidado = consolidado.sort_values("Producto")
        consolidado["Stock Final Actual"] = consolidado["Total Inicial"] + consolidado["Total Entradas"] - consolidado["Total Salidas"]
        
        st.dataframe(consolidado, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Aún no hay datos para consolidar.")

# --- PESTAÑA PRODUCTOS ---
with tab_productos:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("➕ Crear Nuevo Producto")
    nuevo_prod = st.text_input("Nombre del producto", key="nuevo_prod_input")
    if st.button("Guardar Producto"):
        if nuevo_prod.strip():
            if nuevo_prod.strip().upper() in [p.upper() for p in st.session_state.lista_productos]:
                st.warning("⚠️ Este producto ya existe.")
            else:
                if crear_producto(nuevo_prod):
                    st.success("✅ Producto creado con éxito.")
                    st.rerun()
        else:
            st.error("El nombre no puede estar vacío.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("⚙️ Administrar Productos")
    productos_actuales = st.session_state.lista_productos
    
    if not productos_actuales:
        st.info("No hay productos para administrar.")
    else:
        prod_seleccionado = st.selectbox("Selecciona un producto", productos_actuales, key="admin_prod")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Editar**")
            nuevo_nombre = st.text_input("Nuevo nombre", value=prod_seleccionado, key="edit_prod_input")
            if st.button("Actualizar Nombre"):
                if nuevo_nombre.strip() and nuevo_nombre.strip() != prod_seleccionado:
                    if editar_producto(prod_seleccionado, nuevo_nombre):
                        st.success("✅ Producto actualizado.")
                        st.rerun()
        with col2:
            st.markdown("**Eliminar**")
            st.write("Esto borrará el producto de la lista.")
            if st.button("🗑️ Eliminar Producto"):
                if eliminar_producto(prod_seleccionado):
                    st.success("🗑️ Producto eliminado.")
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
