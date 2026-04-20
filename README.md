# 🍻 La App de los Pibes - Organizador de Juntadas

¡Qué onda! Esta app está armada para que los pibes se pongan de acuerdo rápido para la juntada. Votar el día, el lugar y qué carajo hacer nunca fue tan fácil.

## Integrantes
Mauri, Chicho, Palomo, Luis, Cristian, Ova, Pochi, Sinchy.

## 🚀 Cómo correr esto en tu compu (Local)

1. Abrí la terminal y asegurate de tener python (y `pip`).
2. Instalale las dependencias (básicamente Streamlit y Pandas):
   ```bash
   pip install -r requirements.txt
   ```
3. Corré la app:
   ```bash
   streamlit run app.py
   ```
4. Se te abre en el navegador y ya podés empezar a tirar votos.

## ☁️ Instrucciones de Deploy en Streamlit Cloud

Para que todos los pibes lo puedan ver sin que tengas que tener tu compu prendida, subilo a la nube de Streamlit. Es re fácil y gratis.

1. **Subí el código a GitHub:**
   Corré el script de bash que armamos:
   ```bash
   bash deploy_to_github.sh
   ```
   (Te va a pedir tu URL de GitHub que armaste vacía, mandale mecha).

2. **Entrá a Streamlit Cloud:**
   Andá a [share.streamlit.io](https://share.streamlit.io/) y logueate con tu GitHub (si, el mismo donde subiste el código recién).

3. **Creá la App:**
   - Hacé click en "New app".
   - Elegí que querés usar un repo existente ("Use existing repo").
   - Buscá el repo que acabás de subir.
   - En el campo "Main file path", poné `app.py`.
   - Dale a "Deploy".

4. **¡Listo el pollo!**
   Esperá un cachito a que Streamlit prepare el horno, y te va a escupir una URL. Pasales ese link a los pibes por WhatsApp para que entren a votar.

---
**Data importante:** 
Como la app guarda los votos en CSVs adentro de `data/`, si la usás en Streamlit Cloud, los datos van a durar lo que dure el contenedor (se pueden borrar si la app se suspende). Para uso entre amigos sirve de diez, pero si la escala crece, habría que meterle alguna base de datos en la nube. ¡Por ahora, para la previa, va como piña!
