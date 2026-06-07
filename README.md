# HÉLIOS — Olhos · Physical Computing (IoT & IoB)

> **Os "olhos" do HÉLIOS.** Uma webcam aponta para um painel solar, a IA **mede o
> grau de sujeira** (% de cobertura de poeira) e dispara o evento que aciona a
> **limpeza por vibração** — fechando a malha `enxergar → decidir → agir → verificar`.

Entrega da matéria **Physical Computing** da Global Solution 2026.1 (FIAP) — tema
**Indústria Espacial**, projeto **HÉLIOS** (limpeza autônoma de painéis solares na
Lua por vibração piezoelétrica, sem água e sem contato).

---

## Objetivo

**Negócio:** na Lua, a poeira eletrostática cobre os painéis e derruba a geração de
energia. Não há gente para limpar e a distância Terra–Lua inviabiliza controle
remoto — a decisão precisa acontecer **no local, sozinha** (edge AI). Este módulo é
o sensor inteligente que enxerga a sujeira e decide a hora de limpar. **Uso dual na
Terra:** limpeza sem água de fazendas solares em regiões áridas. (ODS 6, 7, 9, 11, 13.)

**Técnico:** entregar, em Python, a etapa de **visão** do pipeline da GS:
medir o `grauSujeira` ∈ [0, 1], gerar `SUJEIRA_DETECTADA` acima do limiar e emitir
tudo no **contrato de dados JSON** compartilhado (seção 6 do briefing), pronto para
o SOA (Java), o domínio (C#) e o app (React Native) consumirem.

---

## O que o módulo faz

1. **Captura** a webcam em loop eficiente (OpenCV).
2. **Robustez:** corrige luz fraca (CLAHE), reduz ruído (filtro bilateral) e
   detecta **oclusão** (objeto na frente → congela a medição, sem alerta falso).
3. **Mede** o `grauSujeira` (0–1) por visão, com **suavização temporal**.
4. **Decide:** acima do limiar gera **Alerta** e **Comando de vibração** com
   intensidade/duração **proporcionais** à sujeira (mesma lógica do C#).
5. **Publica** os eventos no formato do contrato (console + `eventos.jsonl`).
6. **Mostra** tudo num **HUD** sobre o vídeo (barra de sujeira, status, FPS, alerta).

---

## Arquitetura / Pipeline

```
webcam/--demo → robustez (luz/ruído/oclusão) → medição (grauSujeira)
              → decisão (alerta + comando de vibração) → saída (contrato JSON) + HUD
```

Diagrama completo da lógica e da malha fechada em **[docs/diagrama.md](docs/diagrama.md)**.

### Estrutura de pastas

```
IOT/
├── main.py                 # ponto de entrada (amarra o pipeline)
├── requirements.txt        # opencv-python, numpy
├── README.md
├── docs/
│   ├── SPRINTS.md          # plano e divisão do trabalho em sprints
│   └── diagrama.md         # diagramas da lógica
└── src/
    ├── config.py           # todos os parâmetros num só lugar
    ├── captura.py          # Sprint 1 — webcam + exceções/reconexão
    ├── visao.py            # Sprint 2 — medição do grauSujeira
    ├── contrato.py         # Sprint 3 — modelos JSON da seção 6
    ├── decisao.py          # Sprint 3 — alertas + vibração modulada
    ├── saida.py            # Sprint 3 — publicação (console + JSONL)
    ├── robustez.py         # Sprint 4 — CLAHE/bilateral/oclusão
    ├── hud.py              # Sprint 4 — overlay no vídeo
    └── simulador.py        # Sprint 5 — painel sintético (modo demo)
```

---

## Bibliotecas

| Biblioteca | Para quê |
|------------|----------|
| **opencv-python** | captura da webcam, conversões de cor, CLAHE, filtro bilateral, HUD |
| **numpy** | operações vetorizadas (medição do grau de sujeira de forma eficiente) |

Apenas a biblioteca-padrão do Python além dessas duas — sem dependências pesadas.

---

## Como executar

> **Reprodutibilidade exata:** testado em **Python 3.14.5** (ver `.python-version`)
> com as versões **pinadas** em `requirements.txt` (`opencv-python==4.13.0.92`,
> `numpy==2.4.6`). Use um ambiente virtual para reproduzir 1:1.

```bash
# 1) ambiente
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2) rodar
python main.py --camera 0        # webcam real (índice 0)
python main.py --demo            # painel SIMULADO (sem hardware) — ótimo p/ o vídeo
python main.py --video arq.mp4   # a partir de um vídeo gravado
```

**Teclas (com janela):** `c` calibra o painel limpo · `r` descarta a calibração ·
`q` sai.

**Flags úteis:**

| Flag | Efeito |
|------|--------|
| `--demo` | painel sintético que suja com o tempo e limpa ao vibrar |
| `--headless` | roda sem janela (servidor/CI, ou gravando a tela por fora) |
| `--calibrar-inicio` | calibra o painel limpo já no primeiro frame |
| `--mostrar-mascara` | pinta de âmbar as regiões detectadas como poeira |

> **Para gravar o vídeo da entrega sem painel físico:** `python main.py --demo`.
> O painel acumula poeira → dispara o alerta → o HÉLIOS vibra → a poeira se solta →
> a energia "recupera". O loop fechado inteiro aparece na tela em ~15 s.

---

## Contrato de dados (seção 6 do briefing)

A visão **produz** o grau de sujeira (e leituras) e **dispara** alertas e comandos,
todos no JSON compartilhado pela GS:

```json
// Saída da visão
{ "ativoId": "PAINEL-A", "grauSujeira": 0.47, "fonte": "visao", "timestamp": "2026-06-01T14:03:00Z" }

// Alerta (na transição limpo -> sujo)
{ "alertaId": "ALT-001", "ativoId": "PAINEL-A", "severidade": "ALTA",
  "tipo": "SUJEIRA_DETECTADA", "mensagem": "Cobertura de poeira ~47%",
  "timestamp": "2026-06-01T14:03:01Z", "resolvido": false }

// Comando de limpeza (vibração modulada)
{ "comandoId": "CMD-77", "atuadorId": "VIB-PAINEL-A", "acao": "VIBRAR",
  "intensidade": 0.7, "duracaoSeg": 8, "alvoAtivoId": "PAINEL-A",
  "timestamp": "2026-06-01T14:03:02Z" }
```

Os eventos são impressos no console e salvos em `saidas/eventos.jsonl`.
A **lógica da vibração** (`intensidade = clamp(grau, 0.3, 1.0)`, `duração = int(i*12)`)
espelha de propósito o `TarefaLimpeza.CalcularIntensidade` do projeto C#, para manter
a integração coerente entre as matérias.

---

## Robustez e tratamento de exceções

- **Luz fraca:** equalização adaptativa de contraste (CLAHE) no canal de luminância.
- **Ruído:** filtro bilateral (suaviza preservando bordas das células).
- **Oclusão parcial:** se boa parte do quadro escurece de repente, a medição é
  **congelada** (não gera leitura nem alerta falso) e o HUD mostra `OCLUÍDO`.
- **Webcam desconectada** → `WebcamDesconectadaError` com **reconexão automática**
  (até N tentativas); se falhar, encerra com código de saída específico.
- **Queda de frame** → `QuedaDeFrameError`; quedas pontuais são puladas, quedas
  persistentes disparam reconexão.

---

## Sprints

O desenvolvimento foi organizado em 7 sprints — ver **[docs/SPRINTS.md](docs/SPRINTS.md)**.

---

## Integrantes

> Preencher antes da entrega (exigência do repositório — nomes completos + RM):

- Nome Completo — RMxxxxx
- Nome Completo — RMxxxxx
- Nome Completo — RMxxxxx
- Nome Completo — RMxxxxx
- Nome Completo — RMxxxxx

---

*HÉLIOS — da poeira lunar à energia limpa na Terra.*
