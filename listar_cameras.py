"""Utilitário — descobrir o índice da webcam externa.

Abre cada câmera disponível e mostra uma janela com o índice escrito por cima.
Olhe qual janela mostra a imagem da SUA webcam externa e use aquele número em:

    python main.py --camera <N>

Uso:
    python listar_cameras.py            # testa índices 0..5
    python listar_cameras.py 8          # testa índices 0..8

Teclas: 'q' fecha tudo.
"""

from __future__ import annotations

import sys

import cv2


def main() -> None:
    max_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 5

    abertas = []
    for i in range(max_idx + 1):
        cap = cv2.VideoCapture(i)
        ok, frame = cap.read()
        if ok and frame is not None:
            print(f"[OK]  câmera {i} funciona  ({frame.shape[1]}x{frame.shape[0]})")
            abertas.append((i, cap))
        else:
            print(f"[--]  câmera {i} indisponível")
            cap.release()

    if not abertas:
        print("\nNenhuma câmera encontrada. Verifique se a webcam está conectada "
              "e se aparece em `ls /dev/video*`.")
        return

    print("\nMostrando as câmeras que abriram. Identifique a sua webcam externa,"
          "\nanote o número no título da janela e feche com 'q'.")
    print("Depois rode:  python main.py --camera <N>\n")

    while True:
        for i, cap in abertas:
            ok, frame = cap.read()
            if ok and frame is not None:
                cv2.putText(frame, f"camera {i}", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (40, 220, 40), 3)
                cv2.imshow(f"camera {i}", frame)
        if (cv2.waitKey(1) & 0xFF) == ord("q"):
            break

    for _, cap in abertas:
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
