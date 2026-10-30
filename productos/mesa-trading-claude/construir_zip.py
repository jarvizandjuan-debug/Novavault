"""Empaqueta el producto en dist/MesaTrading-ClaudeCode-v<versión>.zip."""
import sys
import zipfile
from pathlib import Path

VERSION = "1.0"
RAIZ = Path(__file__).resolve().parent
INCLUIR = ["README.md", "LICENCIA.txt", "requirements.txt", "instalar.sh", "instalar.ps1", "skills"]
CARPETA = "mesa-trading-claude"


def archivos():
    for nombre in INCLUIR:
        p = RAIZ / nombre
        if p.is_file():
            yield p
        else:
            for f in sorted(p.rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
                    yield f


def main():
    destino = RAIZ / "dist" / f"MesaTrading-ClaudeCode-v{VERSION}.zip"
    destino.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for f in archivos():
            info = zipfile.ZipInfo(f"{CARPETA}/{f.relative_to(RAIZ).as_posix()}", date_time=(2026, 10, 30, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if f.suffix in (".sh",) else 0o644) << 16
            z.writestr(info, f.read_bytes())
    print(f"{destino} ({destino.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    sys.exit(main())
