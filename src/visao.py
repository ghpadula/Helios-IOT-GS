"""Sprint 2 — Medição de sujeira por visão.

Transforma um frame BGR num número `grauSujeira` ∈ [0, 1]:
    0.0 = painel limpo   |   1.0 = totalmente coberto de poeira.

Dois métodos complementares:
  1. Heurística HSV (sem calibração): poeira lunar/terrestre aparece CLARA e
     DESSATURADA (cinza/areia), enquanto o painel limpo é escuro e/ou azulado.
     Contamos a fração de pixels "claros + sem cor".
  2. Baseline (com calibração): guardamos um frame do painel limpo e medimos
     quanto o brilho aumentou em relação a ele — mais robusto a cor do painel.

Uma média móvel suaviza a leitura para não oscilar a cada frame (estabilidade
temporal, importante para a decisão e para o vídeo).
"""

from __future__ import annotations

from collections import deque
from typing import Optional

import cv2
import numpy as np

from .config import ConfigVisao


class MedidorSujeira:
    """Calcula o grauSujeira de um painel a partir de frames da webcam."""

    def __init__(self, cfg: ConfigVisao) -> None:
        self.cfg = cfg
        self._baseline_cinza: Optional[np.ndarray] = None
        self._historico: deque[float] = deque(maxlen=cfg.janela_suavizacao)
        self.ultima_mascara: Optional[np.ndarray] = None  # p/ debug/HUD

    # ------------------------------------------------------------ calibração
    @property
    def calibrado(self) -> bool:
        return self._baseline_cinza is not None

    def calibrar(self, frame: np.ndarray) -> None:
        """Registra o frame atual como referência de painel LIMPO."""
        cinza = self._preparar_cinza(frame)
        self._baseline_cinza = cinza
        self._historico.clear()

    def resetar(self) -> None:
        """Descarta a calibração (volta para a heurística HSV)."""
        self._baseline_cinza = None
        self._historico.clear()

    # ----------------------------------------------------------- pré-processo
    def _preparar_cinza(self, frame: np.ndarray) -> np.ndarray:
        """Converte para cinza e aplica leve blur (reduz ruído de pixel)."""
        cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        k = max(1, self.cfg.blur_kernel | 1)  # garante kernel ímpar
        return cv2.GaussianBlur(cinza, (k, k), 0)

    # --------------------------------------------------------------- métodos
    def _medir_hsv(self, frame: np.ndarray) -> tuple[float, np.ndarray]:
        """Fração de pixels claros e dessaturados (poeira). Sem calibração."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        s = hsv[:, :, 1]
        v = hsv[:, :, 2]
        # Poeira = saturação baixa  E  valor (brilho) alto.
        mascara = (s < self.cfg.saturacao_max_poeira) & (v > self.cfg.valor_min_poeira)
        mascara = mascara.astype(np.uint8) * 255
        grau = float(np.count_nonzero(mascara)) / mascara.size
        return grau, mascara

    def _medir_baseline(self, frame: np.ndarray) -> tuple[float, np.ndarray]:
        """Fração de pixels que ficaram mais claros que o painel limpo."""
        assert self._baseline_cinza is not None
        cinza = self._preparar_cinza(frame)
        # Diferença assinada: poeira só ADICIONA brilho (claro sobre escuro).
        diff = cv2.subtract(cinza, self._baseline_cinza)
        mascara = (diff > self.cfg.limiar_diff_baseline).astype(np.uint8) * 255
        # Limpeza morfológica: remove pontos isolados de ruído.
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        grau = float(np.count_nonzero(mascara)) / mascara.size
        return grau, mascara

    # ----------------------------------------------------------------- medir
    def medir(self, frame: np.ndarray) -> float:
        """Mede o grauSujeira do frame e devolve o valor suavizado ∈ [0, 1]."""
        if self.calibrado:
            grau, mascara = self._medir_baseline(frame)
        else:
            grau, mascara = self._medir_hsv(frame)

        self.ultima_mascara = mascara
        grau = float(np.clip(grau, 0.0, 1.0))

        # Suavização temporal (média móvel) para estabilizar a leitura.
        self._historico.append(grau)
        return float(np.mean(self._historico))

    @property
    def metodo(self) -> str:
        return "baseline" if self.calibrado else "hsv"
