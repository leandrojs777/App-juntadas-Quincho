import uuid
import pandas as pd
import streamlit as st
import gspread

UMBRAL_CANCELACION = 4

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

COLS_EVENTOS  = ["ID_Evento", "Motivo", "Creador", "Estado"]
COLS_OPCIONES = ["ID_Evento", "Categoria", "Opcion"]
COLS_VOTOS    = ["ID_Evento", "Usuario", "Categoria", "Opcion", "Puntos"]


# ── Conexión a Google Sheets ──────────────────────────────────────────────────

@st.cache_resource
def _get_client() -> gspread.Client:
    """Devuelve un cliente gspread autenticado con refresh automático de token."""
    return gspread.service_account_from_dict(
        st.secrets["gcp_service_account"],
        scopes=SCOPES,
    )


def _get_sheet(sheet_name: str) -> gspread.Worksheet:
    """Retorna la hoja (pestaña) indicada dentro del spreadsheet configurado."""
    client = _get_client()
    spreadsheet_id = st.secrets["sheets"]["spreadsheet_id"]
    spreadsheet = client.open_by_key(spreadsheet_id)
    return spreadsheet.worksheet(sheet_name)


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _invalidar_cache():
    """Limpia el cache de datos de Streamlit para forzar re-lectura desde Sheets."""
    st.cache_data.clear()


def _cargar_df(sheet_name: str, columns: list) -> pd.DataFrame:
    """Lee una hoja de Google Sheets y la devuelve como DataFrame."""
    try:
        sheet = _get_sheet(sheet_name)
        records = sheet.get_all_records(expected_headers=columns)
        if not records:
            return pd.DataFrame(columns=columns)
        df = pd.DataFrame(records)
        # Asegurar que todas las columnas esperadas existan
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        if "Puntos" in df.columns:
            df["Puntos"] = pd.to_numeric(df["Puntos"], errors="coerce").fillna(0).astype(int)
        return df[columns]
    except Exception:
        return pd.DataFrame(columns=columns)


def _guardar_df(sheet_name: str, df: pd.DataFrame):
    """Sobrescribe la hoja de Google Sheets con el contenido del DataFrame."""
    sheet = _get_sheet(sheet_name)
    # Limpiar toda la hoja y reescribir desde fila 1
    sheet.clear()
    # Escribir headers + datos
    data = [df.columns.tolist()] + df.astype(str).values.tolist()
    sheet.update(data, "A1")


# ── Init ──────────────────────────────────────────────────────────────────────

def inicializar_datos():
    """Crea las hojas necesarias si no existen y verifica sus headers. Idempotente."""
    client = _get_client()
    spreadsheet_id = st.secrets["sheets"]["spreadsheet_id"]
    spreadsheet = client.open_by_key(spreadsheet_id)
    existing_titles = [ws.title for ws in spreadsheet.worksheets()]

    sheets_needed = [
        ("eventos",  COLS_EVENTOS),
        ("opciones", COLS_OPCIONES),
        ("votos",    COLS_VOTOS),
    ]

    for sheet_name, cols in sheets_needed:
        if sheet_name not in existing_titles:
            # Si existe "Hoja 1" (hoja por defecto vacía), renombrarla
            if "Hoja 1" in existing_titles and sheets_needed.index((sheet_name, cols)) == 0:
                ws = spreadsheet.worksheet("Hoja 1")
                ws.update_title(sheet_name)
                existing_titles = [sheet_name if t == "Hoja 1" else t for t in existing_titles]
            else:
                ws = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=len(cols))
            ws.append_row(cols)
        else:
            ws = spreadsheet.worksheet(sheet_name)
            if not ws.row_values(1):
                ws.append_row(cols)


# ── Lectura con caché (TTL=5s) ────────────────────────────────────────────────

@st.cache_data(ttl=5)
def cargar_eventos() -> pd.DataFrame:
    return _cargar_df("eventos", COLS_EVENTOS)


@st.cache_data(ttl=5)
def cargar_opciones() -> pd.DataFrame:
    return _cargar_df("opciones", COLS_OPCIONES)


@st.cache_data(ttl=5)
def cargar_votos() -> pd.DataFrame:
    return _cargar_df("votos", COLS_VOTOS)


