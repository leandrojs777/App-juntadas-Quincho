import os
import uuid
import pandas as pd

DATA_DIR = 'data'
EVENTOS_FILE = os.path.join(DATA_DIR, 'eventos.csv')
OPCIONES_FILE = os.path.join(DATA_DIR, 'opciones.csv')
VOTOS_FILE = os.path.join(DATA_DIR, 'votos.csv')

UMBRAL_CANCELACION = 4

def inicializar_datos():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    if not os.path.exists(EVENTOS_FILE):
        pd.DataFrame(columns=['ID_Evento', 'Motivo', 'Creador', 'Estado']).to_csv(EVENTOS_FILE, index=False)
        
    if not os.path.exists(OPCIONES_FILE):
        pd.DataFrame(columns=['ID_Evento', 'Categoria', 'Opcion']).to_csv(OPCIONES_FILE, index=False)
        
    if not os.path.exists(VOTOS_FILE):
        pd.DataFrame(columns=['ID_Evento', 'Usuario', 'Categoria', 'Opcion', 'Puntos']).to_csv(VOTOS_FILE, index=False)

def _cargar_df(file_path, columns):
    try:
        df = pd.read_csv(file_path, dtype=str)
        # Convert numeric columns where applicable
        if 'Puntos' in df.columns:
            df['Puntos'] = pd.to_numeric(df['Puntos'], errors='coerce').fillna(0).astype(int)
        if df.empty:
            return pd.DataFrame(columns=columns)
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=columns)

def cargar_eventos():
    return _cargar_df(EVENTOS_FILE, ['ID_Evento', 'Motivo', 'Creador', 'Estado'])

def cargar_opciones():
    return _cargar_df(OPCIONES_FILE, ['ID_Evento', 'Categoria', 'Opcion'])

def cargar_votos():
    return _cargar_df(VOTOS_FILE, ['ID_Evento', 'Usuario', 'Categoria', 'Opcion', 'Puntos'])

def crear_evento(motivo, creador):
    df_eventos = cargar_eventos()
    id_evento = str(uuid.uuid4())[:8]
    nuevo_evento = pd.DataFrame([{
        'ID_Evento': id_evento,
        'Motivo': motivo,
        'Creador': creador,
        'Estado': 'Abierto'
    }])
    df_eventos = pd.concat([df_eventos, nuevo_evento], ignore_index=True)
    df_eventos.to_csv(EVENTOS_FILE, index=False)
    return id_evento

def agregar_opcion(id_evento, categoria, opcion):
    df_opciones = cargar_opciones()
    
    # Evitar duplicados
    mask = (df_opciones['ID_Evento'] == id_evento) & (df_opciones['Categoria'] == categoria) & (df_opciones['Opcion'] == opcion)
    if df_opciones[mask].empty:
        nueva_opcion = pd.DataFrame([{
            'ID_Evento': id_evento,
            'Categoria': categoria,
            'Opcion': opcion
        }])
        df_opciones = pd.concat([df_opciones, nueva_opcion], ignore_index=True)
        df_opciones.to_csv(OPCIONES_FILE, index=False)

def obtener_opciones_evento(id_evento):
    df = cargar_opciones()
    if df.empty:
        return {'Fecha': [], 'Lugar': []}
    
    opciones = df[df['ID_Evento'] == id_evento]
    return {
        'Fecha': opciones[opciones['Categoria'] == 'Fecha']['Opcion'].tolist(),
        'Lugar': opciones[opciones['Categoria'] == 'Lugar']['Opcion'].tolist()
    }

def registrar_voto(id_evento, usuario, categoria, opcion, puntos):
    df_votos = cargar_votos()
    
    mask = (df_votos['ID_Evento'] == id_evento) & (df_votos['Usuario'] == usuario) & (df_votos['Categoria'] == categoria) & (df_votos['Opcion'] == opcion)
    
    if df_votos[mask].empty:
        nuevo_voto = pd.DataFrame([{
            'ID_Evento': id_evento,
            'Usuario': usuario,
            'Categoria': categoria,
            'Opcion': opcion,
            'Puntos': int(puntos)
        }])
        df_votos = pd.concat([df_votos, nuevo_voto], ignore_index=True)
    else:
        df_votos.loc[mask, 'Puntos'] = int(puntos)
        
    df_votos.to_csv(VOTOS_FILE, index=False)
    verificar_estado_evento(id_evento)

