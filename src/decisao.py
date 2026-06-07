"""Sprint 3 — Motor de decisão.

Recebe o `grauSujeira` da visão e decide:
  - se está SUJO (acima do limiar) -> gera um Alerta;
  - quanto vibrar -> gera um ComandoVibracao com intensidade/duração proporcionais.

A regra de intensidade espelha de propósito a lógica C# do briefing
(`TarefaLimpeza.CalcularIntensidade`), para manter a integração coerente:

    if (grauSujeira < 0.15) return Nenhum();
    intensidade = clamp(grauSujeira, 0.3, 1.0);
    duracao = (int)(intensidade * 12);
"""

from __future__ import annotations

import itertools
import time
from typing import Optional

from .config import ConfigDecisao
from .contrato import Alerta, ComandoVibracao


class MotorDecisao:
    """Converte grauSujeira em alertas e comandos de vibração (malha fechada)."""

    def __init__(self, cfg: ConfigDecisao, ativo_id: str, atuador_id: str) -> None:
        self.cfg = cfg
        self.ativo_id = ativo_id
        self.atuador_id = atuador_id
        self._seq_alerta = itertools.count(1)
        self._seq_comando = itertools.count(1)
        self._ultimo_comando_ts = 0.0
        self.sujo = False  # estado atual (para o HUD)

    # --------------------------------------------------------------- sujeira
    def esta_sujo(self, grau: float) -> bool:
        return grau >= self.cfg.limiar_sujeira_detectada

    def _severidade(self, grau: float) -> str:
        if grau >= self.cfg.limiar_severidade_alta:
            return "ALTA"
        if grau >= self.cfg.limiar_severidade_media:
            return "MEDIA"
        return "BAIXA"

    def avaliar_alerta(self, grau: float) -> Optional[Alerta]:
        """Gera um Alerta apenas na TRANSIÇÃO limpo -> sujo (evita repetição)."""
        sujo_agora = self.esta_sujo(grau)
        alerta = None
        if sujo_agora and not self.sujo:
            pct = int(round(grau * 100))
            alerta = Alerta(
                alertaId=f"ALT-{next(self._seq_alerta):03d}",
                ativoId=self.ativo_id,
                severidade=self._severidade(grau),
                tipo="SUJEIRA_DETECTADA",
                mensagem=f"Cobertura de poeira ~{pct}%",
                resolvido=False,
            )
        self.sujo = sujo_agora
        return alerta

    # -------------------------------------------------------------- vibração
    def calcular_intensidade(self, grau: float) -> tuple[float, int]:
        """Replica CalcularIntensidade do C#. Retorna (intensidade, duracaoSeg)."""
        if grau < self.cfg.grau_minimo_para_vibrar:
            return 0.0, 0
        intensidade = max(self.cfg.intensidade_min, min(self.cfg.intensidade_max, grau))
        duracao = int(intensidade * self.cfg.fator_duracao_seg)
        return intensidade, duracao

    def avaliar_comando(self, grau: float) -> Optional[ComandoVibracao]:
        """Gera um ComandoVibracao se está sujo e respeitando o intervalo mínimo."""
        if not self.esta_sujo(grau):
            return None

        agora = time.monotonic()
        if agora - self._ultimo_comando_ts < self.cfg.intervalo_min_comando_seg:
            return None  # ainda no cooldown — não floodar o atuador

        intensidade, duracao = self.calcular_intensidade(grau)
        if intensidade <= 0.0:
            return None

        self._ultimo_comando_ts = agora
        return ComandoVibracao(
            comandoId=f"CMD-{next(self._seq_comando):02d}",
            atuadorId=self.atuador_id,
            intensidade=intensidade,
            duracaoSeg=duracao,
            alvoAtivoId=self.ativo_id,
        )
