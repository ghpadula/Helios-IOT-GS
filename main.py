"""HÉLIOS — Olhos · Ponto de entrada (Sprint 5).

Amarra o pipeline inteiro da matéria Physical Computing:

    webcam/demo  ->  robustez (luz/ruído/oclusão)  ->  medição (grauSujeira)
                 ->  decisão (alerta + comando de vibração)  ->  saída (contrato JSON)
                 ->  HUD no vídeo

Uso:
    python main.py --camera 0        # webcam real (índice 0)
    python main.py --demo            # painel simulado (sem hardware)
    python main.py --video arq.mp4   # a partir de um arquivo de vídeo
    python main.py --headless        # sem janela (servidor/CI)

Teclas (com janela): 'c' calibra o painel limpo · 'q' sai.
"""

from __future__ import annotations

import argparse
import sys
import time

import cv2

from src.config import Config
from src.captura import CapturaWebcam, WebcamDesconectadaError, QuedaDeFrameError
from src.visao import MedidorSujeira
from src.robustez import PreProcessador
from src.decisao import MotorDecisao
from src.saida import Publicador
from src.contrato import GrauSujeiraEvento, LeituraSensor
from src import hud
from src.simulador import PainelSimulado


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="HÉLIOS — Olhos (visão computacional).")
    fonte = p.add_mutually_exclusive_group()
    fonte.add_argument("--camera", type=int, metavar="N",
                       help="índice da webcam (ex.: 0).")
    fonte.add_argument("--video", type=str, metavar="ARQ",
                       help="caminho de um arquivo de vídeo.")
    fonte.add_argument("--demo", action="store_true",
                       help="usa painel simulado (sem hardware).")
    p.add_argument("--headless", action="store_true",
                   help="não abre janela (útil em servidor/gravação por OBS).")
    p.add_argument("--calibrar-inicio", action="store_true",
                   help="calibra o painel limpo no primeiro frame.")
    p.add_argument("--mostrar-mascara", action="store_true",
                   help="pinta de âmbar as regiões detectadas como poeira.")
    return p.parse_args()


class FPSMetro:
    """Mede FPS com média móvel exponencial (leve)."""

    def __init__(self) -> None:
        self._t = time.monotonic()
        self.fps = 0.0

    def tick(self) -> float:
        agora = time.monotonic()
        dt = agora - self._t
        self._t = agora
        if dt > 0:
            inst = 1.0 / dt
            self.fps = inst if self.fps == 0 else 0.9 * self.fps + 0.1 * inst
        return self.fps


def processar_frame(frame, ctx) -> None:
    """Aplica o pipeline a um único frame e emite os eventos do contrato."""
    cfg: Config = ctx["cfg"]
    pre: PreProcessador = ctx["pre"]
    medidor: MedidorSujeira = ctx["medidor"]
    motor: MotorDecisao = ctx["motor"]
    pub: Publicador = ctx["pub"]

    ocluido = pre.ocluido(frame)
    tratado = pre.realcar(frame)

    if ocluido:
        # Sob oclusão não medimos: mantemos o último grau e não geramos alerta.
        grau = ctx["ultimo_grau"]
    else:
        grau = medidor.medir(tratado)
        ctx["ultimo_grau"] = grau

        # --- decisão (malha fechada) ---
        alerta = motor.avaliar_alerta(grau)
        if alerta is not None:
            pub.publicar(alerta, "ALERTA")
        comando = motor.avaliar_comando(grau)
        if comando is not None:
            pub.publicar(comando, "COMANDO")
            # No modo demo, realimenta o painel: a vibração solta a poeira.
            painel = ctx.get("painel_sim")
            if painel is not None:
                painel.acionar_vibracao(comando.intensidade)

        # --- publicação periódica do grauSujeira (não a cada frame) ---
        ctx["frame_idx"] += 1
        if ctx["frame_idx"] % cfg.saida.publicar_a_cada_n_frames == 0:
            pub.publicar(
                GrauSujeiraEvento(ativoId=cfg.ativo_id, grauSujeira=grau), "VISAO"
            )
            pub.publicar(
                LeituraSensor(
                    sensorId=cfg.sensor_visao_id, tipo="sujeira",
                    valor=grau, unidade="frac", ativoId=cfg.ativo_id,
                ), "LEITURA"
            )

    # --- HUD / janela ---
    if not ctx["headless"]:
        vista = hud.aplicar_mascara(frame, medidor.ultima_mascara) \
            if ctx["mostrar_mascara"] else frame
        vista = hud.desenhar(
            vista, grau, medidor.metodo, ctx["fps"].fps,
            sujo=motor.sujo, ocluido=ocluido, calibrado=medidor.calibrado,
            limiar=cfg.decisao.limiar_sujeira_detectada,
        )
        cv2.imshow("HELIOS - Olhos", vista)


