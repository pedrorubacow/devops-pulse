"""
Projeto: DevOps Pulse - Monitoramento de Pipelines CI/CD
Dashboard em Python (matplotlib) construído a partir das tabelas do banco
PostgreSQL criado na máquina virtual em nuvem.

Instalação:
    pip install psycopg2-binary pandas matplotlib

Execução (ajuste as variáveis de ambiente para o seu servidor):
    # 1) abra um túnel SSH até a VM (deixe esse terminal aberto):
    #    ssh -i chave.pem -L 5432:localhost:5432 ubuntu@<ip-publico-da-vm>
    # 2) em outro terminal:
    export DB_HOST=localhost
    export DB_USER=postgres
    export DB_PASSWORD=<sua-senha>
    python 03_dashboard.py

Saída: abre a janela do dashboard e salva o arquivo dashboard_devops_pulse.png
"""
import os

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2

if not os.environ.get("DISPLAY") and os.name != "nt":
    matplotlib.use("Agg")  # servidor sem interface gráfica: só salva o PNG

# ---------------------------------------------------------------------------
# Conexão com o banco
# ---------------------------------------------------------------------------
CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "devops_pulse"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}


def consulta(sql: str) -> pd.DataFrame:
    """Executa um SELECT e devolve o resultado como DataFrame."""
    with psycopg2.connect(**CONFIG) as conn, conn.cursor() as cur:
        cur.execute(sql)
        colunas = [c[0] for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=colunas)


# ---------------------------------------------------------------------------
# Consultas que alimentam o dashboard (todas sobre as tabelas do projeto)
# ---------------------------------------------------------------------------
SQL_KPIS = """
SELECT (SELECT COUNT(*) FROM execucao_pipeline)                         AS execucoes,
       (SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'SUCESSO')
               / COUNT(*), 1) FROM execucao_pipeline)                    AS taxa_sucesso,
       (SELECT COUNT(*) FROM deploy WHERE ambiente = 'producao')         AS deploys_prod,
       (SELECT ROUND(AVG(EXTRACT(EPOCH FROM (resolvido_em - aberto_em)) / 3600)::numeric, 1)
          FROM incidente)                                                AS mttr_horas;
"""

SQL_DEPLOYS_MES = """
SELECT TO_CHAR(DATE_TRUNC('month', data_deploy), 'MM/YYYY') AS mes,
       COUNT(*)                                             AS deploys,
       COUNT(*) FILTER (WHERE rollback)                     AS rollbacks
FROM deploy
WHERE ambiente = 'producao'
GROUP BY DATE_TRUNC('month', data_deploy)
ORDER BY DATE_TRUNC('month', data_deploy);
"""

SQL_SUCESSO_EQUIPE = """
SELECT eq.nome AS equipe,
       ROUND(100.0 * COUNT(*) FILTER (WHERE e.status = 'SUCESSO') / COUNT(*), 1) AS taxa
FROM equipe eq
JOIN projeto p           ON p.id_equipe  = eq.id_equipe
JOIN execucao_pipeline e ON e.id_projeto = p.id_projeto
GROUP BY eq.nome
ORDER BY taxa;
"""

SQL_FALHAS_ETAPA = """
SELECT etapa_falha AS etapa, COUNT(*) AS falhas
FROM execucao_pipeline
WHERE status = 'FALHA'
GROUP BY etapa_falha
ORDER BY falhas DESC;
"""

SQL_DURACAO_FALHA = """
SELECT p.nome AS projeto,
       ROUND(AVG(e.duracao_seg) FILTER (WHERE e.status = 'SUCESSO') / 60.0, 1) AS duracao_min,
       ROUND(100.0 * COUNT(*) FILTER (WHERE e.status = 'FALHA') / COUNT(*), 1) AS taxa_falha
FROM projeto p
JOIN execucao_pipeline e ON e.id_projeto = p.id_projeto
GROUP BY p.nome;
"""

# ---------------------------------------------------------------------------
# Estilo
# ---------------------------------------------------------------------------
SUPERFICIE = "#fcfcfb"
TEXTO = "#0b0b0b"
TEXTO_2 = "#52514e"
GRADE = "#e6e5e1"
COR_1 = "#2a78d6"   # série principal
COR_2 = "#eb6834"   # série secundária

plt.rcParams.update({
    "font.family": ["Inter", "DejaVu Sans"],
    "font.size": 10,
    "axes.edgecolor": GRADE,
    "axes.labelcolor": TEXTO_2,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.titlecolor": TEXTO,
    "axes.titlelocation": "left",
    "axes.titlepad": 12,
    "xtick.color": TEXTO_2,
    "ytick.color": TEXTO_2,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": SUPERFICIE,
    "axes.facecolor": SUPERFICIE,
})


def grade_y(ax):
    ax.grid(axis="y", color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)


def kpi(fig, x, titulo, valor):
    fig.text(x, 0.885, valor, fontsize=24, fontweight="bold", color=TEXTO)
    fig.text(x, 0.865, titulo, fontsize=10, color=TEXTO_2)


