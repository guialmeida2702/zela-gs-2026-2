"""Zela · Visão Computacional — pipeline completo de identificação de fissuras em concreto.

Executa, do início ao fim:
  1. preparação dos dados (amostragem e divisão treino/validação/teste por BLOCOS de recortes vizinhos);
  2. transferência de aprendizado com MobileNetV3-Small pré-treinada no ImageNet;
  3. escolha do limiar de confiança na validação (prioriza recall: na triagem, perder uma fissura custa mais);
  4. avaliação no teste (precisão, recall, F1, matriz de confusão) e análise de erros;
  5. teste de robustez (sombra, pouca luz, superexposição, desfoque, ruído, compressão);
  6. exportação para ONNX e medição de latência/FPS;
  7. simulação de monitoramento urbano (sequência de quadros) com vídeo anotado.

Uso:
    python pipeline.py --dados /caminho/para/ConcreteCrack   # pastas Positive/ e Negative/
Base: Özgenel, Ç. F. (2019). Concrete Crack Images for Classification. Mendeley Data, V2.
      https://data.mendeley.com/datasets/5y9wdsg2zt/2  (CC BY 4.0)
"""

from __future__ import annotations

import argparse
import json
import platform
import random
import time
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import onnxruntime as ort
import torch
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

AQUI = Path(__file__).parent
RESULTADOS = AQUI / "resultados"
MODELOS = AQUI / "modelos"
SEMENTE = 42
TAM = 160  # resolução de entrada (equilíbrio entre detalhe da fissura e velocidade)
MEDIA, DESVIO = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
BLOCO = 50  # recortes consecutivos tendem a vir da mesma foto original: dividimos por blocos
AMOSTRA = {"treino": 1500, "validacao": 400, "teste": 1000}  # por classe
CLASSES = ["sem_fissura", "com_fissura"]


def fixar_sementes() -> None:
    random.seed(SEMENTE)
    np.random.seed(SEMENTE)
    torch.manual_seed(SEMENTE)


