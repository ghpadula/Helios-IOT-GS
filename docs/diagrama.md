# Diagrama da lógica — HÉLIOS / Olhos

## Pipeline de visão (fluxo principal)

```
            ┌──────────────────────────────────────────────────────────────┐
            │                      main.py (loop)                           │
            └──────────────────────────────────────────────────────────────┘
                                       │
        ┌──────────────────┐           │ frame BGR
        │  Webcam (OpenCV) │───────────┤
        │   ou  --demo     │           │   captura.py
        │ (PainelSimulado) │           │   • loop eficiente
        └──────────────────┘           │   • exceções: desconexão / queda de frame
                                       ▼
                            ┌─────────────────────┐
                            │  robustez.py        │   luz fraca (CLAHE)
                            │  PreProcessador     │   ruído (bilateral)
                            │  • realcar()        │   oclusão -> congela medição
                            │  • ocluido()        │
                            └─────────────────────┘
                                       │ frame tratado
                                       ▼
                            ┌─────────────────────┐
                            │  visao.py           │   grauSujeira ∈ [0,1]
                            │  MedidorSujeira     │   • HSV (sem calibrar)
                            │  • medir()          │   • baseline (calibrado)
                            │  • calibrar()       │   • média móvel (suaviza)
                            └─────────────────────┘
                                       │ grauSujeira
                                       ▼
                            ┌─────────────────────┐
                            │  decisao.py         │   SUJEIRA_DETECTADA?
                            │  MotorDecisao       │   • Alerta (transição limpo->sujo)
                            │  • avaliar_alerta() │   • ComandoVibracao
                            │  • avaliar_comando()│     (intensidade ∝ sujeira)
                            └─────────────────────┘
                                       │ eventos (contrato seção 6)
                          ┌────────────┴────────────┐
                          ▼                         ▼
                ┌──────────────────┐      ┌──────────────────┐
                │  saida.py        │      │  hud.py          │
                │  Publicador      │      │  overlay no vídeo│
                │  • console       │      │  • barra/status  │
                │  • eventos.jsonl │      │  • FPS / alerta  │
                └──────────────────┘      └──────────────────┘
                          │
                          ▼
                  Serviços Java (SOA) ──► Domínio C# ──► App Mobile
                  (consomem o mesmo JSON do contrato — "integração da GS")
```

## Malha fechada (enxergar → decidir → agir → verificar)

```
   enxergar            decidir                 agir                 verificar
 ┌──────────┐      ┌────────────┐        ┌───────────────┐      ┌──────────────┐
 │  medir   │ ───► │ grau ≥ 0.4 │ ─sim─► │ VIBRAR         │ ───► │ grau caiu?   │
 │ grauSuj. │      │   ?        │        │ intensidade ∝  │      │ se não:      │
 └──────────┘      └────────────┘        │ grau, dur=i*12 │      │ repete/ajusta│
       ▲                 │ não            └───────────────┘      └──────┬───────┘
       │                 ▼                                              │
       └─────────────────┴──────────────────────────────────────◄──────┘
                         (continua monitorando)
```

## Estados do sistema (HUD)

```
   LIMPO  ──(grau ≥ 0.40)──►  SUJO  ──(vibração solta a poeira / grau < 0.40)──►  LIMPO
     ▲                                                                              │
     └──────────────────────── OCLUÍDO (objeto na frente) ◄─────────────────────────┘
                               • medição congelada, sem alerta falso
```
