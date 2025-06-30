import streamlit as st
import math
import pandas as pd

# --- Configuración de la Página y Datos ---
st.set_page_config(layout="wide", page_title="Planificador de Puesta a Tierra AEA")

# Base de datos de la reglamentación y constantes
DB = {
    "soil_resistivity": {
        'Arcillas': 10, 'Aluvial': 5, 'Greda': 20, 
        'Tierra calcárea': 50, 'Arenisca': 100
    },
    "parallel_coefficients": {
        1: 1.0, 2: 0.57, 3: 0.42, 4: 0.33, 5: 0.27, 6: 0.24,
        7: 0.21, 8: 0.19, 9: 0.17, 10: 0.15
    },
    "aea_table": {
        "50": {"30": 1666, "100": 500, "300": 167, "500": 100, "1000": 50},
        "24": {"30": 800, "100": 240, "300": 80, "500": 48, "1000": 24}
    },
    "aea_final_cap": {"30": 40, "100": 40, "300": 40, "500": 24, "1000": 12},
    "jabalina_l": {"1.5m": 1.5, "3m": 3.0},
    "jabalina_d": {"1/2\"": 0.0127, "5/8\"": 0.0158, "3/4\"": 0.01905},
    "rcd_options": {"30 mA": 30, "100 mA": 100, "300 mA": 300, "500 mA": 500, "1 A": 1000}
}

# --- Funciones de Cálculo ---
def get_pat_objective(rcd, ul, manual_check, manual_value):
    """Determina la resistencia objetivo según la reglamentación o un valor manual."""
    if manual_check and manual_value > 0:
        return manual_value
    rcd_str = str(rcd)
    ul_str = str(ul)
    calculated_ra = DB["aea_table"].get(ul_str, {}).get(rcd_str, float('inf'))
    capped_ra = DB["aea_final_cap"].get(rcd_str, calculated_ra)
    return min(calculated_ra, capped_ra)

def calculate_pat(resistividad, longitud, diametro, objetivo):
    """Calcula la resistencia de la PAT y el número de jabalinas necesarias."""
    # La fórmula del apunte usa 'd' como diámetro
    Rj = (resistividad / (2 * math.pi * longitud)) * math.log((4 * longitud / diametro) - 1)
    
    num_jabalinas = 0
    Rt = float('inf')

    if Rj <= objetivo:
        num_jabalinas = 1
        Rt = Rj
    else:
        for i in range(2, 11):
            k = DB["parallel_coefficients"][i]
            current_rt = k * Rj
            if current_rt <= objetivo:
                num_jabalinas = i
                Rt = current_rt
                break
    
    if num_jabalinas == 0:
        num_jabalinas = 10
        Rt = DB["parallel_coefficients"][10] * Rj
        
    Re = longitud / math.log(longitud / diametro)
    return {
        "Rj": Rj, "Rt": Rt, "num_jabalinas": num_jabalinas, "Re": Re,
        "cumple": Rt <= objetivo, "objetivo": objetivo, 
        "longitud": longitud, "diametro": diametro
    }

# --- Interfaz de Usuario (Sidebar) ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/GHS-pictogram-explos.svg/1024px-GHS-pictogram-explos.svg.png", width=80)
st.sidebar.title("Configuración del Cálculo")

mode = st.sidebar.selectbox(
    "Modo de Calculadora",
    ("Verificación Domiciliaria", "Proyecto Completo (Multi-Sector)")
)

st.sidebar.header("1. Parámetros Generales")
ul_condition = st.sidebar.selectbox(
    "Condiciones / Tensión Límite (UL)",
    ("Común / Sin supervisión (UL = 24V)", "Seco / Personal capacitado (UL = 50V)"),
    key="ul"
)
ul = 24 if "24V" in ul_condition else 50

soil_type = st.sidebar.selectbox("Resistividad del Terreno (ρ)", list(DB["soil_resistivity"].keys()) + ["Manual"])
if soil_type == "Manual":
    resistividad = st.sidebar.number_input("Resistividad Manual (Ω·m)", min_value=1, value=80)
else:
    resistividad = DB["soil_resistivity"][soil_type]

# Inicializar estado de sesión para sectores en modo proyecto
if 'sectors' not in st.session_state:
    st.session_state['sectors'] = {
        1: {"name": "Sector 1", "rcd": 30, "l": 3.0, "d": 0.01905, "manual_check": False, "manual_input": 40.0}
    }

# --- Lógica de la Interfaz Principal ---
st.title("Planificador de Puesta a Tierra (Esquema TT)")
st.caption("Diseño y verificación según reglamentación AEA 90364.")
st.markdown("---")

