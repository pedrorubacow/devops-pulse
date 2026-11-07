-- =====================================================================
-- Projeto: DevOps Pulse - Monitoramento de Pipelines CI/CD
-- Arquivo: consultas (SELECT) exigidas no trabalho
-- Execute: sudo -u postgres psql -d devops_pulse -f 02_consultas_select.sql
-- =====================================================================

-- ---------------------------------------------------------------------
-- CONSULTA 1 - JOIN com 2 tabelas
-- Últimas 10 execuções de pipeline que falharam, com o nome do projeto,
-- a etapa em que quebraram e quanto tempo rodaram até falhar.
-- ---------------------------------------------------------------------
SELECT p.nome                                   AS projeto,
       p.linguagem,
       e.branch,
       TO_CHAR(e.iniciado_em, 'DD/MM/YYYY HH24:MI') AS iniciado_em,
       e.etapa_falha,
       ROUND(e.duracao_seg / 60.0, 1)           AS minutos_ate_falha
FROM execucao_pipeline e
JOIN projeto p ON p.id_projeto = e.id_projeto
WHERE e.status = 'FALHA'
ORDER BY e.iniciado_em DESC
LIMIT 10;

-- ---------------------------------------------------------------------
-- CONSULTA 2 - JOIN com pelo menos 2 tabelas + GROUP BY + HAVING
-- Taxa de sucesso das pipelines por equipe (3 tabelas), considerando
-- apenas equipes com 60 execuções ou mais no período.
-- ---------------------------------------------------------------------
SELECT eq.nome                                               AS equipe,
       COUNT(*)                                              AS total_execucoes,
       COUNT(*) FILTER (WHERE e.status = 'SUCESSO')          AS sucessos,
       COUNT(*) FILTER (WHERE e.status = 'FALHA')            AS falhas,
       ROUND(100.0 * COUNT(*) FILTER (WHERE e.status = 'SUCESSO') / COUNT(*), 1)
                                                             AS taxa_sucesso_pct,
       ROUND(AVG(e.duracao_seg) / 60.0, 1)                   AS duracao_media_min
FROM equipe eq
JOIN projeto p           ON p.id_equipe  = eq.id_equipe
JOIN execucao_pipeline e ON e.id_projeto = p.id_projeto
GROUP BY eq.nome
HAVING COUNT(*) >= 60
ORDER BY taxa_sucesso_pct DESC;

-- ---------------------------------------------------------------------
-- CONSULTA 3 - JOIN com SUBSELECT
-- Projetos cuja duração média de pipeline (execuções com sucesso) está
-- ACIMA da média geral da empresa. O JOIN é feito com uma subconsulta
-- (tabela derivada) e o filtro usa uma segunda subconsulta escalar.
-- ---------------------------------------------------------------------
SELECT p.nome                               AS projeto,
       eq.nome                              AS equipe,
       p.linguagem,
       m.qtd_sucessos,
       ROUND(m.media_seg / 60.0, 1)         AS media_projeto_min,
       ROUND((SELECT AVG(duracao_seg)
              FROM execucao_pipeline
              WHERE status = 'SUCESSO') / 60.0, 1) AS media_geral_min
FROM projeto p
JOIN equipe eq ON eq.id_equipe = p.id_equipe
JOIN (
        SELECT id_projeto,
               COUNT(*)         AS qtd_sucessos,
               AVG(duracao_seg) AS media_seg
        FROM execucao_pipeline
        WHERE status = 'SUCESSO'
        GROUP BY id_projeto
     ) m ON m.id_projeto = p.id_projeto
WHERE m.media_seg > (SELECT AVG(duracao_seg)
                     FROM execucao_pipeline
                     WHERE status = 'SUCESSO')
ORDER BY m.media_seg DESC;

-- ---------------------------------------------------------------------
-- CONSULTAS DE APOIO AO DASHBOARD
-- ---------------------------------------------------------------------

-- 4) Deploys em produção por mês, com quantidade de rollbacks
SELECT TO_CHAR(DATE_TRUNC('month', d.data_deploy), 'YYYY-MM') AS mes,
       COUNT(*)                                               AS deploys_producao,
       COUNT(*) FILTER (WHERE d.rollback)                     AS rollbacks
FROM deploy d
WHERE d.ambiente = 'producao'
GROUP BY DATE_TRUNC('month', d.data_deploy)
ORDER BY 1;

-- 5) Em qual etapa as pipelines mais quebram
SELECT e.etapa_falha,
       COUNT(*)                                          AS falhas,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM execucao_pipeline e
WHERE e.status = 'FALHA'
GROUP BY e.etapa_falha
ORDER BY falhas DESC;

-- 6) Incidentes por severidade e tempo médio de resolução (MTTR)
SELECT i.severidade,
       COUNT(*)                                                         AS incidentes,
       ROUND(AVG(EXTRACT(EPOCH FROM (i.resolvido_em - i.aberto_em)) / 3600)::numeric, 1)
                                                                        AS mttr_horas
FROM incidente i
JOIN deploy d ON d.id_deploy = i.id_deploy
GROUP BY i.severidade
ORDER BY i.severidade;
