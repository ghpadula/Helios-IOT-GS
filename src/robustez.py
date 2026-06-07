"""Sprint 4 — Robustez (luz fraca, ruído e oclusão parcial).

O briefing pontua a solução funcionar sob condições ruins. Aqui tratamos:
  - LUZ FRACA: CLAHE (equalização de histograma adaptativa) realça o painel.
  - RUÍDO:     filtro bilateral suaviza preservando bordas.
  - OCLUSÃO:   se algo (mão/objeto) tampa boa parte da câmera, detectamos e
               congelamos a medição para não gerar leitura/alerta falso.
"""

from __future__ import annotations

import cv2
import numpy as np

from .config import ConfigRobustez


class PreProcessador:
    """Prepara o frame para a medição e detecta oclusão."""

    def __init__(self, cfg: ConfigRobustez) -> None:
        self.cfg = cfg
        self._clahe = cv2.createCLAHE(
            clipLimit=cfg.clahe_clip,
            tileGridSize=(cfg.clahe_grid, cfg.clahe_grid),
        )

    def realcar(self, frame: np.ndarray) -> np.ndarray:
        """Aplica CLAHE (luz fraca) + bilateral (ruído) e devolve o frame tratado."""
        out = frame
        if self.cfg.usar_clahe:
            # Equaliza só a luminância (canal L do LAB) — preserva as cores.
            lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l = self._clahe.apply(l)
            out = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
        if self.cfg.usar_bilateral:
            out = cv2.bilateralFilter(
                out, self.cfg.bilateral_d,
                self.cfg.bilateral_sigma, self.cfg.bilateral_sigma,
            )
        return out

    def ocluido(self, frame: np.ndarray) -> bool:
        """True se boa parte do frame está muito escura (provável oclusão)."""
        cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fracao_escura = float(np.mean(cinza < self.cfg.limiar_oclusao_escuro))
        return fracao_escura >= self.cfg.fracao_oclusao
