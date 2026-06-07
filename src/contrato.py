"""Sprint 3 — Contrato de dados compartilhado (seção 6 do briefing).

Todas as matérias da GS usam o MESMO formato de JSON. Aqui modelamos os quatro
tipos que a visão produz/consome, garantindo coerência com Mobile, SOA e C#.

Exemplos do briefing:

    // Grau de sujeira (saída da visão)
    { "ativoId": "PAINEL-A", "grauSujeira": 0.47, "fonte": "visao",
      "timestamp": "2026-06-01T14:03:00Z" }

    // Alerta
    { "alertaId": "ALT-001", "ativoId": "PAINEL-A", "severidade": "ALTA",
      "tipo": "SUJEIRA_DETECTADA", "mensagem": "Cobertura de poeira > 40%",
      "timestamp": "2026-06-01T14:03:01Z", "resolvido": false }

    // Comando de limpeza (vibração modulada)
    { "comandoId": "CMD-77", "atuadorId": "VIB-PAINEL-A", "acao": "VIBRAR",
      "intensidade": 0.7, "duracaoSeg": 8, "alvoAtivoId": "PAINEL-A",
      "timestamp": "2026-06-01T14:03:02Z" }
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone


def agora_iso() -> str:
    """Timestamp UTC no formato do contrato: 2026-06-01T14:03:00Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class GrauSujeiraEvento:
    """Saída principal da visão — o que o resto do HÉLIOS consome."""

    ativoId: str
    grauSujeira: float
    fonte: str = "visao"
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "ativoId": self.ativoId,
            "grauSujeira": round(self.grauSujeira, 4),
            "fonte": self.fonte,
            "timestamp": self.timestamp or agora_iso(),
        }


@dataclass
class LeituraSensor:
    """Leitura genérica de sensor (a visão também é um 'sensor de sujeira')."""

    sensorId: str
    tipo: str
    valor: float
    unidade: str
    ativoId: str
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "sensorId": self.sensorId,
            "tipo": self.tipo,
            "valor": round(self.valor, 4),
            "unidade": self.unidade,
            "ativoId": self.ativoId,
            "timestamp": self.timestamp or agora_iso(),
        }


@dataclass
class Alerta:
    """Alerta gerado quando a sujeira passa do limite."""

    alertaId: str
    ativoId: str
    severidade: str          # "ALTA" | "MEDIA" | "BAIXA"
    tipo: str                # ex.: "SUJEIRA_DETECTADA"
    mensagem: str
    resolvido: bool = False
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "alertaId": self.alertaId,
            "ativoId": self.ativoId,
            "severidade": self.severidade,
            "tipo": self.tipo,
            "mensagem": self.mensagem,
            "timestamp": self.timestamp or agora_iso(),
            "resolvido": self.resolvido,
        }


@dataclass
class ComandoVibracao:
    """Comando de limpeza por vibração modulada (vai para o atuador via SOA)."""

    comandoId: str
    atuadorId: str
    intensidade: float       # 0..1
    duracaoSeg: int
    alvoAtivoId: str
    acao: str = "VIBRAR"
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "comandoId": self.comandoId,
            "atuadorId": self.atuadorId,
            "acao": self.acao,
            "intensidade": round(self.intensidade, 4),
            "duracaoSeg": self.duracaoSeg,
            "alvoAtivoId": self.alvoAtivoId,
            "timestamp": self.timestamp or agora_iso(),
        }


def to_json(evento) -> str:
    """Serializa qualquer evento do contrato em JSON compacto."""
    return json.dumps(evento.to_dict(), ensure_ascii=False)