def loop_demo(ctx) -> None:
    """Loop para o painel simulado (sem exceções de hardware)."""
    painel: PainelSimulado = ctx["painel_sim"]
    medidor: MedidorSujeira = ctx["medidor"]
    while True:
        frame = painel.ler()
        ctx["fps"].tick()
        if ctx.get("calibrar_pendente"):
            medidor.calibrar(frame)
            ctx["calibrar_pendente"] = False
            print("[main] painel limpo calibrado.")
        processar_frame(frame, ctx)
        if not _tratar_teclado(ctx, medidor):
            break


def loop_webcam(ctx) -> None:
    """Loop para webcam/vídeo, com tratamento das exceções obrigatórias."""
    cfg: Config = ctx["cfg"]
    medidor: MedidorSujeira = ctx["medidor"]
    try:
        with CapturaWebcam(cfg.captura, fonte=ctx["fonte"]) as cam:
            primeiro = True
            for frame in cam.frames():
                ctx["fps"].tick()
                if primeiro and ctx["calibrar_inicio"]:
                    medidor.calibrar(frame)
                    print("[main] painel limpo calibrado (primeiro frame).")
                primeiro = False
                if ctx.get("calibrar_pendente"):
                    medidor.calibrar(frame)
                    ctx["calibrar_pendente"] = False
                    print("[main] painel limpo calibrado.")
                processar_frame(frame, ctx)
                if not _tratar_teclado(ctx, medidor):
                    break
    except WebcamDesconectadaError as exc:
        print(f"[ERRO] Webcam desconectada e sem reconexão: {exc}", file=sys.stderr)
        sys.exit(2)
    except QuedaDeFrameError as exc:
        print(f"[ERRO] Falha persistente de leitura de frames: {exc}", file=sys.stderr)
        sys.exit(3)


def _tratar_teclado(ctx, medidor) -> bool:
    """Lê teclado quando há janela. Retorna False para encerrar o loop."""
    if ctx["headless"]:
        return True
    tecla = cv2.waitKey(1) & 0xFF
    if tecla == ord("q"):
        return False
    if tecla == ord("c"):
        ctx["calibrar_pendente"] = True
    if tecla == ord("r"):
        medidor.resetar()
        print("[main] calibração descartada (volta para heurística HSV).")
    return True


def main() -> None:
    args = parse_args()
    cfg = Config()

    # Resolve a fonte de vídeo.
    usar_demo = args.demo or (args.camera is None and args.video is None)
    if args.camera is not None:
        fonte = args.camera
    elif args.video is not None:
        fonte = args.video
    else:
        fonte = None  # demo

    pre = PreProcessador(cfg.robustez)
    medidor = MedidorSujeira(cfg.visao)
    motor = MotorDecisao(cfg.decisao, cfg.ativo_id, cfg.atuador_id)

    with Publicador(cfg.saida) as pub:
        ctx = {
            "cfg": cfg, "pre": pre, "medidor": medidor, "motor": motor, "pub": pub,
            "fps": FPSMetro(), "frame_idx": 0, "ultimo_grau": 0.0,
            "headless": args.headless, "mostrar_mascara": args.mostrar_mascara,
            "calibrar_inicio": args.calibrar_inicio, "calibrar_pendente": False,
            "fonte": fonte,
        }

        print("=" * 60)
        print(" HÉLIOS — Olhos | Physical Computing")
        print(f" Fonte: {'DEMO (painel simulado)' if usar_demo else fonte}")
        print(f" Saída: {pub.caminho}")
        print(" Teclas: c=calibrar  r=reset  q=sair")
        print("=" * 60)

        try:
            if usar_demo:
                ctx["painel_sim"] = PainelSimulado(cfg.captura.largura, cfg.captura.altura)
                loop_demo(ctx)
            else:
                loop_webcam(ctx)
        except KeyboardInterrupt:
            print("\n[main] interrompido pelo usuário.")
        finally:
            cv2.destroyAllWindows()
            print("[main] encerrado. Eventos salvos em:", pub.caminho)


if __name__ == "__main__":
    main()
