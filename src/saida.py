"""Sprint 3/5 — Saída / publicação dos eventos.

Imprime os eventos do contrato no console e persiste em JSON Lines (.jsonl).
Em produção, este ponto enviaria os eventos ao serviço SOA (REST/MQTT); aqui
simulamos com arquivo local — o formato é exatamente o do contrato (seção 6).
"""

from __future__ import annotations

import os
from typing import Optional

from .config import ConfigSaida
from .contrato import to_json


class Publicador:
    """Centraliza a emissão dos eventos (console + arquivo JSONL)."""

    def __init__(self, cfg: ConfigSaida) -> None:
        self.cfg = cfg
        os.makedirs(cfg.pasta_saida, exist_ok=True)
        self.caminho = os.path.join(cfg.pasta_saida, cfg.arquivo_eventos)
        # 'a' = append: não perde histórico entre execuções.
        self._arquivo = open(self.caminho, "a", encoding="utf-8")

    def publicar(self, evento, rotulo: str = "") -> None:
        """Serializa e emite um evento do contrato."""
        linha = to_json(evento)
        self._arquivo.write(linha + "\n")
        self._arquivo.flush()  # garante persistência mesmo se cair no meio
        if self.cfg.imprimir_console:
            prefixo = f"[{rotulo}] " if rotulo else ""
            print(prefixo + linha)

    def fechar(self) -> None:
        if not self._arquivo.closed:
            self._arquivo.close()

    def __enter__(self) -> "Publicador":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.fechar()
