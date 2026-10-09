# Painel Eleitoral do Candidato

Painel estático para consulta e cruzamento de resultados eleitorais por candidata/o, ano, município, região, zona e referência territorial. O catálogo cobre candidaturas do Estado de São Paulo aos cargos de vereador, deputado estadual e deputado federal nos ciclos disponíveis desde 2020.

A identidade histórica não depende do partido nem do número da candidatura. O build vincula os registros pela combinação normalizada de nome civil e data de nascimento, publica somente um identificador irreversível e permite busca exata pelos nomes civil e de urna. Homônimos permanecem separados e são apresentados para desambiguação.

## Fontes e atualização

A base local é gerada por build_dashboard_data.py a partir dos CSVs consolidados do projeto. O catálogo integral é gerado por build_electoral_catalog.py, que publica no manifesto as contagens por ano e cargo. Os registros integrais dos candidatos são extraídos por extract_full_candidate_records.py e reconciliados por contagem, soma de votos e chave município-zona.

"100%" significa igualdade entre todas as linhas dos arquivos oficiais TSE carregados para SP e todas as candidaturas elegíveis emitidas pelo build. Não significa cobertura nacional; para isso, os arquivos das 27 UFs precisam ser ingeridos e auditados pelo mesmo contrato.

O Portal de Dados Abertos do TSE é a fonte oficial recomendada para futuros adapters de resultados, candidaturas, eleitorado e prestação de contas: https://dadosabertos.tse.jus.br/

Integração remota deve usar adapter versionado, validação de schema, cache com expiração, rate limit, logs sanitizados e fallback para a base reconciliada local. O painel não faz scraping nem envia CPF/RG.

## Testes

Comandos:

    python -m py_compile build_dashboard_data.py extract_full_candidate_records.py
    node --check app.js
    node --test app.test.js
