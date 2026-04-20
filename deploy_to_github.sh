#!/bin/bash
# Script para iniciar repo, commitear y pushear los códigos de la Juntada

echo "¡Che, vamos a pushear esto a GitHub!"

# Iniciar o re-iniciar git
git init

# Agregar los archivos (menos los ignorados en .gitignore)
git add .

# Hacer el commit inicial
git commit -m "Commit Inicial: Dale que sale esa juntada"

# Asegurar que la rama principal sea main
git branch -M main

# Pedir la URL del repo de GitHub
echo "Pasame la URL del repo de GitHub (onda: https://github.com/tu-usuario/tu-repo.git):"
read REPO_URL

if [ -n "$REPO_URL" ]; then
    git remote add origin "$REPO_URL"
    echo "Mandando todo a la nube..."
    git push -u origin main
    echo "¡Listo papá! Ya tenés el código en GitHub. Ahora metete a Streamlit Cloud y conectá el repo."
else
    echo "No pusiste ni una URL, sos de terror. Tenés que agregar el origin a mano y pushear."
    echo "Comandos: git remote add origin URL && git push -u origin main"
fi
