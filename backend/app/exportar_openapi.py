"""Exporta o contrato OpenAPI para o app gerar os tipos TypeScript.

Uso (a partir de backend/):  python -m app.exportar_openapi
Escreve ../mobile/openapi.json. Não precisa do banco: o contrato vem só dos modelos e rotas.
"""

import json
import sys
from pathlib import Path
from typing import cast

from app.core.config import Settings
from app.main import criar_app

DESTINO = Path(__file__).resolve().parents[2] / "mobile" / "openapi.json"


def gerar_contrato() -> str:
    # A URL não é usada: o pool só abre no lifespan, que não roda aqui.
    app = criar_app(Settings(api_database_url="postgresql://nao-usado@127.0.0.1:1/nao-usado"))
    contrato = cast(dict[str, object], app.openapi())
    return json.dumps(contrato, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> None:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else DESTINO
    destino.write_text(gerar_contrato(), encoding="utf-8")
    print(f"Contrato escrito em {destino}")


if __name__ == "__main__":
    main()
