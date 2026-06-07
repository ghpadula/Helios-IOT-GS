"""Sprint 5 — Simulador de painel (modo demo).

Permite rodar e GRAVAR O VÍDEO sem webcam/painel físico. Gera um painel solar
sintético (escuro, azulado, com grade de células) e vai acumulando "poeira"
clara por cima ao longo do tempo. Quando a vibração é acionada, a poeira
"cai" (o grau de sujeira diminui), fechando a malha visualmente.

Expõe a mesma interface mínima de leitura usada no loop (método `ler()`),
para o main tratar webcam e demo do mesmo jeito.
"""

from __future__ import annotations

import numpy as np
import cv2


class PainelSimulado:
    """Gera frames de um painel que suja com o tempo e limpa ao vibrar."""

    def __init__(self, largura: int = 640, altura: int = 480, seed: int = 7) -> None:
        self.w = largura
        self.h = altura
        self._rng = np.random.default_rng(seed)
        self._base = self._desenhar_painel_limpo()
        # Mapa de poeira (0..1 por pixel), começa limpo.
        self._poeira = np.zeros((altura, largura), dtype=np.float32)
        self._taxa_acumulo = 0.0009   # quão rápido suja por frame
        self._vibrando_frames = 0     # >0 enquanto a vibração "sacode" a poeira

    # ------------------------------------------------------------- desenho
    def _desenhar_painel_limpo(self) -> np.ndarray:
        """Painel escuro azulado com grade de células fotovoltaicas."""
        img = np.full((self.h, self.w, 3), (60, 35, 20), dtype=np.uint8)  # BGR escuro
        passo = 64
        for x in range(0, self.w, passo):
            cv2.line(img, (x, 0), (x, self.h), (90, 55, 30), 1)
        for y in range(0, self.h, passo):
            cv2.line(img, (0, y), (self.w, y), (90, 55, 30), 1)
        # leve brilho azul (reflexo de vidro)
        cv2.rectangle(img, (0, 0), (self.w, self.h), (110, 70, 35), 2)
        return img

    # ------------------------------------------------------------- dinâmica
    def acionar_vibracao(self, intensidade: float, duracao_frames: int = 45) -> None:
        """Sinaliza que o atuador vibrou — a poeira começa a se soltar."""
        self._vibrando_frames = max(self._vibrando_frames, duracao_frames)
        self._intensidade_vib = max(0.3, float(intensidade))

    def _evoluir_poeira(self) -> None:
        if self._vibrando_frames > 0:
            # Vibração: poeira escorrega/desliza para fora (cai pela inclinação).
            self._poeira *= (1.0 - 0.05 * self._intensidade_vib)
            self._poeira = np.roll(self._poeira, 2, axis=0)  # desliza p/ baixo
            self._vibrando_frames -= 1
        else:
            # Acúmulo gradual + manchas aleatórias de poeira.
            self._poeira += self._taxa_acumulo
            if self._rng.random() < 0.06:
                cx = int(self._rng.integers(0, self.w))
                cy = int(self._rng.integers(0, self.h))
                r = int(self._rng.integers(20, 70))
                mancha = np.zeros((self.h, self.w), dtype=np.float32)
                cv2.circle(mancha, (cx, cy), r, 0.4, -1)
                mancha = cv2.GaussianBlur(mancha, (31, 31), 0)
                self._poeira += mancha
        np.clip(self._poeira, 0.0, 1.0, out=self._poeira)

    def ler(self) -> np.ndarray:
        """Retorna o próximo frame BGR (painel + poeira atual)."""
        self._evoluir_poeira()
        frame = self._base.copy().astype(np.float32)
        # Poeira = camada clara/bege por cima, proporcional ao mapa.
        poeira_cor = np.dstack([self._poeira] * 3) * np.array([180, 200, 210])
        frame = frame * (1 - self._poeira[..., None] * 0.85) + poeira_cor * 0.85
        # ruído de sensor leve (deixa realista p/ a robustez aparecer)
        ruido = self._rng.normal(0, 4, frame.shape)
        frame = np.clip(frame + ruido, 0, 255).astype(np.uint8)
        return frame
