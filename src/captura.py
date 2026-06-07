"""Sprint 1 — Captura da webcam.

Responsável por abrir a webcam, entregar frames num loop eficiente e tratar as
duas exceções obrigatórias do briefing:
  - webcam desconectada  -> WebcamDesconectadaError (+ reconexão automática)
  - queda de frame        -> QuedaDeFrameError

Uso típico (context manager):

    with CapturaWebcam(cfg.captura) as cam:
        for frame in cam.frames():
            ...  # processa cada frame
"""

from __future__ import annotations

import time
from typing import Iterator, Optional

import cv2
import numpy as np

from .config import ConfigCaptura


class ErroCaptura(Exception):
    """Erro genérico da camada de captura."""


class WebcamDesconectadaError(ErroCaptura):
    """A webcam não pôde ser aberta ou caiu durante a operação."""


class QuedaDeFrameError(ErroCaptura):
    """Muitos frames vazios seguidos — provável travamento do dispositivo."""


class CapturaWebcam:
    """Encapsula a `cv2.VideoCapture` com reconexão e tratamento de exceções."""

    def __init__(self, cfg: ConfigCaptura, fonte: Optional[object] = None) -> None:
        """
        Args:
            cfg: parâmetros de captura.
            fonte: índice da câmera (int) ou caminho de um vídeo (str). Se None,
                   usa `cfg.indice_camera`.
        """
        self.cfg = cfg
        self.fonte = cfg.indice_camera if fonte is None else fonte
        self._cap: Optional[cv2.VideoCapture] = None
        self._frames_vazios = 0

    # ----------------------------------------------------------------- ciclo
    def abrir(self) -> None:
        """Abre o dispositivo. Levanta WebcamDesconectadaError se falhar."""
        cap = cv2.VideoCapture(self.fonte)
        if not cap.isOpened():
            raise WebcamDesconectadaError(
                f"Não foi possível abrir a fonte de vídeo: {self.fonte!r}"
            )
        # Define resolução/fps desejados (a câmera pode ignorar — tudo bem):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cfg.largura)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cfg.altura)
        cap.set(cv2.CAP_PROP_FPS, self.cfg.fps_alvo)
        self._cap = cap
        self._frames_vazios = 0

    def fechar(self) -> None:
        """Libera o dispositivo."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def _reconectar(self) -> None:
        """Tenta reabrir a webcam após uma queda, respeitando o limite de tentativas."""
        self.fechar()
        for tentativa in range(1, self.cfg.max_tentativas_reconexao + 1):
            print(
                f"[captura] tentando reconectar a webcam "
                f"({tentativa}/{self.cfg.max_tentativas_reconexao})..."
            )
            time.sleep(self.cfg.espera_reconexao_seg)
            try:
                self.abrir()
                print("[captura] webcam reconectada.")
                return
            except WebcamDesconectadaError:
                continue
        raise WebcamDesconectadaError(
            "Falha ao reconectar a webcam após várias tentativas."
        )

    # --------------------------------------------------------------- leitura
    def ler(self) -> np.ndarray:
        """Lê um frame. Trata queda de frame e tenta reconexão automática.

        Returns:
            frame BGR (np.ndarray).

        Raises:
            WebcamDesconectadaError, QuedaDeFrameError.
        """
        if self._cap is None:
            raise WebcamDesconectadaError("Captura não inicializada (chame abrir()).")

        ok, frame = self._cap.read()

        if not ok or frame is None:
            # Frame vazio: pode ser oscilação momentânea ou desconexão real.
            self._frames_vazios += 1
            if self._frames_vazios >= self.cfg.max_frames_vazios:
                # Tratamos como dispositivo travado/desconectado e reconectamos.
                try:
                    self._reconectar()
                    self._frames_vazios = 0
                    return self.ler()
                except WebcamDesconectadaError as exc:
                    raise QuedaDeFrameError(
                        f"Queda de frame persistente ({self._frames_vazios} frames "
                        f"vazios) e reconexão falhou."
                    ) from exc
            # Ainda dentro da tolerância — sinaliza queda pontual.
            raise QuedaDeFrameError("Frame vazio recebido da webcam.")

        # Frame válido — zera o contador.
        self._frames_vazios = 0
        return frame

    def frames(self) -> Iterator[np.ndarray]:
        """Gera frames continuamente, absorvendo quedas pontuais de frame.

        Loop eficiente: não há `sleep` ocupado; o ritmo é ditado pelo `read()`
        bloqueante da própria câmera. Quedas pontuais (QuedaDeFrameError dentro
        da tolerância) são puladas; desconexão real (WebcamDesconectadaError)
        sobe para o chamador encerrar com elegância.
        """
        while True:
            try:
                yield self.ler()
            except QuedaDeFrameError:
                # Queda pontual: ignora este frame e segue.
                continue

    # --------------------------------------------------- context manager API
    def __enter__(self) -> "CapturaWebcam":
        self.abrir()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.fechar()
