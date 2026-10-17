import streamlit as st
import pandas as pd
from datetime import date
import os
import uuid

# ----------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ----------------------------
st.set_page_config(
    page_title="📦 Control de Stock",
    page_icon="📦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ----------------------------
# ESTILOS PERSONALIZADOS (MÓVIL)
# ----------------------------
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    .card {
        background-color: white; padding: 1.2rem; border-radius: 1.2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 1rem;
    }
    h1, h2, h3 { color: #2c3e50; text-align: center; }
    .stButton > button {
        background-color: #ff6b6b; color: white; border-radius: 2rem;
        padding: 0.6rem 1.5rem; font-weight: bold; border: none;
        width: 100%; transition: 0.3s;
    }
    .stButton > button:hover { background-color: #ee5a24; transform: scale(1.02); }
    .stTextInput, .stNumberInput, .stDateInput, .stSelectbox { border-radius: 1rem !important; }
    .stMetric {
        background-color: #ffffffcc; border-radius: 1rem; padding: 0.8rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ----------------------------
# CARGA DE PRODUCTOS DESDE EXCEL
# ----------------------------
@st.cache_data
def cargar_productos():
    try:
        df = pd.read_excel("data.xlsx", sheet_name="HOJA 1")
        return df["PRODUCTO"].dropna().astype(str).tolist()
    except Exception as e:
        return ["Producto de ejemplo"]

PRODUCTOS = cargar_productos()

# ----------------------------
# GESTIÓN DEL ARCHIVO DE HISTORIAL
# ----------------------------
ARCHIVO = "historial_stock.csv"
COLUMNAS = ["id", "fecha", "producto", "stock_inicial", "entradas", "salidas", "stock_final"]

def cargar_historial():
    if os.path.exists(ARCHIVO):
        df = pd.read_csv(ARCHIVO)
        if "id" not in df.columns:
            df["id"] = [str(uuid.uuid4()) for _ in range(len(df))]
            df.to_csv(ARCHIVO, index=False)
        return df
    else:
        return pd.DataFrame(columns=COLUMNAS)

def guardar_dataframe(df):
    df.to_csv(ARCHIVO, index=False)

# ----------------------------
# INICIALIZAR SESSION STATE
# ----------------------------
if "form_version" not in st.session_state:
    st.session_state.form_version = 0
v = st.session_state.form_version

# ----------------------------
# INTERFAZ PRINCIPAL
# ----------------------------
st.markdown("<h1>📦 Control de Stock</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#555;'>Registra, edita y visualiza tu inventario 🚀</p>", unsafe_allow_html=True)

tab_registro, tab_historial, tab_consolidado = st.tabs(["📝 Registrar", "📜 Historial", "📊 Consolidado"])

# ==========================================
# PESTAÑA 1: REGISTRAR
# ==========================================
with tab_registro:
    historial_actual = cargar_historial()
    
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📅 Fecha y Producto")
        fecha = st.date_input("Selecciona la fecha", value=date.today(), key=f"fecha_{v}")
        producto = st.selectbox("Selecciona el producto", PRODUCTOS, key=f"producto_{v}")
        
        # Calcular stock actual real
        stock_actual = 0
        if not historial_actual.empty:
            df_prod = historial_actual[historial_actual["producto"] == producto]
            if not df_prod.empty:
                stock_actual = int(df_prod["stock_final"].sum())
                
        st.info(f"📦 **Stock actual en sistema:** {stock_actual} unidades")
        
        # NUEVO: Opción para forzar stock inicial (por si es la primera vez)
        actualizar_inicial = st.checkbox("🔄 Registrar/Actualizar Stock Inicial", key=f"chk_inicial_{v}")
        
        nuevo_stock_base = stock_actual
        if actualizar_inicial:
            nuevo_stock_base = st.number_input(
                "Escribe la cantidad física real que tienes:", 
                min_value=0, step=1, value=stock_actual, key=f"stock_base_{v}"
            )
            
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📊 Movimientos del día")
        
        entradas = st.number_input("Entradas (➕)", min_value=0, step=1, value=0, key=f"entradas_{v}")
        salidas = st.number_input("Salidas (➖)", min_value=0, step=1, value=0, key=f"salidas_{v}")
        
        # Cálculo matemático final
        stock_final = nuevo_stock_base + entradas - salidas
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("✅ Stock Final Proyectado")
    st.metric(label="Resultado", value=f"{stock_final} unidades")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("💾 Guardar registro"):
        if stock_final < 0:
            st.error(f"🚨 ¡Ojo! No tienes suficiente stock. Tienes {nuevo_stock_base} y estás intentando sacar {salidas}.")
        elif entradas == 0 and salidas == 0 and not actualizar_inicial:
            st.warning("⚠️ No has registrado entradas, salidas ni actualizado el stock inicial.")
        else:
            df_actual = cargar_historial()
            
            # Si el usuario actualizó el stock inicial, calculamos la diferencia como una "entrada"
            # para que el historial guarde la realidad de forma correcta.
            entrada_real = entradas
            if actualizar_inicial and nuevo_stock_base != stock_actual:
                entrada_real += (nuevo_stock_base - stock_actual)
            
            nuevo = pd.DataFrame([{
                "id": str(uuid.uuid4()), 
                "fecha": str(fecha), 
                "producto": producto,
                "stock_inicial": stock_actual, 
                "entradas": entrada_real,
                "salidas": salidas, 
                "stock_final": stock_final
            }])
            df_actual = pd.concat([df_actual, nuevo], ignore_index=True)
            guardar_dataframe(df_actual)
            
            st.success(f"✅ Registro guardado para **{producto}**")
            st.balloons()
            st.session_state.form_version += 1
            st.rerun()

# ==========================================
# PESTAÑA 2: HISTORIAL
# ==========================================
with tab_historial:
    historial = cargar_historial()

    if historial.empty:
        st.info("Aún no hay registros. ¡Empieza registrando tu primer movimiento! 🎉")
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

            for _, row in filtrado.iterrows():
                rid = row["id"]
                with st.expander(f"📅 {row['fecha']} | 📦 {row['producto']} | Final: {int(row['stock_final'])}"):
                    st.write(f"**Stock inicial:** {int(row['stock_inicial'])}")
                    st.write(f"**Entradas:** ➕ {int(row['entradas'])}")
                    st.write(f"**Salidas:** ➖ {int(row['salidas'])}")
                    st.write(f"**Stock final:** ✅ {int(row['stock_final'])}")

                    col_edit, col_del = st.columns(2)
                    with col_edit:
                        if st.button("✏️ Editar", key=f"edit_{rid}"):
                            st.session_state["editando"] = rid
                    with col_del:
                        if st.button("🗑️ Eliminar", key=f"del_{rid}"):
                            st.session_state["confirmar_eliminar"] = rid

                    if st.session_state.get("editando") == rid:
                        st.markdown("### ✏️ Editando registro histórico")
                        edit_ent = st.number_input("Entradas", min_value=0, step=1, value=int(row["entradas"]), key=f"edit_ent_{rid}")
                        edit_sal = st.number_input("Salidas", min_value=0, step=1, value=int(row["salidas"]), key=f"edit_sal_{rid}")
                        edit_final = int(row["stock_inicial"]) + edit_ent - edit_sal
                        st.info(f"Stock final recalculado: **{edit_final}**")

                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.button("💾 Guardar cambios", key=f"save_{rid}"):
                                if edit_final < 0:
                                    st.warning("⚠️ El stock final no puede ser negativo.")
                                else:
                                    df_actual = cargar_historial()
                                    mask = df_actual["id"] == rid
                                    df_actual.loc[mask, "entradas"] = edit_ent
                                    df_actual.loc[mask, "salidas"] = edit_sal
                                    df_actual.loc[mask, "stock_final"] = edit_final
                                    guardar_dataframe(df_actual)
                                    st.session_state.pop("editando", None)
                                    st.success("✅ Registro actualizado")
                                    st.rerun()
                        with col_cancel:
                            if st.button("❌ Cancelar", key=f"cancel_{rid}"):
                                st.session_state.pop("editando", None)
                                st.rerun()

                    if st.session_state.get("confirmar_eliminar") == rid:
                        st.warning("⚠️ ¿Seguro que quieres eliminar este registro?")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✅ Sí, eliminar", key=f"conf_del_{rid}"):
                                df_actual = cargar_historial()
                                df_actual = df_actual[df_actual["id"] != rid]
                                guardar_dataframe(df_actual)
                                st.session_state.pop("confirmar_eliminar", None)
                                st.success("🗑️ Registro eliminado")
                                st.rerun()
                        with c2:
                            if st.button("❌ No", key=f"no_del_{rid}"):
                                st.session_state.pop("confirmar_eliminar", None)
                                st.rerun()

# ==========================================
# PESTAÑA 3: CONSOLIDADO
# ==========================================
with tab_consolidado:
    historial = cargar_historial()
    
    if historial.empty:
        st.info("Aún no hay datos para consolidar. Registra algún movimiento primero. 📉")
    else:
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
        
        csv_consolidado = consolidado.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Descargar Consolidado (CSV)",
            data=csv_consolidado,
            file_name="consolidado_stock.csv",
            mime="text/csv"
        )