import os
import uuid
import pandas as pd
import streamlit as st

DATA_DIR = 'data'
EVENTOS_FILE = os.path.join(DATA_DIR, 'eventos.csv')
OPCIONES_FILE = os.path.join(DATA_DIR, 'opciones.csv')
VOTOS_FILE = os.path.join(DATA_DIR, 'votos.csv')

UMBRAL_CANCELACION = 4


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _invalidar_cache():
    """Limpia el cache de Streamlit después de cada operación de escritura.
    Fuerza que la próxima lectura vaya al disco con datos frescos."""
    st.cache_data.clear()


def _cargar_df(file_path: str, columns: list) -> pd.DataFrame:
    """Cargador base tolerante a archivos vacíos o inexistentes."""
    try:
        df = pd.read_csv(file_path, dtype=str)
        if 'Puntos' in df.columns:
            df['Puntos'] = pd.to_numeric(df['Puntos'], errors='coerce').fillna(0).astype(int)
        if df.empty:
            return pd.DataFrame(columns=columns)
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=columns)


# ── Init ──────────────────────────────────────────────────────────────────────

def inicializar_datos():
    """Crea el directorio y los CSVs si no existen. Idempotente."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    if not os.path.exists(EVENTOS_FILE):
        pd.DataFrame(columns=['ID_Evento', 'Motivo', 'Creador', 'Estado']).to_csv(EVENTOS_FILE, index=False)

    if not os.path.exists(OPCIONES_FILE):
        pd.DataFrame(columns=['ID_Evento', 'Categoria', 'Opcion']).to_csv(OPCIONES_FILE, index=False)

    if not os.path.exists(VOTOS_FILE):
        pd.DataFrame(columns=['ID_Evento', 'Usuario', 'Categoria', 'Opcion', 'Puntos']).to_csv(VOTOS_FILE, index=False)


# ── Lectura con caché (TTL=5s) ────────────────────────────────────────────────
# Cada write llama a _invalidar_cache() para forzar re-lectura inmediata.

@st.cache_data(ttl=5)
def cargar_eventos() -> pd.DataFrame:
    return _cargar_df(EVENTOS_FILE, ['ID_Evento', 'Motivo', 'Creador', 'Estado'])


@st.cache_data(ttl=5)
def cargar_opciones() -> pd.DataFrame:
    return _cargar_df(OPCIONES_FILE, ['ID_Evento', 'Categoria', 'Opcion'])


@st.cache_data(ttl=5)
def cargar_votos() -> pd.DataFrame:
    return _cargar_df(VOTOS_FILE, ['ID_Evento', 'Usuario', 'Categoria', 'Opcion', 'Puntos'])


# ── Eventos ───────────────────────────────────────────────────────────────────

def crear_evento(motivo: str, creador: str) -> str:
    """Crea un nuevo evento y devuelve su ID."""
    df = cargar_eventos()
    id_evento = str(uuid.uuid4())[:8]
    nuevo = pd.DataFrame([{
        'ID_Evento': id_evento,
        'Motivo': motivo,
        'Creador': creador,
        'Estado': 'Abierto',
    }])
    df = pd.concat([df, nuevo], ignore_index=True)
    df.to_csv(EVENTOS_FILE, index=False)
    _invalidar_cache()
    return id_evento


def cambiar_estado_evento(id_evento: str, estado_nuevo: str) -> bool:
    """Cambia el estado de un evento.
    Para 'Concretado', valida que haya al menos un voto registrado.
    Retorna True si el cambio fue exitoso, False si no se pudo.
    """
    df_eventos = cargar_eventos()
    mask = df_eventos['ID_Evento'] == id_evento

    if df_eventos[mask].empty:
        return False

    if estado_nuevo == 'Concretado':
        df_votos = cargar_votos()
        votos_reales = df_votos[
            (df_votos['ID_Evento'] == id_evento) &
            (df_votos['Categoria'] != 'Estado')
        ]
        if votos_reales.empty:
            return False  # No se puede concretar sin votos

    df_eventos.loc[mask, 'Estado'] = estado_nuevo
    df_eventos.to_csv(EVENTOS_FILE, index=False)
    _invalidar_cache()
    return True


def verificar_estado_evento(id_evento: str):
    """Auto-cancela el evento si se supera el umbral de cancelaciones."""
    df_eventos = cargar_eventos()
    df_votos = cargar_votos()

    mask_cancelar = (
        (df_votos['ID_Evento'] == id_evento) &
        (df_votos['Categoria'] == 'Estado') &
        (df_votos['Opcion'] == 'Cancelar')
    )
    votos_cancelar = len(df_votos[mask_cancelar])

    mask_evento = df_eventos['ID_Evento'] == id_evento
    if not df_eventos[mask_evento].empty and votos_cancelar >= UMBRAL_CANCELACION:
        df_eventos.loc[mask_evento, 'Estado'] = 'Cancelado'
        df_eventos.to_csv(EVENTOS_FILE, index=False)
        _invalidar_cache()


# ── Opciones ──────────────────────────────────────────────────────────────────

def agregar_opcion(id_evento: str, categoria: str, opcion: str):
    """Agrega una opción al evento evitando duplicados."""
    df = cargar_opciones()
    mask = (
        (df['ID_Evento'] == id_evento) &
        (df['Categoria'] == categoria) &
        (df['Opcion'] == opcion)
    )
    if df[mask].empty:
        nueva = pd.DataFrame([{'ID_Evento': id_evento, 'Categoria': categoria, 'Opcion': opcion}])
        df = pd.concat([df, nueva], ignore_index=True)
        df.to_csv(OPCIONES_FILE, index=False)
        _invalidar_cache()


def obtener_opciones_evento(id_evento: str) -> dict:
    """Retorna {Fecha: [...], Lugar: [...], Modalidad: [...]} para el evento dado."""
    df = cargar_opciones()
    if df.empty:
        return {'Fecha': [], 'Lugar': [], 'Modalidad': []}
    opciones = df[df['ID_Evento'] == id_evento]
    return {
        'Fecha':     opciones[opciones['Categoria'] == 'Fecha']['Opcion'].tolist(),
        'Lugar':     opciones[opciones['Categoria'] == 'Lugar']['Opcion'].tolist(),
        'Modalidad': opciones[opciones['Categoria'] == 'Modalidad']['Opcion'].tolist(),
    }


# ── Votos ─────────────────────────────────────────────────────────────────────

def registrar_voto(id_evento: str, usuario: str, categoria: str, opcion: str, puntos: int):
    """Registra o actualiza el voto de un usuario en una opción. Luego verifica auto-cancelación."""
    df = cargar_votos()
    mask = (
        (df['ID_Evento'] == id_evento) &
        (df['Usuario'] == usuario) &
        (df['Categoria'] == categoria) &
        (df['Opcion'] == opcion)
    )
    if df[mask].empty:
        nuevo = pd.DataFrame([{
            'ID_Evento': id_evento,
            'Usuario': usuario,
            'Categoria': categoria,
            'Opcion': opcion,
            'Puntos': int(puntos),
        }])
        df = pd.concat([df, nuevo], ignore_index=True)
    else:
        df.loc[mask, 'Puntos'] = int(puntos)

    df.to_csv(VOTOS_FILE, index=False)
    _invalidar_cache()
    verificar_estado_evento(id_evento)


def registrar_voto_cancelar(id_evento: str, usuario: str):
    """Registra que un usuario se bata del evento."""
    registrar_voto(id_evento, usuario, 'Estado', 'Cancelar', 1)


def registrar_voto_unico(id_evento: str, usuario: str, categoria: str, opcion: str, puntos: int = 1):
    """Para categorías de elección única (ej: Modalidad): elimina votos previos
    del usuario en esa categoría antes de guardar el nuevo, evitando duplicados."""
    df = cargar_votos()
    # Borrar cualquier voto previo del usuario en esta categoría
    mask_old = (
        (df['ID_Evento'] == id_evento) &
        (df['Usuario'] == usuario) &
        (df['Categoria'] == categoria)
    )
    df = df[~mask_old]
    # Insertar el nuevo voto
    nuevo = pd.DataFrame([{
        'ID_Evento': id_evento,
        'Usuario':   usuario,
        'Categoria': categoria,
        'Opcion':    opcion,
        'Puntos':    int(puntos),
    }])
    df = pd.concat([df, nuevo], ignore_index=True)
    df.to_csv(VOTOS_FILE, index=False)
    _invalidar_cache()


def obtener_votos_usuario(id_evento: str, usuario: str) -> dict:
    """Retorna un dict {('Categoria', 'Opcion'): puntos} con todos los votos del usuario.
    Usado para pre-popular los sliders con valores ya existentes.
    """
    df = cargar_votos()
    if df.empty:
        return {}
    mask = (df['ID_Evento'] == id_evento) & (df['Usuario'] == usuario)
    return {
        (row['Categoria'], row['Opcion']): row['Puntos']
        for _, row in df[mask].iterrows()
    }


def obtener_cancelaciones_evento(id_evento: str) -> list:
    """Retorna lista de usuarios que votaron Cancelar en el evento."""
    df = cargar_votos()
    if df.empty:
        return []
    mask = (
        (df['ID_Evento'] == id_evento) &
        (df['Categoria'] == 'Estado') &
        (df['Opcion'] == 'Cancelar')
    )
    return df[mask]['Usuario'].tolist()


def obtener_resultados_evento(id_evento: str) -> pd.DataFrame:
    """Retorna DataFrame con puntaje acumulado por (Categoria, Opcion), ordenado desc."""
    df = cargar_votos()
    if df.empty:
        return pd.DataFrame()
    votos = df[
        (df['ID_Evento'] == id_evento) &
        (df['Categoria'] != 'Estado')
    ]
    if votos.empty:
        return pd.DataFrame()
    resultado = votos.groupby(['Categoria', 'Opcion'])['Puntos'].sum().reset_index()
    return resultado.sort_values(['Categoria', 'Puntos'], ascending=[True, False])


# ── Estadísticas ──────────────────────────────────────────────────────────────

def obtener_estadisticas_quincho() -> pd.DataFrame:
    """Retorna DataFrame con métricas de participación por cada pibe."""
    df_eventos = cargar_eventos()
    df_votos = cargar_votos()
    los_pibes = ["Mauri", "Chicho", "Palomo", "Luis", "Cristian", "Ova", "Pochi", "Sinchy"]
    stats = []

    for pibe in los_pibes:
        creados = len(df_eventos[df_eventos['Creador'] == pibe]) if not df_eventos.empty else 0
        emitidos = len(df_votos[df_votos['Usuario'] == pibe]) if not df_votos.empty else 0
        cancelar = len(df_votos[
            (df_votos['Usuario'] == pibe) & (df_votos['Opcion'] == 'Cancelar')
        ]) if not df_votos.empty else 0
        positivos = len(df_votos[
            (df_votos['Usuario'] == pibe) &
            (df_votos['Puntos'] >= 3) &
            (df_votos['Categoria'] != 'Estado')
        ]) if not df_votos.empty else 0
        negativos = len(df_votos[
            (df_votos['Usuario'] == pibe) &
            (df_votos['Puntos'] < 3) &
            (df_votos['Categoria'] != 'Estado')
        ]) if not df_votos.empty else 0

        stats.append({
            'Pibe': pibe,
            'Juntadas Creadas': creados,
            'Votos Emitidos': emitidos,
            'Votos Positivos (3-5⭐)': positivos,
            'Votos Negativos (1-2⭐)': negativos,
            'Veces que Agitó Cancelar': cancelar,
        })

    return pd.DataFrame(stats)