def main():
    kpis = consulta(SQL_KPIS).iloc[0]
    deploys = consulta(SQL_DEPLOYS_MES)
    equipes = consulta(SQL_SUCESSO_EQUIPE)
    etapas = consulta(SQL_FALHAS_ETAPA)
    projetos = consulta(SQL_DURACAO_FALHA)

    fig = plt.figure(figsize=(16, 10.5))
    fig.text(0.05, 0.955, "DevOps Pulse — Saúde das pipelines CI/CD",
             fontsize=20, fontweight="bold", color=TEXTO)
    fig.text(0.05, 0.93, "Período: maio a outubro de 2026 · fonte: banco devops_pulse (PostgreSQL)",
             fontsize=11, color=TEXTO_2)

    # Linha de indicadores (KPIs)
    kpi(fig, 0.05, "execuções de pipeline", f"{int(kpis.execucoes)}")
    kpi(fig, 0.29, "taxa de sucesso geral", f"{float(kpis.taxa_sucesso):.1f}%".replace(".", ","))
    kpi(fig, 0.53, "deploys em produção", f"{int(kpis.deploys_prod)}")
    kpi(fig, 0.77, "tempo médio p/ resolver incidente",
        f"{float(kpis.mttr_horas):.1f} h".replace(".", ","))

    gs = fig.add_gridspec(2, 2, left=0.05, right=0.97, top=0.80, bottom=0.06,
                          hspace=0.42, wspace=0.22)

    # 1) LINHA — evolução no tempo (deploys e rollbacks por mês)
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(deploys.mes, deploys.deploys, color=COR_1, linewidth=2,
             marker="o", markersize=6, label="Deploys em produção")
    ax1.plot(deploys.mes, deploys.rollbacks, color=COR_2, linewidth=2,
             marker="s", markersize=6, label="Rollbacks")
    for x, y in zip(deploys.mes, deploys.deploys):
        ax1.annotate(str(y), (x, y), textcoords="offset points", xytext=(0, 8),
                     ha="center", fontsize=9, color=TEXTO_2)
    ax1.set_title("Deploys em produção por mês")
    ax1.set_ylim(0, max(deploys.deploys) * 1.25)
    ax1.legend(frameon=False, loc="center right", fontsize=9)
    grade_y(ax1)

    # 2) BARRAS HORIZONTAIS — comparação entre itens (taxa de sucesso por equipe)
    ax2 = fig.add_subplot(gs[0, 1])
    barras = ax2.barh(equipes.equipe, equipes.taxa, color=COR_1, height=0.55)
    for b, v in zip(barras, equipes.taxa):
        ax2.text(b.get_width() + 0.6, b.get_y() + b.get_height() / 2,
                 f"{float(v):.1f}%".replace(".", ","), va="center", fontsize=9, color=TEXTO)
    ax2.set_title("Taxa de sucesso das pipelines por equipe")
    ax2.set_xlim(0, 105)
    ax2.set_xlabel("% de execuções com sucesso")
    ax2.grid(axis="x", color=GRADE, linewidth=0.8)
    ax2.set_axisbelow(True)
    ax2.tick_params(axis="y", length=0)

    # 3) COLUNAS — distribuição das falhas por etapa da pipeline
    ax3 = fig.add_subplot(gs[1, 0])
    nomes = {"build": "Build", "teste": "Testes", "scan_seguranca": "Scan de\nsegurança",
             "deploy": "Deploy"}
    rotulos = [nomes.get(e, e) for e in etapas.etapa]
    colunas = ax3.bar(rotulos, etapas.falhas, color=COR_1, width=0.5)
    total = etapas.falhas.sum()
    for c, v in zip(colunas, etapas.falhas):
        ax3.text(c.get_x() + c.get_width() / 2, c.get_height() + 0.3,
                 f"{v} ({100 * v / total:.0f}%)", ha="center", fontsize=9, color=TEXTO)
    ax3.set_title("Em qual etapa as pipelines falham")
    ax3.set_ylabel("nº de falhas")
    ax3.set_ylim(0, max(etapas.falhas) * 1.2)
    grade_y(ax3)

    # 4) DISPERSÃO — relação entre duração da pipeline e taxa de falha
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.scatter(projetos.duracao_min.astype(float), projetos.taxa_falha.astype(float),
                s=70, color=COR_1, edgecolor=SUPERFICIE, linewidth=1.5, zorder=3)
    destaque = projetos.sort_values("taxa_falha", ascending=False).head(3).projeto.tolist()
    destaque += projetos.sort_values("duracao_min", ascending=False).head(2).projeto.tolist()
    for _, r in projetos.iterrows():
        if r.projeto in destaque:
            ax4.annotate(r.projeto, (float(r.duracao_min), float(r.taxa_falha)),
                         textcoords="offset points", xytext=(6, 6), fontsize=9, color=TEXTO_2)
    ax4.set_title("Duração média x taxa de falha (por projeto)")
    ax4.set_xlabel("duração média da pipeline com sucesso (min)")
    ax4.set_ylabel("% de execuções com falha")
    ax4.set_xlim(0, projetos.duracao_min.astype(float).max() * 1.2)
    ax4.set_ylim(0, projetos.taxa_falha.astype(float).max() * 1.3)
    grade_y(ax4)
    ax4.grid(axis="x", color=GRADE, linewidth=0.8)

    fig.savefig("dashboard_devops_pulse.png", dpi=150)
    print("Dashboard salvo em dashboard_devops_pulse.png")
    if matplotlib.get_backend().lower() != "agg":
        plt.show()


if __name__ == "__main__":
    main()