# ── Eventos ───────────────────────────────────────────────────────────────────

def crear_evento(motivo: str, creador: str) -> str:
    """Crea un nuevo evento y devuelve su ID."""
    id_evento = str(uuid.uuid4())[:8]
    sheet = _get_sheet("eventos")
    sheet.append_row([id_evento, motivo, creador, "Abierto"])
    _invalidar_cache()
    return id_evento


def cambiar_estado_evento(id_evento: str, estado_nuevo: str) -> bool:
    """Cambia el estado de un evento. Retorna True si fue exitoso."""
    df_eventos = _cargar_df("eventos", COLS_EVENTOS)
    mask = df_eventos["ID_Evento"] == id_evento

    if df_eventos[mask].empty:
        return False

    if estado_nuevo == "Concretado":
        df_votos = _cargar_df("votos", COLS_VOTOS)
        votos_reales = df_votos[
            (df_votos["ID_Evento"] == id_evento) &
            (df_votos["Categoria"] != "Estado")
        ]
        if votos_reales.empty:
            return False

    df_eventos.loc[mask, "Estado"] = estado_nuevo
    _guardar_df("eventos", df_eventos)
    _invalidar_cache()
    return True


def verificar_estado_evento(id_evento: str):
    """Auto-cancela el evento si se supera el umbral de cancelaciones."""
    df_eventos = _cargar_df("eventos", COLS_EVENTOS)
    df_votos   = _cargar_df("votos", COLS_VOTOS)

    mask_cancelar = (
        (df_votos["ID_Evento"] == id_evento) &
        (df_votos["Categoria"] == "Estado") &
        (df_votos["Opcion"] == "Cancelar")
    )
    votos_cancelar = len(df_votos[mask_cancelar])

    mask_evento = df_eventos["ID_Evento"] == id_evento
    if not df_eventos[mask_evento].empty and votos_cancelar >= UMBRAL_CANCELACION:
        df_eventos.loc[mask_evento, "Estado"] = "Cancelado"
        _guardar_df("eventos", df_eventos)
        _invalidar_cache()


# ── Opciones ──────────────────────────────────────────────────────────────────

def agregar_opcion(id_evento: str, categoria: str, opcion: str):
    """Agrega una opción al evento evitando duplicados."""
    df = cargar_opciones()
    mask = (
        (df["ID_Evento"] == id_evento) &
        (df["Categoria"] == categoria) &
        (df["Opcion"] == opcion)
    )
    if df[mask].empty:
        sheet = _get_sheet("opciones")
        sheet.append_row([id_evento, categoria, opcion])
        _invalidar_cache()


def obtener_opciones_evento(id_evento: str) -> dict:
    """Retorna {Fecha: [...], Lugar: [...], Modalidad: [...]} para el evento dado."""
    df = cargar_opciones()
    if df.empty:
        return {"Fecha": [], "Lugar": [], "Modalidad": []}
    opciones = df[df["ID_Evento"] == id_evento]
    return {
        "Fecha":     opciones[opciones["Categoria"] == "Fecha"]["Opcion"].tolist(),
        "Lugar":     opciones[opciones["Categoria"] == "Lugar"]["Opcion"].tolist(),
        "Modalidad": opciones[opciones["Categoria"] == "Modalidad"]["Opcion"].tolist(),
    }


# ── Votos ─────────────────────────────────────────────────────────────────────

def registrar_voto(id_evento: str, usuario: str, categoria: str, opcion: str, puntos: int):
    """Registra o actualiza el voto de un usuario en una opción."""
    df = _cargar_df("votos", COLS_VOTOS)
    mask = (
        (df["ID_Evento"] == id_evento) &
        (df["Usuario"] == usuario) &
        (df["Categoria"] == categoria) &
        (df["Opcion"] == opcion)
    )
    if df[mask].empty:
        # Nuevo voto: append directo (más eficiente que reescribir todo)
        sheet = _get_sheet("votos")
        sheet.append_row([id_evento, usuario, categoria, opcion, int(puntos)])
    else:
        # Actualizar voto existente: requiere reescribir la hoja
        df.loc[mask, "Puntos"] = int(puntos)
        _guardar_df("votos", df)

    _invalidar_cache()
    verificar_estado_evento(id_evento)


