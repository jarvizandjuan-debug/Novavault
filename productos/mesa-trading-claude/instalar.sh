#!/usr/bin/env bash
# Instalador de la Mesa de Trading para Claude Code (macOS / Linux)
set -euo pipefail

ORIGEN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
MESA="${MESA_TRADING_HOME:-$HOME/mesa-trading}"

echo "== Mesa de Trading para Claude Code · instalador =="

PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
    PY="$(command -v "$c")"
    break
  fi
done
if [ -z "$PY" ]; then
  echo "✗ Necesitas Python 3.9 o superior: https://www.python.org/downloads/"
  exit 1
fi
echo "Python: $PY"

mkdir -p "$SKILLS_DEST" "$MESA"
for d in "$ORIGEN"/skills/*/; do
  n="$(basename "$d")"
  rm -rf "${SKILLS_DEST:?}/$n"
  cp -R "$d" "$SKILLS_DEST/$n"
  echo "  ✓ skill $n"
done

echo "Creando el entorno de Python en $MESA/.venv (1–2 minutos)..."
if ! "$PY" -m venv "$MESA/.venv"; then
  echo "✗ No pude crear el entorno virtual. En Ubuntu/Debian instala: sudo apt install python3-venv"
  exit 1
fi
"$MESA/.venv/bin/python" -m pip install --quiet --upgrade pip
"$MESA/.venv/bin/python" -m pip install --quiet -r "$ORIGEN/requirements.txt"

cat > "$MESA/py" <<'LANZADOR'
#!/usr/bin/env bash
exec "$(dirname "$0")/.venv/bin/python" "$@"
LANZADOR
chmod +x "$MESA/py"

"$MESA/py" "$SKILLS_DEST/configurar-mesa/scripts/configurar.py" inicializar >/dev/null
"$MESA/py" "$SKILLS_DEST/configurar-mesa/scripts/configurar.py" verificar || true

echo
echo "Listo. Abre Claude Code (o reinícialo si ya estaba abierto) y escribe:"
echo "  configura mi mesa de trading"
