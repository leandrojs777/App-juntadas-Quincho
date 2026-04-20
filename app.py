import streamlit as st
import pandas as pd
from utils.scoring import (
    inicializar_datos,
    cargar_eventos,
    crear_evento,
    agregar_opcion,
    obtener_opciones_evento,
    registrar_voto,
    registrar_voto_cancelar,
    cambiar_estado_evento,
    obtener_resultados_evento,
    obtener_cancelaciones_evento,
    obtener_estadisticas_quincho,
    UMBRAL_CANCELACION
)

# Inicializar bd
inicializar_datos()

# Config de pág
st.set_page_config(
    page_title="La App de los Pibes",
    page_icon="🍻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .titulo-cheto { background: -webkit-linear-gradient(45deg, #FF6B6B, #FF8E53); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3em !important; font-weight: 800; text-align: center; margin-bottom: 0.5em; }
    .resultado-card { background: #1E1E2E; border-radius: 15px; padding: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); border-left: 5px solid #FF6B6B; color: #FFFFFF; text-align: center; margin-bottom: 10px; }
    .resultado-ganador { font-size: 1.5em; font-weight: bold; color: #A8E6CF; }
    .stat-number { font-size: 2em; color: #FF8E53; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

LOS_PIBES = ["Mauri", "Chicho", "Palomo", "Luis", "Cristian", "Ova", "Pochi", "Sinchy"]

# SIDEBAR
st.sidebar.markdown("## 👤 ¿Quién sos, fiera?")
usuario_actual = st.sidebar.selectbox("Elegí tu nombre:", LOS_PIBES)

st.sidebar.markdown("---")
st.sidebar.info(f"""
**Reglas del Tablero:**
1. Alguien propone una juntada nueva.
2. Votá qué fecha y lugar te van (1 a 5 estrellas).
3. Podés agregar opciones a la juntada si no te gusta ninguna.
4. Si {UMBRAL_CANCELACION} personas se bajan (voto Cancelar), la juntada muere.
""")

st.markdown('<h1 class="titulo-cheto">🍻 Organizador de Juntadas</h1>', unsafe_allow_html=True)

tab_tablero, tab_nueva, tab_stats = st.tabs(["📅 Tablero Principal", "➕ Armar Propuesta", "📊 Estadísticas del Quincho"])

df_eventos = cargar_eventos()

# TAB 1: TABLERO PRINCIPAL
with tab_tablero:
    st.header("Juntadas Activas")
    
    eventos_abiertos = df_eventos[df_eventos['Estado'] == 'Abierto']
    
    if eventos_abiertos.empty:
        st.info("No hay ninguna juntada activa. ¡Andá a 'Armar Propuesta' y agitá un poco!")
    else:
        for index, row in eventos_abiertos.iterrows():
            id_evento = row['ID_Evento']
            motivo = row['Motivo']
            creador = row['Creador']
            
            with st.expander(f"🔥 {motivo} (Agitada por {creador})", expanded=False):
                col_votar, col_resultados = st.columns([1.5, 1])
                
                opciones = obtener_opciones_evento(id_evento)
                fechas = opciones.get('Fecha', [])
                lugares = opciones.get('Lugar', [])
                canceladores = obtener_cancelaciones_evento(id_evento)
                
                with col_votar:
                    st.subheader("Emití tu Voto")
                    with st.form(key=f"form_votar_{id_evento}"):
                        votos_temp = {}
                        
                        st.markdown("**Fechas Propuestas**")
                        if fechas:
                            for f in fechas:
                                votos_temp[('Fecha', f)] = st.slider(f"Día: {f}", 1, 5, 3, key=f"sld_{id_evento}_f_{f}")
                        else:
                            st.write("No hay fechas.")
                            
                        st.markdown("**Lugares Sugeridos**")
                        if lugares:
                            for l in lugares:
                                votos_temp[('Lugar', l)] = st.slider(f"Lugar: {l}", 1, 5, 3, key=f"sld_{id_evento}_l_{l}")
                        else:
                            st.write("No hay lugares.")
                            
                        submit_voto = st.form_submit_button("Guardar Votos")
                        if submit_voto:
                            for (cat, op), pts in votos_temp.items():
                                registrar_voto(id_evento, usuario_actual, cat, op, pts)
                            st.success("¡Votos guardados!")
                            st.rerun()
                    
                    st.markdown("---")
                    st.markdown("**¿Tenés una mejor idea?**")
                    with st.form(key=f"form_nueva_op_{id_evento}"):
                        nueva_cat = st.radio("Categoría:", ["Fecha", "Lugar"], key=f"rad_{id_evento}")
                        nueva_op = st.text_input("Nueva propuesta:", key=f"txt_{id_evento}")
                        if st.form_submit_button("Agregar al evento"):
                            if nueva_op:
                                agregar_opcion(id_evento, nueva_cat, nueva_op.strip())
                                registrar_voto(id_evento, usuario_actual, nueva_cat, nueva_op.strip(), 5) # Vota automático 5
                                st.success("Agregada")
                                st.rerun()
                    
                    st.markdown("---")
                    if usuario_actual in canceladores:
                        st.error("Vos ya te bajaste de esta juntada (Votaste Cancelar).")
                    else:
                        if st.button("❌ ¡Me bajo de esta! (Votar Cancelar)", key=f"btn_cancel_{id_evento}"):
                            registrar_voto_cancelar(id_evento, usuario_actual)
                            st.warning("Te bajaste. Si son 4, se pudre todo.")
                            st.rerun()

                with col_resultados:
                    st.subheader("Resultados Parciales")
                    df_res = obtener_resultados_evento(id_evento)
                    
                    if df_res.empty:
                        st.info("No hay votos todavía.")
                    else:
                        for cat in ['Fecha', 'Lugar']:
                            df_cat = df_res[df_res['Categoria'] == cat]
                            if not df_cat.empty:
                                gan = df_cat.iloc[0]
                                st.markdown(f"""
                                <div class="resultado-card">
                                    <div style="color:#FF8E53">{cat} que va ganando:</div>
                                    <div class="resultado-ganador">{gan['Opcion']}</div>
                                    <div style="font-size:0.8em; color:#ddd">{gan['Puntos']} puntos</div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                    if canceladores:
                        st.write(f"🛑 **Gente que se bajó ({len(canceladores)}/{UMBRAL_CANCELACION}):**", ", ".join(canceladores))
                        
                    if creador == usuario_actual:
                        st.markdown("---")
                        if st.button("✅ Marcar como CONCRETADA", key=f"btn_concl_{id_evento}", help="Solo el creador puede cerrar la juntada si ya se hizo."):
                            cambiar_estado_evento(id_evento, "Concretado")
                            st.success("Evento cerrado con éxito.")
                            st.rerun()

    st.markdown("---")
    st.header("Historial (Canceladas / Concretadas)")
    eventos_cerrados = df_eventos[df_eventos['Estado'] != 'Abierto']
    if not eventos_cerrados.empty:
        st.dataframe(eventos_cerrados[['Motivo', 'Creador', 'Estado']], use_container_width=True)


# TAB 2: ARMAR PROPUESTA
with tab_nueva:
    st.header("Agitar una nueva Juntada")
    st.write("Tirá la idea, poné un par de fechas y opciones de lugar base, y que los pibes decidan.")
    
    with st.form("form_crear_evento"):
        motivo = st.text_input("¿Qué hacemos? (Ej: Asadazo de fin de mes, Jugar al Padel)")
        st.markdown("**Opciones iniciales (separalas con coma)**")
        fechas_iniciales = st.text_input("Fechas posibles (Ej: Viernes 12, Sabado 13)")
        lugares_iniciales = st.text_input("Lugares posibles (Ej: Lo de Chicho, Bar del centro)")
        
        submit_crear = st.form_submit_button("¡Crear y habilitar votación!")
        
        if submit_crear:
            if motivo.strip() and fechas_iniciales.strip() and lugares_iniciales.strip():
                nuevo_id = crear_evento(motivo.strip(), usuario_actual)
                
                # Procesar fechas
                fechas = [f.strip() for f in fechas_iniciales.split(',') if f.strip()]
                for f in fechas:
                    agregar_opcion(nuevo_id, "Fecha", f)
                    
                # Procesar lugares
                lugares = [l.strip() for l in lugares_iniciales.split(',') if l.strip()]
                for l in lugares:
                    agregar_opcion(nuevo_id, "Lugar", l)
                    
                st.success("¡Juntada creada! Ya está en el tablero lista para que voten.")
                # No hacemos st.rerun automático acá a veces rompe la UI si es rápido, mejor limpiar o invitar a cambiar de tab.
            else:
                st.error("Che, llená todos los campos para que no quede vacía la encuesta.")


# TAB 3: ESTADÍSTICAS DEL QUINCHO
with tab_stats:
    st.header("Estadísticas del Quincho")
    st.write("Acá vemos quién pone la casa y las ideas, y quién se baja a último momento.")
    
    df_stats = obtener_estadisticas_quincho()
    
    # Destacar a los mejores y peores
    if not df_stats.empty:
        col_mvp, col_fantasma = st.columns(2)
        
        mvp = df_stats.loc[df_stats['Juntadas Creadas'].idxmax()]
        fantasma = df_stats.loc[df_stats['Veces que Agitó Cancelar'].idxmax()]
        
        with col_mvp:
            st.info(f"🏆 **El MVP (Más juntadas armadas):** {mvp['Pibe']} con {mvp['Juntadas Creadas']} agitadas.")
        with col_fantasma:
            st.error(f"👻 **El Fantasma (Más veces se bajó):** {fantasma['Pibe']} con {fantasma['Veces que Agitó Cancelar']} fugas.")
    
        st.dataframe(df_stats.style.highlight_max(axis=0, subset=['Juntadas Creadas', 'Veces que Agitó Cancelar']), use_container_width=True)