if mode == "Verificación Domiciliaria":
    st.sidebar.header("2. Puesta a Tierra a Verificar")
    
    dom_rcd_key = st.sidebar.selectbox("Sensibilidad Diferencial (IΔn)", list(DB["rcd_options"].keys()), index=0)
    dom_rcd = DB["rcd_options"][dom_rcd_key]

    dom_manual_check = st.sidebar.checkbox("Usar objetivo manual de resistencia", key="dom_manual_check")
    dom_manual_input = st.sidebar.number_input("Objetivo Manual (Ω)", min_value=0.1, value=5.0, key="dom_manual_input", disabled=not dom_manual_check)
    
    col1, col2 = st.sidebar.columns(2)
    dom_l_key = col1.selectbox("Longitud", list(DB["jabalina_l"].keys()), index=1)
    dom_d_key = col2.selectbox("Diámetro", list(DB["jabalina_d"].keys()), index=2)
    dom_l = DB["jabalina_l"][dom_l_key]
    dom_d = DB["jabalina_d"][dom_d_key]

    if st.sidebar.button("Verificar Jabalina Domiciliaria", use_container_width=True, type="primary"):
        objetivo = get_pat_objective(dom_rcd, ul, dom_manual_check, dom_manual_input)
        result = calculate_pat(resistividad, dom_l, dom_d, objetivo)
        result["isManual"] = dom_manual_check
        result["rcd"] = dom_rcd
        currentResults = {"params": {"mode": "domiciliaria", "ul": ul, "resistividad": resistividad}, "patUnica": result}

        # Display results for home verification
        st.subheader("Resultados de Verificación")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Resistencia de 1 Jabalina (Rj)", f"{result['Rj']:.2f} Ω")
            st.metric("Resistencia Máx. Permitida", f"≤ {result['objetivo']:.1f} Ω")
        with col2:
            st.metric("Jabalinas Necesarias", f"{result['num_jabalinas']}")
            st.metric("Resistencia Final (RT)", f"{result['Rt']:.2f} Ω")

        if result['cumple']:
            st.success("✅ **CUMPLE:** La solución propuesta cumple con la reglamentación.")
        else:
            st.error("❌ **NO CUMPLE:** La solución propuesta no alcanza el objetivo de resistencia.")

