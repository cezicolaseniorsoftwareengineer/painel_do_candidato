# Painel Eleitoral do Candidato

Painel estático para consulta e cruzamento de resultados eleitorais por candidata/o, ano, município, região, zona e referência territorial.

## Fontes e atualização

A base local é gerada por build_dashboard_data.py a partir dos CSVs consolidados do projeto. Os registros integrais dos candidatos são extraídos por extract_full_candidate_records.py e reconciliados por contagem, soma de votos e chave município-zona.

O Portal de Dados Abertos do TSE é a fonte oficial recomendada para futuros adapters de resultados, candidaturas, eleitorado e prestação de contas: https://dadosabertos.tse.jus.br/

Integração remota deve usar adapter versionado, validação de schema, cache com expiração, rate limit, logs sanitizados e fallback para a base reconciliada local. O painel não faz scraping nem envia CPF/RG.

## Testes

Comandos:

    python -m py_compile build_dashboard_data.py extract_full_candidate_records.py
    node --check app.js
    node --test app.test.js