def registrar_voto_cancelar(id_evento, usuario):
    registrar_voto(id_evento, usuario, 'Estado', 'Cancelar', 1)

def verificar_estado_evento(id_evento):
    df_eventos = cargar_eventos()
    df_votos = cargar_votos()
    
    # Verificar cuántos votos "Cancelar" hay
    mask_cancelar = (df_votos['ID_Evento'] == id_evento) & (df_votos['Categoria'] == 'Estado') & (df_votos['Opcion'] == 'Cancelar')
    votos_cancelar = len(df_votos[mask_cancelar])
    
    mask_evento = (df_eventos['ID_Evento'] == id_evento)
    if not df_eventos[mask_evento].empty:
        if votos_cancelar >= UMBRAL_CANCELACION:
            df_eventos.loc[mask_evento, 'Estado'] = 'Cancelado'
            df_eventos.to_csv(EVENTOS_FILE, index=False)

def cambiar_estado_evento(id_evento, estado_nuevo):
    df_eventos = cargar_eventos()
    mask_evento = (df_eventos['ID_Evento'] == id_evento)
    if not df_eventos[mask_evento].empty:
        df_eventos.loc[mask_evento, 'Estado'] = estado_nuevo
        df_eventos.to_csv(EVENTOS_FILE, index=False)

def obtener_resultados_evento(id_evento):
    df_votos = cargar_votos()
    if df_votos.empty:
        return pd.DataFrame()
        
    votos_evento = df_votos[(df_votos['ID_Evento'] == id_evento) & (df_votos['Categoria'] != 'Estado')]
    if votos_evento.empty:
        return pd.DataFrame()
        
    resultados = votos_evento.groupby(['Categoria', 'Opcion'])['Puntos'].sum().reset_index()
    resultados = resultados.sort_values(['Categoria', 'Puntos'], ascending=[True, False])
    return resultados

def obtener_cancelaciones_evento(id_evento):
    df_votos = cargar_votos()
    if df_votos.empty:
        return []
    mask = (df_votos['ID_Evento'] == id_evento) & (df_votos['Categoria'] == 'Estado') & (df_votos['Opcion'] == 'Cancelar')
    return df_votos[mask]['Usuario'].tolist()

def obtener_estadisticas_quincho():
    df_eventos = cargar_eventos()
    df_votos = cargar_votos()
    
    stats = []
    # Lista default (hardcoded just for safety but should use app list)
    los_pibes = ["Mauri", "Chicho", "Palomo", "Luis", "Cristian", "Ova", "Pochi", "Sinchy"]
    
    for pibe in los_pibes:
        eventos_creados = len(df_eventos[df_eventos['Creador'] == pibe]) if not df_eventos.empty else 0
        votos_totales = len(df_votos[df_votos['Usuario'] == pibe]) if not df_votos.empty else 0
        votos_cancelar = len(df_votos[(df_votos['Usuario'] == pibe) & (df_votos['Opcion'] == 'Cancelar')]) if not df_votos.empty else 0
        votos_positivos = len(df_votos[(df_votos['Usuario'] == pibe) & (df_votos['Puntos'] >= 3) & (df_votos['Categoria'] != 'Estado')]) if not df_votos.empty else 0
        votos_negativos = len(df_votos[(df_votos['Usuario'] == pibe) & (df_votos['Puntos'] < 3) & (df_votos['Categoria'] != 'Estado')]) if not df_votos.empty else 0
        
        stats.append({
            'Pibe': pibe,
            'Juntadas Creadas': eventos_creados,
            'Votos Emitidos': votos_totales,
            'Votos Positivos (3-5⭐)': votos_positivos,
            'Votos Negativos (1-2⭐)': votos_negativos,
            'Veces que Agitó Cancelar': votos_cancelar
        })
        
    return pd.DataFrame(stats)
