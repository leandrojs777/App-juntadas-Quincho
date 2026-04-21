import streamlit as st
import pandas as pd
from utils.scoring import (
    inicializar_datos,
    cargar_eventos,
    cargar_votos,
    crear_evento,
    agregar_opcion,
    obtener_opciones_evento,
    registrar_voto,
    registrar_voto_cancelar,
    cambiar_estado_evento,
    obtener_cancelaciones_evento,
    obtener_votos_usuario,
    obtener_estadisticas_quincho,
    UMBRAL_CANCELACION,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="La App de los Pibes 🍻",
    page_icon="🍻",
    layout="wide",
    initial_sidebar_state="expanded",
)

inicializar_datos()

# ── Constantes de votación ────────────────────────────────────────────────────
# El sistema usa 3 niveles: puedo (5pts) / capaz (3pts) / no puedo (1pt)
VOTO_OPTIONS = ["✅ Puedo", "🤔 Capaz", "❌ No puedo"]
VOTO_PTS     = {"✅ Puedo": 5, "🤔 Capaz": 3, "❌ No puedo": 1}
PTS_TO_LABEL = {5: "✅ Puedo", 3: "🤔 Capaz", 1: "❌ No puedo"}
LOS_PIBES    = ["Mauri", "Chicho", "Palomo", "Luis", "Cristian", "Ova", "Pochi", "Sinchy"]


# Etiquetas plurales correctas por categoría
CAT_LABEL = {"Fecha": "Fechas", "Lugar": "Lugares", "Modalidad": "Modalidad"}

# ── Callback auto-save ────────────────────────────────────────────────────────
# Se dispara en on_change del radio — guarda el voto sin botón extra.
# También marca el evento como "en votación activa" para evitar que el
# expander se cierre automáticamente durante el proceso de voto.
def _auto_votar(id_evento: str, usuario: str, categoria: str, opcion: str, key: str):
    label = st.session_state.get(key)
    if label and label in VOTO_PTS:
        registrar_voto(id_evento, usuario, categoria, opcion, VOTO_PTS[label])
    # Mantener expander abierto mientras el usuario está votando
    st.session_state[f"voting_active_{id_evento}"] = True


# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .titulo-main {
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 60%, #FF6B6B 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
        font-size: 2.8em !important; font-weight: 800; text-align: center;
        margin-bottom: 0.1em; letter-spacing: -1.5px;
    }
    .subtitulo { text-align:center; color:#6b7280; font-size:.95em; margin-bottom:1.8em; }

    /* Badges */
    .badge { display:inline-block; border-radius:20px; padding:2px 11px;
             font-size:.72em; font-weight:600; line-height:1.8; margin-right:4px; }
    .badge-ok     { background:#14532d; color:#4ade80; border:1px solid #22c55e; }
    .badge-warn   { background:#431407; color:#fb923c; border:1px solid #f97316; }
    .badge-cancel { background:#450a0a; color:#f87171; border:1px solid #ef4444; }
    .badge-done   { background:#1e3a5f; color:#60a5fa; border:1px solid #3b82f6; }

    /* Resultados */
    .res-row {
        display:flex; align-items:center; justify-content:space-between;
        background:#1e2533; border-radius:10px; padding:11px 16px;
        margin-bottom:8px; gap:10px;
        border: 1px solid #374151;
    }
    .res-name    { font-weight:600; font-size:.95em; flex:1; color:#f3f4f6; }
    .res-counts  { display:flex; gap:14px; font-size:.92em; white-space:nowrap; }
    .cnt-ok      { color:#4ade80; font-weight:700; }
    .cnt-maybe   { color:#fbbf24; font-weight:700; }
    .cnt-no      { color:#f87171; font-weight:700; }
    .lider-badge { font-size:.75em; background:#14532d; color:#4ade80;
                   border:1px solid #22c55e; border-radius:12px;
                   padding:1px 8px; margin-left:6px; }

    /* Section dividers */
    .sec-label { font-size:.72em; font-weight:700; color:#9ca3af;
                 letter-spacing:1px; text-transform:uppercase;
                 margin: 14px 0 4px 0; }

    /* Historial */
    .hist-item { display:flex; align-items:center; gap:10px; padding:8px 12px;
                 border-radius:8px; background:#111827; margin-bottom:6px; font-size:.9em; }

    /* User chip sidebar */
    .user-chip { background:linear-gradient(135deg,#1e1e3a,#23234a);
                 border:1px solid #6366f1; border-radius:14px;
                 padding:12px 16px; text-align:center; margin-bottom:4px; }
    .user-chip-name { font-size:1.1em; font-weight:700; color:#a5b4fc; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "usuario_actual" not in st.session_state:
    st.session_state["usuario_actual"] = LOS_PIBES[0]


# ════════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 👤 ¿Quién sos?")

    nuevo_usuario = st.selectbox(
        "Elegí tu nombre:",
        LOS_PIBES,
        index=LOS_PIBES.index(st.session_state["usuario_actual"]),
        key="sel_usuario_box",
    )
    if nuevo_usuario != st.session_state["usuario_actual"]:
        st.session_state["usuario_actual"] = nuevo_usuario
        st.rerun()

    st.markdown(f"""
    <div class="user-chip">
        <div style="font-size:1.6em">🙋</div>
        <div class="user-chip-name">{st.session_state['usuario_actual']}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"""
**📋 Cómo funciona**

1. Alguien propone una juntada con fechas y lugares.
2. Cada pibe toca **✅ Puedo / 🤔 Capaz / ❌ No puedo** en cada opción.
   *Se guarda solo al tocar — sin "Guardar".*
3. Podés sugerir fechas o lugares nuevos.
4. Si **{UMBRAL_CANCELACION}** o más se bajan → la juntada se cancela.
5. El creador la marca como **Concretada** cuando ya fue.
    """)

usuario_actual: str = st.session_state["usuario_actual"]


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<h1 class="titulo-main">🍻 La App de los Pibes</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitulo">Organizador de Juntadas del Quincho</p>', unsafe_allow_html=True)

tab_tablero, tab_nueva, tab_stats = st.tabs(["📅 Tablero", "➕ Nueva Juntada", "📊 Estadísticas"])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — TABLERO
# ════════════════════════════════════════════════════════════════════════════════
with tab_tablero:
    df_eventos  = cargar_eventos()
    df_votos_all = cargar_votos()

    eventos_abiertos = df_eventos[df_eventos["Estado"] == "Abierto"]

    col_h1, col_h2, col_h3 = st.columns([3, 1, 1])
    with col_h1:
        st.subheader("🔥 Juntadas Activas")
    with col_h2:
        st.metric("Activas", len(eventos_abiertos))
    with col_h3:
        st.metric("Historial", len(df_eventos) - len(eventos_abiertos))

    st.markdown("---")

    if eventos_abiertos.empty:
        st.info("No hay juntadas activas. ¡Andá a **'Nueva Juntada'** y agitá algo!")

    for _, row in eventos_abiertos.iterrows():
        id_evento: str = row["ID_Evento"]
        motivo:    str = row["Motivo"]
        creador:   str = row["Creador"]

        # ── Estado de participación ──────────────────────────────────────────
        votos_usuario = obtener_votos_usuario(id_evento, usuario_actual)
        votos_reales  = {k: v for k, v in votos_usuario.items() if k[0] != "Estado"}
        ya_voto       = bool(votos_reales)
        canceladores  = obtener_cancelaciones_evento(id_evento)

        participantes = (
            df_votos_all[
                (df_votos_all["ID_Evento"] == id_evento) &
                (df_votos_all["Categoria"] != "Estado")
            ]["Usuario"].nunique()
            if not df_votos_all.empty else 0
        )

        badge_html = (
            '<span class="badge badge-ok">✅ Ya votaste</span>'
            if ya_voto else
            '<span class="badge badge-warn">⏳ Todavía no votaste</span>'
        )

        titulo = f"🔥 {motivo}  ·  por {creador}  ·  {participantes}/8 pibes respondieron"

        # El expander permanece abierto si el usuario aún no votó
        # o si está en proceso de votar (voting_active se setea en _auto_votar)
        voting_active = st.session_state.get(f"voting_active_{id_evento}", False)
        should_expand = (not ya_voto) or voting_active

        with st.expander(titulo, expanded=should_expand):
            st.markdown(badge_html, unsafe_allow_html=True)
            st.markdown("")

            col_votar, col_resultados = st.columns([3, 2], gap="large")

            opciones = obtener_opciones_evento(id_evento)
            fechas   = opciones.get("Fecha", [])
            lugares  = opciones.get("Lugar", [])

            # ── Auto-migración: eventos creados antes de la feature de Modalidad ──
            modalidades_en_bd = opciones.get("Modalidad", [])
            if not modalidades_en_bd and (fechas or lugares):
                for m in ["Solos", "En pareja", "En familia"]:
                    agregar_opcion(id_evento, "Modalidad", m)
                opciones["Modalidad"] = ["Solos", "En pareja", "En familia"]

            # ── COLUMNA VOTAR ────────────────────────────────────────────────
            with col_votar:
                st.markdown("#### 🗳️ Tu disponibilidad")
                st.caption("Tocá una opción — se guarda automáticamente.")

                # ── Fechas ───────────────────────────────────────────────────
                if fechas:
                    st.markdown('<div class="sec-label">📅 Fechas propuestas</div>', unsafe_allow_html=True)
                    for f in fechas:
                        k = f"radio_{id_evento}_{usuario_actual}_F_{f}"
                        voto_pts    = votos_usuario.get(("Fecha", f))
                        voto_label  = PTS_TO_LABEL.get(voto_pts)

                        # Inicializar desde BD solo la primera vez
                        if k not in st.session_state and voto_label:
                            st.session_state[k] = voto_label

                        st.radio(
                            f"📅 {f}",
                            options=VOTO_OPTIONS,
                            index=(VOTO_OPTIONS.index(st.session_state[k])
                                   if k in st.session_state and st.session_state[k] in VOTO_OPTIONS
                                   else None),
                            horizontal=True,
                            key=k,
                            on_change=_auto_votar,
                            args=(id_evento, usuario_actual, "Fecha", f, k),
                        )

                # ── Lugares ──────────────────────────────────────────────────
                if lugares:
                    st.markdown('<div class="sec-label">📍 Lugares sugeridos</div>', unsafe_allow_html=True)
                    for lu in lugares:
                        k = f"radio_{id_evento}_{usuario_actual}_L_{lu}"
                        voto_pts   = votos_usuario.get(("Lugar", lu))
                        voto_label = PTS_TO_LABEL.get(voto_pts)

                        if k not in st.session_state and voto_label:
                            st.session_state[k] = voto_label

                        st.radio(
                            f"📍 {lu}",
                            options=VOTO_OPTIONS,
                            index=(VOTO_OPTIONS.index(st.session_state[k])
                                   if k in st.session_state and st.session_state[k] in VOTO_OPTIONS
                                   else None),
                            horizontal=True,
                            key=k,
                            on_change=_auto_votar,
                            args=(id_evento, usuario_actual, "Lugar", lu, k),
                        )

                # ── Modalidad ────────────────────────────────────────────
                modalidades = opciones.get("Modalidad", [])
                if modalidades:
                    st.markdown('<div class="sec-label">🎭 ¿Cómo venimos?</div>', unsafe_allow_html=True)
                    st.caption("Votá cada modalidad — puede ganar la que más pibes quieran.")
                    for m in modalidades:
                        k = f"radio_{id_evento}_{usuario_actual}_M_{m}"
                        voto_pts   = votos_usuario.get(("Modalidad", m))
                        voto_label = PTS_TO_LABEL.get(voto_pts)
                        if k not in st.session_state and voto_label:
                            st.session_state[k] = voto_label
                        st.radio(
                            f"🎭 {m}",
                            options=VOTO_OPTIONS,
                            index=(VOTO_OPTIONS.index(st.session_state[k])
                                   if k in st.session_state and st.session_state[k] in VOTO_OPTIONS
                                   else None),
                            horizontal=True,
                            key=k,
                            on_change=_auto_votar,
                            args=(id_evento, usuario_actual, "Modalidad", m, k),
                        )

                if not fechas and not lugares and not modalidades:
                    st.info("Este evento no tiene opciones todavía.")

                # ── Sugerir nueva opción ─────────────────────────────────────
                st.markdown("---")
                st.markdown('<div class="sec-label">💡 ¿Querés agregar una opción?</div>', unsafe_allow_html=True)
                with st.form(key=f"form_nueva_op_{id_evento}", clear_on_submit=True):
                    nueva_cat = st.radio(
                        "Categoría:",
                        ["Fecha", "Lugar"],
                        horizontal=True,
                        key=f"rad_cat_{id_evento}",
                    )
                    nueva_op = st.text_input(
                        "Tu propuesta:",
                        placeholder="Ej: Domingo 20, Parrilla El Río...",
                        key=f"txt_op_{id_evento}",
                    )
                    if st.form_submit_button("➕ Agregar", use_container_width=True):
                        if nueva_op.strip():
                            agregar_opcion(id_evento, nueva_cat, nueva_op.strip())
                            registrar_voto(id_evento, usuario_actual, nueva_cat, nueva_op.strip(), 5)
                            st.success(f"'{nueva_op.strip()}' agregada — votada ✅ Puedo automático.")
                            st.rerun()
                        else:
                            st.error("Escribí algo primero.")

                # ── Cancelar asistencia ──────────────────────────────────────
                st.markdown("---")
                if usuario_actual in canceladores:
                    st.markdown(
                        '<span class="badge badge-cancel">🛑 Ya te bajaste de esta juntada</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    if st.button(
                        "🚫 Me bajo de esta juntada",
                        key=f"btn_cancel_{id_evento}",
                        help="Avisa a los demás que no podés ir.",
                    ):
                        registrar_voto_cancelar(id_evento, usuario_actual)
                        n = len(canceladores) + 1
                        msg = f"Te bajaste ({n}/{UMBRAL_CANCELACION})."
                        (st.error if n >= UMBRAL_CANCELACION else st.warning)(msg)
                        st.rerun()

            # ── COLUMNA RESULTADOS ───────────────────────────────────────────
            with col_resultados:
                st.markdown("#### 📊 ¿Cómo van los votos?")

                votos_evento = (
                    df_votos_all[
                        (df_votos_all["ID_Evento"] == id_evento) &
                        (df_votos_all["Categoria"] != "Estado")
                    ]
                    if not df_votos_all.empty else pd.DataFrame()
                )

                if votos_evento.empty:
                    st.info("Sin votos todavía.\nSé el primero 👈")
                else:
                    for cat, emoji in [("Fecha", "📅"), ("Lugar", "📍"), ("Modalidad", "🎭")]:
                        ops_cat = opciones.get(cat, [])
                        if not ops_cat:
                            continue

                        # Calcular puntos totales para ranking
                        scores = {}
                        for op in ops_cat:
                            v = votos_evento[
                                (votos_evento["Categoria"] == cat) &
                                (votos_evento["Opcion"] == op)
                            ]["Puntos"]
                            scores[op] = {
                                "total":    int(v.sum()),
                                "puedo":    int((v == 5).sum()),
                                "capaz":    int((v == 3).sum()),
                                "no_puedo": int((v == 1).sum()),
                                "n":        len(v),
                            }

                        sorted_ops = sorted(ops_cat, key=lambda x: scores[x]["total"], reverse=True)

                        st.markdown(
                            f'<div class="sec-label">{emoji} {CAT_LABEL.get(cat, cat)}</div>',
                            unsafe_allow_html=True,
                        )

                        for i, op in enumerate(sorted_ops):
                            s = scores[op]
                            if s["n"] == 0:
                                continue
                            lider = '<span class="lider-badge">🥇 va ganando</span>' if i == 0 else ""
                            st.markdown(
                                f'<div class="res-row">'
                                f'  <div class="res-name">{op}{lider}</div>'
                                f'  <div class="res-counts">'
                                f'    <span class="cnt-ok">✅ {s["puedo"]}</span>'
                                f'    <span class="cnt-maybe">🤔 {s["capaz"]}</span>'
                                f'    <span class="cnt-no">❌ {s["no_puedo"]}</span>'
                                f'  </div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                if canceladores:
                    st.markdown(
                        f'<span class="badge badge-cancel">🛑 {len(canceladores)}/{UMBRAL_CANCELACION} se bajaron</span>',
                        unsafe_allow_html=True,
                    )
                    st.caption(", ".join(canceladores))

                # ── Concretar (solo el creador) ──────────────────────────────
                if creador == usuario_actual:
                    st.markdown("---")
                    tiene_votos = not votos_evento.empty
                    if st.button(
                        "✅ Marcar como CONCRETADA",
                        key=f"btn_concl_{id_evento}",
                        type="primary",
                        disabled=not tiene_votos,
                    ):
                        ok = cambiar_estado_evento(id_evento, "Concretado")
                        if ok:
                            st.balloons()
                            st.success("🎉 ¡Juntada concretada!")
                            st.rerun()
                    if not tiene_votos:
                        st.caption("⚠️ Necesitás al menos un voto para concretar.")

    # ── Historial ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📜 Historial")
    eventos_cerrados = df_eventos[df_eventos["Estado"] != "Abierto"]
    if eventos_cerrados.empty:
        st.caption("Todavía no hay juntadas cerradas.")
    else:
        for _, row in eventos_cerrados.iterrows():
            es_ok       = row["Estado"] == "Concretado"
            emoji_hist  = "✅" if es_ok else "❌"
            badge_class = "badge-done" if es_ok else "badge-cancel"
            st.markdown(
                f'<div class="hist-item">'
                f'{emoji_hist} <strong>{row["Motivo"]}</strong> — por {row["Creador"]} '
                f'<span class="badge {badge_class}">{row["Estado"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — NUEVA JUNTADA
# ════════════════════════════════════════════════════════════════════════════════
with tab_nueva:
    st.subheader("🎉 Agitar una nueva Juntada")
    st.write(f"Hola **{usuario_actual}** 👋 — tirá la idea y que los pibes respondan.")

    with st.form("form_crear_evento", clear_on_submit=True):
        motivo_input = st.text_input(
            "🎯 ¿Qué hacemos?",
            placeholder="Ej: Asadazo de fin de mes, Partido de Padel...",
        )
        col_f, col_l = st.columns(2)
        with col_f:
            fechas_input = st.text_input(
                "📅 Fechas posibles",
                placeholder="Separá con coma: Viernes 12, Sábado 13",
            )
        with col_l:
            lugares_input = st.text_input(
                "📍 Lugares posibles",
                placeholder="Separá con coma: Lo de Chicho, Bar del centro",
            )
        submitted = st.form_submit_button(
            "🚀 ¡Crear y abrir votación!",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        errores = [
            e for cond, e in [
                (not motivo_input.strip(),  "Escribí de qué va la juntada."),
                (not fechas_input.strip(),  "Poné al menos una fecha posible."),
                (not lugares_input.strip(), "Poné al menos un lugar posible."),
            ] if cond
        ]
        if errores:
            for e in errores:
                st.error(f"❌ {e}")
        else:
            nuevo_id = crear_evento(motivo_input.strip(), usuario_actual)
            for f in [x.strip() for x in fechas_input.split(",") if x.strip()]:
                agregar_opcion(nuevo_id, "Fecha", f)
            for lu in [x.strip() for x in lugares_input.split(",") if x.strip()]:
                agregar_opcion(nuevo_id, "Lugar", lu)
            # Las 3 modalidades se crean automáticamente en cada juntada
            for m in ["Solos", "En pareja", "En familia"]:
                agregar_opcion(nuevo_id, "Modalidad", m)
            st.success(f"🎉 ¡Juntada **'{motivo_input.strip()}'** creada!")
            st.info("Andá al **Tablero** 👆 y respondé tu disponibilidad.")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — ESTADÍSTICAS
# ════════════════════════════════════════════════════════════════════════════════
with tab_stats:
    st.subheader("📊 Estadísticas del Quincho")
    st.caption("Quién pone la casa, quién participa y quién se baja a último momento.")

    df_stats = obtener_estadisticas_quincho()

    if df_stats["Votos Emitidos"].sum() == 0:
        st.info("Todavía no hay actividad suficiente. ¡Empiecen a votar!")
    else:
        mvp       = df_stats.loc[df_stats["Juntadas Creadas"].idxmax()]
        participon = df_stats.loc[df_stats["Votos Emitidos"].idxmax()]
        fantasma  = df_stats.loc[df_stats["Veces que Agitó Cancelar"].idxmax()]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🏆 MVP", mvp["Pibe"], f"{mvp['Juntadas Creadas']} juntadas")
        with col2:
            st.metric("📣 Más participativo", participon["Pibe"],
                      f"{participon['Votos Emitidos']} votos")
        with col3:
            st.metric("👻 El Fantasma", fantasma["Pibe"],
                      f"{fantasma['Veces que Agitó Cancelar']} fugas",
                      delta_color="inverse")

        st.markdown("---")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("**Juntadas creadas**")
            st.bar_chart(df_stats.set_index("Pibe")[["Juntadas Creadas"]], color="#FF8E53")
        with col_c2:
            st.markdown("**Votos emitidos**")
            st.bar_chart(df_stats.set_index("Pibe")[["Votos Emitidos"]], color="#818cf8")

        st.markdown("---")
        st.dataframe(
            df_stats.style.highlight_max(
                axis=0,
                subset=["Juntadas Creadas", "Votos Emitidos", "Veces que Agitó Cancelar"],
                color="#2d4a1e",
            ),
            hide_index=True,
        )