elif mode == "Proyecto Completo (Multi-Sector)":
    st.sidebar.header("2. Puesta a Tierra de Servicio (RB)")
    st.sidebar.caption("Objetivo predeterminado: ≤ 1.0 Ω")
    
    col1, col2 = st.sidebar.columns(2)
    srv_l_key = col1.selectbox("Longitud Jabalina Servicio", list(DB["jabalina_l"].keys()), index=1)
    srv_d_key = col2.selectbox("Diámetro Jabalina Servicio", list(DB["jabalina_d"].keys()), index=2)
    srv_l = DB["jabalina_l"][srv_l_key]
    srv_d = DB["jabalina_d"][srv_d_key]
    
    srv_manual_check = st.sidebar.checkbox("Usar objetivo manual para RB", key="srv_manual_check")
    srv_manual_input = st.sidebar.number_input("Objetivo Manual RB (Ω)", min_value=0.1, value=1.0, key="srv_manual_input", disabled=not srv_manual_check)

    st.sidebar.header("3. Sectores de Protección (RA)")
    for i in st.session_state.sectors:
        with st.sidebar.expander(f"Configuración Sector {i}: {st.session_state.sectors[i]['name']}", expanded=True):
            st.session_state.sectors[i]['name'] = st.text_input("Nombre del Sector", st.session_state.sectors[i]['name'], key=f"name_{i}")
            rcd_key = st.selectbox("Sensibilidad Diferencial", list(DB["rcd_options"].keys()), key=f"rcd_{i}")
            st.session_state.sectors[i]['rcd'] = DB["rcd_options"][rcd_key]
            
            c1, c2 = st.columns(2)
            l_key = c1.selectbox("Longitud Jabalina", list(DB["jabalina_l"].keys()), index=1, key=f"l_{i}")
            d_key = c2.selectbox("Diámetro Jabalina", list(DB["jabalina_d"].keys()), index=2, key=f"d_{i}")
            st.session_state.sectors[i]['l'] = DB["jabalina_l"][l_key]
            st.session_state.sectors[i]['d'] = DB["jabalina_d"][d_key]
            
            st.session_state.sectors[i]['manual_check'] = st.checkbox("Usar objetivo manual", key=f"manual_check_{i}")
            st.session_state.sectors[i]['manual_input'] = st.number_input("Objetivo Manual (Ω)", min_value=0.1, value=40.0, key=f"manual_input_{i}", disabled=not st.session_state.sectors[i]['manual_check'])
    
    col1, col2 = st.sidebar.columns(2)
    if col1.button("Añadir Sector"):
        new_id = max(st.session_state.sectors.keys()) + 1 if st.session_state.sectors else 1
        st.session_state.sectors[new_id] = {"name": f"Sector {new_id}", "rcd": 30, "l": 3.0, "d": 0.01905, "manual_check": False, "manual_input": 40.0}
        st.rerun()

    if col2.button("Eliminar Último"):
        if len(st.session_state.sectors) > 1:
            last_id = max(st.session_state.sectors.keys())
            del st.session_state.sectors[last_id]
            st.rerun()

    if st.sidebar.button("Calcular Proyecto Completo", use_container_width=True, type="primary"):
        # Service PAT
        srv_objetivo = srv_manual_input if srv_manual_check else 1.0
        pat_service = calculate_pat(resistividad, srv_l, srv_d, srv_objetivo)
        pat_service["isManual"] = srv_manual_check
        
        # Protection PATs
        pat_proteccion = []
        for i in st.session_state.sectors:
            sector = st.session_state.sectors[i]
            objetivo = get_pat_objective(sector['rcd'], ul, sector['manual_check'], sector['manual_input'])
            result = calculate_pat(resistividad, sector['l'], sector['d'], objetivo)
            result.update({"name": sector['name'], "rcd": sector['rcd'], "isManual": sector['manual_check']})
            pat_proteccion.append(result)

        # Display results for project
        st.subheader("1. Puesta a Tierra de Servicio (RB)")
        st.metric("Resistencia de 1 Jabalina (Rj)", f"{pat_service['Rj']:.2f} Ω")
        st.metric("Objetivo de Resistencia", f"≤ {pat_service['objetivo']:.1f} Ω")
        st.metric("Jabalinas Necesarias", f"{pat_service['num_jabalinas']}")
        st.metric("Resistencia Final del Sistema (RT)", f"{pat_service['Rt']:.2f} Ω")
        if pat_service['cumple']: st.success("✅ CUMPLE") 
        else: st.error("❌ NO CUMPLE")

        st.subheader("2. Puestas a Tierra de Protección (RA)")
        cols = st.columns(len(pat_proteccion))
        for i, p in enumerate(pat_proteccion):
            with cols[i]:
                with st.container(border=True):
                    st.caption(f"SECTOR: {p['name']}")
                    st.metric("Resistencia Final (RT)", f"{p['Rt']:.2f} Ω")
                    st.metric("Jabalinas", f"{p['num_jabalinas']}")
                    st.caption(f"Objetivo: ≤ {p['objetivo']:.1f} Ω")
                    if p['cumple']: st.success("CUMPLE", icon="✅")
                    else: st.error("NO CUMPLE", icon="❌")

        st.subheader("3. Requisito de Separación")
        st.metric("Separación Mínima entre Sistemas (10 x Re)", f"{(pat_service['Re'] * 10):.2f} m")

# --- Anexos y Exportación (siempre visibles si hay un cálculo) ---
if st.button("Mostrar/Ocultar Anexos"):
    st.session_state.show_annex = not st.session_state.get('show_annex', False)

if st.session_state.get('show_annex', False):
    st.markdown("---")
    st.header("Anexos Técnicos")
    tab1, tab2, tab3 = st.tabs(["Fórmulas", "Tabla Resistividad", "Tabla Coeficientes"])
    with tab1:
        st.subheader("Fórmulas Utilizadas")
        st.latex(r''' R_j = \left(\frac{\rho}{2 \cdot \pi \cdot L}\right) \cdot \ln\left(\frac{4L}{d} - 1\right) ''')
        st.latex(r''' R_T = K \cdot R_j ''')
        st.latex(r''' R_A \le \frac{U_L}{I_{\Delta n}} ''')
    with tab2:
        st.subheader("Tabla de Resistividad del Terreno")
        st.table(pd.DataFrame(list(DB["soil_resistivity"].items()), columns=["Tipo de Suelo", "Resistividad (Ω·m)"]))
    with tab3:
        st.subheader("Tabla de Coeficientes en Paralelo (K)")
        st.table(pd.DataFrame(list(DB["parallel_coefficients"].items()), columns=["N° Jabalinas", "Coeficiente (K)"]))