def registrar_voto_cancelar(id_evento: str, usuario: str):
    """Registra que un usuario se baja del evento."""
    registrar_voto(id_evento, usuario, "Estado", "Cancelar", 1)


def registrar_voto_unico(id_evento: str, usuario: str, categoria: str, opcion: str, puntos: int = 1):
    """Para categorías de elección única: elimina votos previos del usuario en esa categoría."""
    df = _cargar_df("votos", COLS_VOTOS)
    mask_old = (
        (df["ID_Evento"] == id_evento) &
        (df["Usuario"] == usuario) &
        (df["Categoria"] == categoria)
    )
    df = df[~mask_old]
    nuevo = pd.DataFrame([{
        "ID_Evento": id_evento,
        "Usuario":   usuario,
        "Categoria": categoria,
        "Opcion":    opcion,
        "Puntos":    int(puntos),
    }])
    df = pd.concat([df, nuevo], ignore_index=True)
    _guardar_df("votos", df)
    _invalidar_cache()


def obtener_votos_usuario(id_evento: str, usuario: str) -> dict:
    """Retorna un dict {('Categoria', 'Opcion'): puntos} con todos los votos del usuario."""
    df = cargar_votos()
    if df.empty:
        return {}
    mask = (df["ID_Evento"] == id_evento) & (df["Usuario"] == usuario)
    return {
        (row["Categoria"], row["Opcion"]): row["Puntos"]
        for _, row in df[mask].iterrows()
    }


def obtener_cancelaciones_evento(id_evento: str) -> list:
    """Retorna lista de usuarios que votaron Cancelar en el evento."""
    df = cargar_votos()
    if df.empty:
        return []
    mask = (
        (df["ID_Evento"] == id_evento) &
        (df["Categoria"] == "Estado") &
        (df["Opcion"] == "Cancelar")
    )
    return df[mask]["Usuario"].tolist()


def obtener_resultados_evento(id_evento: str) -> pd.DataFrame:
    """Retorna DataFrame con puntaje acumulado por (Categoria, Opcion), ordenado desc."""
    df = cargar_votos()
    if df.empty:
        return pd.DataFrame()
    votos = df[
        (df["ID_Evento"] == id_evento) &
        (df["Categoria"] != "Estado")
    ]
    if votos.empty:
        return pd.DataFrame()
    resultado = votos.groupby(["Categoria", "Opcion"])["Puntos"].sum().reset_index()
    return resultado.sort_values(["Categoria", "Puntos"], ascending=[True, False])


# ── Estadísticas ──────────────────────────────────────────────────────────────

def obtener_estadisticas_quincho() -> pd.DataFrame:
    """Retorna DataFrame con métricas de participación por cada pibe."""
    df_eventos = cargar_eventos()
    df_votos   = cargar_votos()
    los_pibes  = ["Mauri", "Chicho", "Palomo", "Luis", "Cristian", "Ova", "Pochi", "Sinchy"]
    stats = []

    for pibe in los_pibes:
        creados   = len(df_eventos[df_eventos["Creador"] == pibe]) if not df_eventos.empty else 0
        emitidos  = len(df_votos[df_votos["Usuario"] == pibe]) if not df_votos.empty else 0
        cancelar  = len(df_votos[
            (df_votos["Usuario"] == pibe) & (df_votos["Opcion"] == "Cancelar")
        ]) if not df_votos.empty else 0
        positivos = len(df_votos[
            (df_votos["Usuario"] == pibe) &
            (df_votos["Puntos"] >= 3) &
            (df_votos["Categoria"] != "Estado")
        ]) if not df_votos.empty else 0
        negativos = len(df_votos[
            (df_votos["Usuario"] == pibe) &
            (df_votos["Puntos"] < 3) &
            (df_votos["Categoria"] != "Estado")
        ]) if not df_votos.empty else 0

        stats.append({
            "Pibe":                       pibe,
            "Juntadas Creadas":           creados,
            "Votos Emitidos":             emitidos,
            "Votos Positivos (3-5⭐)":   positivos,
            "Votos Negativos (1-2⭐)":   negativos,
            "Veces que Agitó Cancelar":   cancelar,
        })

    return pd.DataFrame(stats)
