"""Sprint 4 — HUD (overlay) desenhado sobre o vídeo.

É o que aparece na gravação: barra de sujeira, status (LIMPO/SUJO/OCLUÍDO),
FPS, método de medição e banner de alerta. Tudo com OpenCV (sem libs extras).

Paleta HÉLIOS (tema espacial): fundo escuro, ciano e âmbar.
"""

from __future__ import annotations

import cv2
import numpy as np

# Cores em BGR (OpenCV).
_PRETO = (18, 18, 24)
_BRANCO = (240, 240, 245)
_CIANO = (220, 200, 40)
_VERDE = (90, 200, 90)
_AMBAR = (40, 170, 240)
_VERMELHO = (60, 60, 230)
_CINZA = (120, 120, 130)


def _painel(img, x, y, w, h, cor=_PRETO, alpha=0.55):
    """Desenha um retângulo semitransparente (fundo de texto legível)."""
    sub = img[y:y + h, x:x + w]
    if sub.size == 0:
        return
    overlay = np.full_like(sub, cor)
    cv2.addWeighted(overlay, alpha, sub, 1 - alpha, 0, sub)


def desenhar(
    frame: np.ndarray,
    grau: float,
    metodo: str,
    fps: float,
    sujo: bool,
    ocluido: bool,
    calibrado: bool,
    limiar: float,
) -> np.ndarray:
    """Aplica o HUD do HÉLIOS sobre o frame e devolve a imagem anotada."""
    img = frame.copy()
    h, w = img.shape[:2]

    # ---- cabeçalho ----
    _painel(img, 0, 0, w, 40)
    cv2.putText(img, "HELIOS // Olhos - Physical Computing", (12, 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, _CIANO, 2, cv2.LINE_AA)
    cv2.putText(img, f"{fps:4.1f} FPS", (w - 110, 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, _BRANCO, 1, cv2.LINE_AA)

    # ---- status ----
    if ocluido:
        status, cor = "OCLUIDO", _AMBAR
    elif sujo:
        status, cor = "SUJO", _VERMELHO
    else:
        status, cor = "LIMPO", _VERDE

    _painel(img, 0, h - 70, w, 70)

    # barra de grau de sujeira
    bx, by, bw, bh = 12, h - 40, w - 130, 18
    cv2.rectangle(img, (bx, by), (bx + bw, by + bh), _CINZA, 1)
    preenchido = int(bw * float(np.clip(grau, 0, 1)))
    cv2.rectangle(img, (bx, by), (bx + preenchido, by + bh), cor, -1)
    # marcador do limiar
    lx = bx + int(bw * limiar)
    cv2.line(img, (lx, by - 3), (lx, by + bh + 3), _BRANCO, 1, cv2.LINE_AA)

    cv2.putText(img, f"grauSujeira: {grau:0.2f}", (bx, by - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, _BRANCO, 1, cv2.LINE_AA)
    cv2.putText(img, status, (w - 110, h - 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor, 2, cv2.LINE_AA)

    cal = "calibrado" if calibrado else "sem calibrar"
    cv2.putText(img, f"metodo: {metodo} ({cal})  |  c=calibrar  q=sair",
                (bx, h - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, _CINZA, 1, cv2.LINE_AA)

    # ---- banner de alerta ----
    if sujo and not ocluido:
        _painel(img, 0, 44, w, 30, cor=_VERMELHO, alpha=0.35)
        cv2.putText(img, "! SUJEIRA_DETECTADA -> acionando vibracao", (12, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, _BRANCO, 2, cv2.LINE_AA)

    return img


def aplicar_mascara(frame: np.ndarray, mascara: np.ndarray) -> np.ndarray:
    """Pinta de âmbar as regiões detectadas como poeira (debug visual no vídeo)."""
    if mascara is None:
        return frame
    img = frame.copy()
    realce = np.zeros_like(img)
    realce[mascara > 0] = _AMBAR
    return cv2.addWeighted(img, 1.0, realce, 0.35, 0)
