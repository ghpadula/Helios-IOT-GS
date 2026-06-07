"""Configuração central do HÉLIOS — Olhos.

Todos os parâmetros ajustáveis ficam aqui para manter os demais módulos limpos
e facilitar a calibração em campo (mudar limiar, câmera, resolução, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field


# --------------------------------------------------------------------------- #
# Identidade do ativo monitorado (coerente com o contrato de dados, seção 6)
# --------------------------------------------------------------------------- #
ATIVO_ID = "PAINEL-A"
ATUADOR_ID = "VIB-PAINEL-A"
SENSOR_VISAO_ID = "PANEL-A-VISION"


@dataclass
class ConfigCaptura:
    """Parâmetros da captura de vídeo (Sprint 1)."""

    indice_camera: int = 0          # 0 = webcam padrão
    largura: int = 640
    altura: int = 480
    fps_alvo: int = 30
    # Reconexão quando a webcam cai (exceção obrigatória do briefing):
    max_tentativas_reconexao: int = 5
    espera_reconexao_seg: float = 1.0
    # Quantos frames vazios seguidos toleramos antes de declarar "queda de frame":
    max_frames_vazios: int = 30


@dataclass
class ConfigVisao:
    """Parâmetros da medição de sujeira (Sprint 2)."""

    # Janela da média móvel que suaviza o grauSujeira (estabilidade temporal):
    janela_suavizacao: int = 8
    # Heurística HSV: poeira é clara (valor alto) e dessaturada (saturação baixa).
    saturacao_max_poeira: int = 90      # 0-255 — abaixo disso é "sem cor" (poeira)
    valor_min_poeira: int = 90          # 0-255 — acima disso é "claro" (poeira)
    # Método por baseline: diferença de brilho que conta como poeira (0-255):
    limiar_diff_baseline: int = 25
    # Suavização espacial antes de medir (reduz ruído de pixel):
    blur_kernel: int = 5


@dataclass
class ConfigDecisao:
    """Parâmetros do motor de decisão (Sprint 3)."""

    # Acima deste grauSujeira disparamos SUJEIRA_DETECTADA:
    limiar_sujeira_detectada: float = 0.40
    # Faixas de severidade do alerta:
    limiar_severidade_alta: float = 0.40
    limiar_severidade_media: float = 0.25
    # Lógica da vibração modulada (espelha o CalcularIntensidade do C#):
    grau_minimo_para_vibrar: float = 0.15
    intensidade_min: float = 0.30
    intensidade_max: float = 1.00
    fator_duracao_seg: int = 12         # duracao = int(intensidade * fator)
    # Evita reemitir comando a cada frame: intervalo mínimo entre comandos (seg):
    intervalo_min_comando_seg: float = 5.0


@dataclass
class ConfigRobustez:
    """Parâmetros de robustez a luz fraca / ruído / oclusão (Sprint 4)."""

    usar_clahe: bool = True             # equaliza contraste em luz fraca
    clahe_clip: float = 2.0
    clahe_grid: int = 8
    usar_bilateral: bool = True         # reduz ruído preservando bordas
    bilateral_d: int = 5
    bilateral_sigma: int = 50
    # Oclusão: se uma fração grande do frame ficar muito escura de repente,
    # tratamos como oclusão (mão/objeto na frente) e congelamos a medição.
    limiar_oclusao_escuro: int = 35     # brilho médio considerado "tampado"
    fracao_oclusao: float = 0.55        # fração do frame escura p/ acusar oclusão


@dataclass
class ConfigSaida:
    """Parâmetros de saída / persistência (Sprint 3/5)."""

    pasta_saida: str = "saidas"
    arquivo_eventos: str = "eventos.jsonl"   # linha a linha (JSON Lines)
    imprimir_console: bool = True
    # A cada quantos frames publicamos a leitura de grauSujeira (evita spam):
    publicar_a_cada_n_frames: int = 15


@dataclass
class Config:
    """Configuração agregada do sistema."""

    captura: ConfigCaptura = field(default_factory=ConfigCaptura)
    visao: ConfigVisao = field(default_factory=ConfigVisao)
    decisao: ConfigDecisao = field(default_factory=ConfigDecisao)
    robustez: ConfigRobustez = field(default_factory=ConfigRobustez)
    saida: ConfigSaida = field(default_factory=ConfigSaida)

    ativo_id: str = ATIVO_ID
    atuador_id: str = ATUADOR_ID
    sensor_visao_id: str = SENSOR_VISAO_ID