# ---------------------------------------------------------------- 1. dados
def dividir_por_blocos(pasta: Path) -> dict[str, list[Path]]:
    arquivos = sorted(pasta.glob("*.jpg"))
    blocos: dict[int, list[Path]] = {}
    for arq in arquivos:
        indice = int(arq.stem.split("_")[0]) - 1
        blocos.setdefault(indice // BLOCO, []).append(arq)
    ids = sorted(blocos)
    random.Random(SEMENTE).shuffle(ids)
    n = len(ids)
    cortes = {"treino": ids[: int(0.7 * n)], "validacao": ids[int(0.7 * n): int(0.85 * n)], "teste": ids[int(0.85 * n):]}
    saida = {}
    for conjunto, bl in cortes.items():
        todos = [a for b in bl for a in blocos[b]]
        random.Random(SEMENTE).shuffle(todos)
        saida[conjunto] = todos[: AMOSTRA[conjunto]]
    return saida


class ConjuntoFissuras(Dataset):
    def __init__(self, itens: list[tuple[Path, int]], transformacao):
        self.itens = itens
        self.transformacao = transformacao

    def __len__(self) -> int:
        return len(self.itens)

    def __getitem__(self, i):
        caminho, rotulo = self.itens[i]
        return self.transformacao(Image.open(caminho).convert("RGB")), rotulo


T_TREINO = transforms.Compose([
    transforms.RandomResizedCrop(TAM, scale=(0.7, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.ColorJitter(brightness=0.3, contrast=0.3),
    transforms.ToTensor(),
    transforms.Normalize(MEDIA, DESVIO),
])
T_AVAL = transforms.Compose([transforms.Resize((TAM, TAM)), transforms.ToTensor(), transforms.Normalize(MEDIA, DESVIO)])


# ---------------------------------------------------------------- 2. modelo e treino
def criar_modelo() -> nn.Module:
    modelo = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
    modelo.classifier[3] = nn.Linear(modelo.classifier[3].in_features, 2)
    return modelo


@torch.no_grad()
def prever(modelo: nn.Module, carregador: DataLoader) -> tuple[np.ndarray, np.ndarray]:
    modelo.eval()
    probs, rotulos = [], []
    for x, y in carregador:
        probs.append(torch.softmax(modelo(x), dim=1)[:, 1].numpy())
        rotulos.append(y.numpy())
    return np.concatenate(probs), np.concatenate(rotulos)


def treinar(modelo: nn.Module, treino: DataLoader, validacao: DataLoader, historico: list) -> nn.Module:
    perda_fn = nn.CrossEntropyLoss()
    fases = [("cabeça (backbone congelado)", 1, 1e-3, True), ("ajuste fino completo", 2, 3e-4, False)]
    melhor_f1, melhor_estado = -1.0, None
    for nome, epocas, lr, congelar in fases:
        for p in modelo.features.parameters():
            p.requires_grad = not congelar
        otimizador = torch.optim.AdamW([p for p in modelo.parameters() if p.requires_grad], lr=lr, weight_decay=1e-4)
        for ep in range(epocas):
            modelo.train()
            inicio, soma, n = time.time(), 0.0, 0
            for x, y in treino:
                otimizador.zero_grad()
                perda = perda_fn(modelo(x), y)
                perda.backward()
                otimizador.step()
                soma += perda.item() * len(y)
                n += len(y)
            p_val, y_val = prever(modelo, validacao)
            f1 = f1_score(y_val, p_val >= 0.5)
            registro = {"fase": nome, "epoca": ep + 1, "perda_treino": round(soma / n, 4),
                        "f1_validacao": round(float(f1), 4), "acuracia_validacao": round(float(accuracy_score(y_val, p_val >= 0.5)), 4),
                        "segundos": round(time.time() - inicio, 1)}
            historico.append(registro)
            print("  ", registro, flush=True)
            if f1 > melhor_f1:
                melhor_f1, melhor_estado = f1, {k: v.clone() for k, v in modelo.state_dict().items()}
    modelo.load_state_dict(melhor_estado)
    return modelo


def escolher_limiar(probs: np.ndarray, rotulos: np.ndarray) -> float:
    """Limiar que maximiza F2 (recall pesa o dobro): na triagem, deixar de sinalizar uma fissura é o erro mais caro."""
    melhor, melhor_t = -1.0, 0.5
    for t in np.arange(0.10, 0.91, 0.05):
        pred = probs >= t
        p, r = precision_score(rotulos, pred, zero_division=0), recall_score(rotulos, pred, zero_division=0)
        f2 = 5 * p * r / (4 * p + r) if (p + r) else 0
        if f2 > melhor:
            melhor, melhor_t = f2, float(round(t, 2))
    return melhor_t


def metricas(probs: np.ndarray, rotulos: np.ndarray, limiar: float) -> dict:
    pred = (probs >= limiar).astype(int)
    return {
        "limiar": limiar,
        "acuracia": round(float(accuracy_score(rotulos, pred)), 4),
        "precisao": round(float(precision_score(rotulos, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(rotulos, pred, zero_division=0)), 4),
        "f1": round(float(f1_score(rotulos, pred, zero_division=0)), 4),
        "matriz_confusao": confusion_matrix(rotulos, pred).tolist(),
        "n": int(len(rotulos)),
    }


# ---------------------------------------------------------------- 4. análise de erros
def grade_erros(itens: list[tuple[Path, int]], probs: np.ndarray, limiar: float, destino: Path) -> dict:
    rotulos = np.array([r for _, r in itens])
    fp = [i for i in np.argsort(-probs) if rotulos[i] == 0 and probs[i] >= limiar][:8]
    fn = [i for i in np.argsort(probs) if rotulos[i] == 1 and probs[i] < limiar][:8]
    acertos = [i for i in np.argsort(-probs) if rotulos[i] == 1 and probs[i] >= limiar][:4] + \
              [i for i in np.argsort(probs) if rotulos[i] == 0 and probs[i] < limiar][:4]
    linhas = [("Falsos positivos (sinalizou sem fissura)", fp), ("Falsos negativos (fissura não sinalizada)", fn),
              ("Acertos (exemplos)", acertos)]
    fig, eixos = plt.subplots(3, 8, figsize=(16, 6.6))
    for r, (titulo, idxs) in enumerate(linhas):
        for c in range(8):
            ax = eixos[r, c]
            ax.axis("off")
            if c < len(idxs):
                i = idxs[c]
                ax.imshow(Image.open(itens[i][0]))
                ax.set_title(f"p={probs[i]:.2f} ({'fiss.' if rotulos[i] else 'sem'})", fontsize=8)
        eixos[r, 0].text(-0.15, 0.5, titulo, transform=eixos[r, 0].transAxes, rotation=90, va="center", ha="right", fontsize=8)
    fig.suptitle("Análise de erros no conjunto de teste", fontsize=12)
    fig.tight_layout()
    fig.savefig(destino, dpi=110)
    plt.close(fig)
    return {"falsos_positivos": [itens[i][0].name for i in fp], "falsos_negativos": [itens[i][0].name for i in fn]}


# ---------------------------------------------------------------- 5. robustez
def _sombra(im: Image.Image) -> Image.Image:
    arr = np.asarray(im).astype(np.float32)
    gradiente = np.linspace(0.25, 1.0, arr.shape[1])[None, :, None]
    return Image.fromarray(np.clip(arr * gradiente, 0, 255).astype(np.uint8))


def _ruido(im: Image.Image) -> Image.Image:
    arr = np.asarray(im).astype(np.float32) + np.random.default_rng(SEMENTE).normal(0, 25, np.asarray(im).shape)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _jpeg(im: Image.Image) -> Image.Image:
    import io
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=12)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


PERTURBACOES = {
    "original": lambda im: im,
    "sombra lateral": _sombra,
    "pouca luz (40%)": lambda im: ImageEnhance.Brightness(im).enhance(0.4),
    "superexposição (180%)": lambda im: ImageEnhance.Brightness(im).enhance(1.8),
    "desfoque (raio 2)": lambda im: im.filter(ImageFilter.GaussianBlur(2)),
    "ruído (σ=25)": _ruido,
    "compressão JPEG forte": _jpeg,
}


class ConjuntoPerturbado(ConjuntoFissuras):
    def __init__(self, itens, transformacao, perturbacao):
        super().__init__(itens, transformacao)
        self.perturbacao = perturbacao

    def __getitem__(self, i):
        caminho, rotulo = self.itens[i]
        return self.transformacao(self.perturbacao(Image.open(caminho).convert("RGB"))), rotulo


# ---------------------------------------------------------------- 6. ONNX e desempenho
def exportar_onnx(modelo: nn.Module, destino: Path) -> None:
    modelo.eval()

    class ComSoftmax(nn.Module):
        def __init__(self, m):
            super().__init__()
            self.m = m

        def forward(self, x):
            return torch.softmax(self.m(x), dim=1)

    exemplo = torch.randn(1, 3, TAM, TAM)
    torch.onnx.export(ComSoftmax(modelo), exemplo, destino, input_names=["imagem"], output_names=["probabilidades"],
                      dynamic_axes={"imagem": {0: "lote"}, "probabilidades": {0: "lote"}}, opset_version=17, dynamo=False)


def preprocessar_np(im: Image.Image) -> np.ndarray:
    arr = np.asarray(im.convert("RGB").resize((TAM, TAM), Image.BILINEAR), dtype=np.float32) / 255.0
    arr = (arr - np.array(MEDIA, dtype=np.float32)) / np.array(DESVIO, dtype=np.float32)
    return arr.transpose(2, 0, 1)[None]


def medir_latencia(sessao: ort.InferenceSession, caminhos: list[Path], repeticoes: int = 200) -> dict:
    entrada = sessao.get_inputs()[0].name
    x = preprocessar_np(Image.open(caminhos[0]))
    for _ in range(20):
        sessao.run(None, {entrada: x})
    tempos_modelo, tempos_total = [], []
    for i in range(repeticoes):
        caminho = caminhos[i % len(caminhos)]
        t0 = time.perf_counter()
        x = preprocessar_np(Image.open(caminho))
        t1 = time.perf_counter()
        sessao.run(None, {entrada: x})
        t2 = time.perf_counter()
        tempos_modelo.append((t2 - t1) * 1000)
        tempos_total.append((t2 - t0) * 1000)
    media_total = float(np.mean(tempos_total))
    return {
        "inferencia_media_ms": round(float(np.mean(tempos_modelo)), 2),
        "inferencia_p95_ms": round(float(np.percentile(tempos_modelo, 95)), 2),
        "fim_a_fim_media_ms": round(media_total, 2),
        "fps_fim_a_fim": round(1000 / media_total, 1),
        "repeticoes": repeticoes,
        "resolucao_entrada": f"{TAM}x{TAM}",
        "resolucao_imagem_original": "227x227",
    }


# ---------------------------------------------------------------- 7. monitoramento (sequência de quadros)
def simular_monitoramento(sessao: ort.InferenceSession, itens_teste: list[tuple[Path, int]], limiar: float) -> dict:
    """Simula uma câmera percorrendo um muro: um mosaico de recortes de teste é varrido por uma janela móvel.
    Cada quadro é dividido em blocos de 227 px; blocos acima do limiar recebem moldura e confiança."""
    rnd = random.Random(SEMENTE)
    pos = [p for p, r in itens_teste if r == 1]
    neg = [p for p, r in itens_teste if r == 0]
    linhas, colunas, lado = 2, 10, 227
    mosaico = Image.new("RGB", (colunas * lado, linhas * lado))
    verdade = np.zeros((linhas, colunas), dtype=int)
    for r in range(linhas):
        for c in range(colunas):
            com_fissura = rnd.random() < 0.35
            verdade[r, c] = int(com_fissura)
            mosaico.paste(Image.open(rnd.choice(pos if com_fissura else neg)), (c * lado, r * lado))
    largura_janela = 4 * lado
    passos = list(range(0, mosaico.width - largura_janela + 1, lado // 4))
    entrada = sessao.get_inputs()[0].name
    escritor = cv2.VideoWriter(str(RESULTADOS / "monitoramento_simulado.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 6,
                               (largura_janela, linhas * lado))
    tempos, quadros_exemplo = [], []
    for k, x0 in enumerate(passos):
        quadro = mosaico.crop((x0, 0, x0 + largura_janela, linhas * lado))
        t0 = time.perf_counter()
        blocos, posicoes = [], []
        for r in range(linhas):
            for c in range(4):
                caixa = (c * lado, r * lado, (c + 1) * lado, (r + 1) * lado)
                blocos.append(preprocessar_np(quadro.crop(caixa))[0])
                posicoes.append(caixa)
        probs = sessao.run(None, {entrada: np.stack(blocos)})[0][:, 1]
        tempos.append(time.perf_counter() - t0)
        desenho = ImageDraw.Draw(quadro)
        for caixa, p in zip(posicoes, probs, strict=True):
            if p >= limiar:
                desenho.rectangle(caixa, outline=(220, 30, 30), width=5)
                desenho.rectangle((caixa[0], caixa[1], caixa[0] + 150, caixa[1] + 24), fill=(220, 30, 30))
                desenho.text((caixa[0] + 6, caixa[1] + 5), f"FISSURA {p:.0%}", fill=(255, 255, 255))
        desenho.rectangle((0, quadro.height - 26, 330, quadro.height), fill=(0, 0, 0))
        desenho.text((8, quadro.height - 20), f"quadro {k + 1}/{len(passos)}  {1 / tempos[-1]:.1f} quadros/s", fill=(255, 255, 255))
        escritor.write(cv2.cvtColor(np.asarray(quadro), cv2.COLOR_RGB2BGR))
        if k in (0, len(passos) // 2, len(passos) - 1):
            quadros_exemplo.append(quadro)
    escritor.release()
    fig, eixos = plt.subplots(len(quadros_exemplo), 1, figsize=(10, 3.3 * len(quadros_exemplo)))
    for ax, q in zip(eixos, quadros_exemplo, strict=True):
        ax.imshow(q)
        ax.axis("off")
    fig.suptitle("Monitoramento simulado: quadros do início, meio e fim da varredura", fontsize=11)
    fig.tight_layout()
    fig.savefig(RESULTADOS / "monitoramento_quadros.png", dpi=90)
    plt.close(fig)
    return {
        "quadros": len(passos),
        "blocos_por_quadro": linhas * 4,
        "resolucao_quadro": f"{largura_janela}x{linhas * lado}",
        "tempo_medio_por_quadro_ms": round(float(np.mean(tempos)) * 1000, 1),
        "quadros_por_segundo": round(1 / float(np.mean(tempos)), 1),
        "blocos_com_fissura_no_mosaico": int(verdade.sum()),
    }


# ---------------------------------------------------------------- execução
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dados", required=True, type=Path)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    fixar_sementes()
    torch.set_num_threads(args.threads)
    RESULTADOS.mkdir(exist_ok=True)
    MODELOS.mkdir(exist_ok=True)
    relatorio: dict = {"base": "Concrete Crack Images for Classification (Özgenel, 2019)", "semente": SEMENTE}

    print("1. Preparando dados (divisão por blocos de recortes vizinhos)...", flush=True)
    conjuntos: dict[str, list[tuple[Path, int]]] = {k: [] for k in AMOSTRA}
    for rotulo, nome in ((0, "Negative"), (1, "Positive")):
        for k, arqs in dividir_por_blocos(args.dados / nome).items():
            conjuntos[k] += [(a, rotulo) for a in arqs]
    for k in conjuntos:
        random.Random(SEMENTE).shuffle(conjuntos[k])
    relatorio["divisao"] = {k: {"total": len(v), "com_fissura": sum(r for _, r in v)} for k, v in conjuntos.items()}
    relatorio["divisao_metodo"] = f"blocos de {BLOCO} arquivos consecutivos; 70/15/15% dos blocos por classe; amostra {AMOSTRA} por classe"
    print("  ", relatorio["divisao"], flush=True)

    carregar = lambda itens, t, emb=False: DataLoader(ConjuntoFissuras(itens, t), batch_size=32, shuffle=emb, num_workers=0)  # noqa: E731
    dl_treino = carregar(conjuntos["treino"], T_TREINO, True)
    dl_val = carregar(conjuntos["validacao"], T_AVAL)
    dl_teste = carregar(conjuntos["teste"], T_AVAL)

    print("2. Treinando MobileNetV3-Small (transferência de aprendizado)...", flush=True)
    historico: list = []
    inicio = time.time()
    modelo = treinar(criar_modelo(), dl_treino, dl_val, historico)
    relatorio["treino"] = {"historico": historico, "minutos": round((time.time() - inicio) / 60, 1), "resolucao": TAM}

    print("3. Escolhendo limiar na validação...", flush=True)
    p_val, y_val = prever(modelo, dl_val)
    limiar = escolher_limiar(p_val, y_val)
    relatorio["validacao"] = {"limiar_0_5": metricas(p_val, y_val, 0.5), "limiar_escolhido": metricas(p_val, y_val, limiar)}

    print("4. Avaliando no teste...", flush=True)
    p_teste, y_teste = prever(modelo, dl_teste)
    relatorio["teste"] = {"limiar_0_5": metricas(p_teste, y_teste, 0.5), "limiar_escolhido": metricas(p_teste, y_teste, limiar),
                          "roc_auc": round(float(roc_auc_score(y_teste, p_teste)), 4)}
    for nome, t in (("limiar_0_5", 0.5), ("limiar_escolhido", limiar)):
        disp = ConfusionMatrixDisplay(confusion_matrix(y_teste, p_teste >= t), display_labels=["Sem fissura", "Com fissura"])
        disp.plot(cmap="Blues", colorbar=False)
        plt.title(f"Matriz de confusão — teste (limiar {t:.2f})")
        plt.tight_layout()
        plt.savefig(RESULTADOS / f"matriz_confusao_{nome}.png", dpi=120)
        plt.close()
    relatorio["erros"] = grade_erros(conjuntos["teste"], p_teste, limiar, RESULTADOS / "analise_erros.png")

    print("5. Testando robustez a interferências visuais...", flush=True)
    sub = conjuntos["teste"][:600]
    robustez = {}
    for nome, f in PERTURBACOES.items():
        dl = DataLoader(ConjuntoPerturbado(sub, T_AVAL, f), batch_size=32)
        pr, yr = prever(modelo, dl)
        m = metricas(pr, yr, limiar)
        robustez[nome] = {k: m[k] for k in ("precisao", "recall", "f1")}
        print("  ", nome, robustez[nome], flush=True)
    relatorio["robustez"] = {"amostra": len(sub), "resultados": robustez}
    exemplo = Image.open([p for p, r in sub if r == 1][0]).convert("RGB")
    fig, eixos = plt.subplots(1, len(PERTURBACOES), figsize=(2.2 * len(PERTURBACOES), 2.6))
    for ax, (nome, f) in zip(eixos, PERTURBACOES.items(), strict=True):
        ax.imshow(f(exemplo))
        ax.set_title(nome, fontsize=8)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(RESULTADOS / "perturbacoes_exemplo.png", dpi=110)
    plt.close(fig)

    print("6. Exportando ONNX e medindo desempenho...", flush=True)
    caminho_onnx = MODELOS / "fissura_mobilenetv3s.onnx"
    exportar_onnx(modelo, caminho_onnx)
    opcoes = ort.SessionOptions()
    opcoes.intra_op_num_threads = args.threads
    sessao = ort.InferenceSession(str(caminho_onnx), opcoes, providers=["CPUExecutionProvider"])
    diff = abs(sessao.run(None, {"imagem": preprocessar_np(exemplo)})[0][0, 1] -
               float(torch.softmax(modelo(T_AVAL(exemplo)[None]), 1)[0, 1]))
    relatorio["onnx"] = {"arquivo": caminho_onnx.name, "tamanho_mb": round(caminho_onnx.stat().st_size / 1e6, 2),
                         "diferenca_maxima_vs_pytorch": round(float(diff), 5)}
    relatorio["desempenho"] = medir_latencia(sessao, [p for p, _ in conjuntos["teste"][:200]])
    relatorio["desempenho"]["equipamento"] = _equipamento(args.threads)
    (MODELOS / "preprocessamento.json").write_text(json.dumps({
        "tamanho": TAM, "media": MEDIA, "desvio": DESVIO, "limiar": limiar, "classes": CLASSES,
        "bloco_px": 227, "modelo": caminho_onnx.name}, indent=2), encoding="utf-8")

    print("7. Simulando monitoramento por sequência de quadros...", flush=True)
    relatorio["monitoramento"] = simular_monitoramento(sessao, conjuntos["teste"], limiar)

    (RESULTADOS / "metricas.json").write_text(json.dumps(relatorio, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({k: relatorio[k] for k in ("teste", "desempenho", "monitoramento")}, indent=2, ensure_ascii=False))


def _equipamento(threads: int) -> str:
    cpu = "CPU desconhecida"
    try:
        for linha in Path("/proc/cpuinfo").read_text().splitlines():
            if linha.startswith("model name"):
                cpu = linha.split(":", 1)[1].strip()
                break
    except OSError:
        cpu = platform.processor() or cpu
    return f"{cpu}, {threads} threads, sem GPU, ONNX Runtime {ort.__version__}"


if __name__ == "__main__":
    main()
