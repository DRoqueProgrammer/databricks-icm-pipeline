# Brazilian Public Data Sources — File/URL Gotchas

Real-world gotchas when downloading from INEP/IBGE/Base dos Dados for a Free Edition project. Each one burned real time in a session — save them before they bite you.

## INEP — IDEB: which file is the right one?

INEP publishes IDEB results under **3 different zips** on the same page. They look similar at a glance but contain **completely different data**:

| Zip file | Granularity | Rows | Use it for |
|---|---|---|---|
| `divulgacao_brasil_ideb_2023.zip` | Brasil aggregated | ~25 rows | Total Brasil charts only |
| `divulgacao_regioes_ufs_ideb_2023.zip` | UF aggregated | ~30 rows | State-level analysis |
| `divulgacao_municipios_ideb_2023.zip` | Município aggregated | ~5,570 rows | City comparison |
| **`divulgacao_anos_iniciais_escolas_2023.zip`** | **Escola** | **~65k** | **School-level analysis (the one you want)** |
| **`divulgacao_anos_finais_escolas_2023.zip`** | **Escola** | **~47k** | **School-level analysis (6-9 ano)** |
| **`divulgacao_ensino_medio_escolas_2023.zip`** | **Escola** | **~22k** | **School-level analysis (EM)** |

**Direct URL pattern (2023):**
- https://download.inep.gov.br/ideb/resultados/divulgacao_anos_iniciais_escolas_2023.zip
- https://download.inep.gov.br/ideb/resultados/divulgacao_anos_finais_escolas_2023.zip
- https://download.inep.gov.br/ideb/resultados/divulgacao_ensino_medio_escolas_2023.zip

**The "brasil" file is the trap.** Its first sheet (`Brasil (Anos Iniciais)`) has only ~25 rows of aggregated data, not school-level. If your smoke test returns 25 rows after `CREATE TABLE`, you downloaded the wrong file.

**Each school-level file is only ~10-100 MB compressed (5-15 MB extracted CSV).** Download all 3 school-level zips; they're cheap.

**Each zip contains:**
- `divulgacao_*.xlsx` (main, ~5-50 MB)
- `divulgacao_*.ods` (LibreOffice format, similar size)
- `md5_*.txt` (checksum file — ignore)

**Extract the xlsx → CSV locally** (avoid `binaryFile` 128MB limit on Free Edition), then upload. See SKILL.md "Robust extraction pattern".

## IBGE — PIB Municipalidades xlsx: 5 tabs, only 1 is right

The IBGE `tabelas_completas_2022.xlsx` (PIB dos Municípios 2022) has **5 tabs**, and only one of them has the per-capita data:

| Tab | Title (first cell) | Use it? |
|---|---|---|
| Tabela 1 | "100 maiores municípios em relação ao PIB" | ❌ PIB absoluto, top 100 |
| Tabela 2 | "30 maiores municípios em relação ao PIB" | ❌ PIB absoluto, top 30 |
| Tabela 3 | "30 menores municípios em relação ao PIB" | ❌ PIB absoluto, bottom 30 |
| **Tabela 4** | **"100 maiores municípios em relação ao PIB per capita"** | ✅ **THIS ONE** |
| Tabela 5 | "Participação percentual do PIB, número de municípios e população dos cinco municípios com maiores PIBs" | ❌ Top 5 share % |

**Picking heuristic in code** (works for any year):

```python
target_sheet = None
# Prefer "per capita" + "100 maiores" (the full per-capita ranking)
for name in wb.sheetnames:
    if "per capita" in name.lower() and "100 maiores" in name.lower():
        target_sheet = name
        break
# Fallback: any "per capita" tab
if not target_sheet:
    for name in wb.sheetnames:
        if "per capita" in name.lower():
            target_sheet = name
            break
# Last resort: first tab (probably wrong but better than failing)
if not target_sheet:
    target_sheet = wb.sheetnames[0]
```

**Don't trust sheet indices across years.** The 2022 file has Tabela 4 as per-capita, but the 2023 file might have it as Tabela 2 (IBGE reorders). Always inspect `wb.sheetnames` first and pick by name.

## Alternative PIB sources (if IBGE's xlsx is being weird)

If you can't get the IBGE xlsx to convert (encoding issues, sheet detection, etc.):

1. **Base dos Dados (BigQuery):** https://basedosdados.org/dataset/fcf025ca-8b19-4131-8e2d-5ddb12492347 — pre-cleaned PIB per capita, BigQuery access
2. **SIDRA (Tabela 5938):** https://sidra.ibge.gov.br/tabela/5938 — interactive table, CSV download per year/municipality, **cleaner than the xlsx** because the column structure is consistent across years
3. **API IBGE:** https://servicos.ibge.gov.br/api/docs/localidades — programmatic access

The SIDRA route is the **easiest** for a Free Edition project: open the page, filter to `Ano = 2022 + Município`, click "Download → CSV", and you get a clean ~5500 row CSV. No xlsx conversion, no sheet detection, no encoding guesswork.

## ENEM zip internal structure

INEP ENEM zips have a nested `DADOS/` folder:

```
microdados_enem_2023.zip
└── DADOS/
    ├── MICRODADOS_ENEM_2023.csv       # the main file (~1.7GB)
    ├── ITENS_PROVA_2023.csv           # per-question metadata, not needed
    └── QUEST_HAB_ESTUDO.csv          # some years only, ignore
```

**Unzip the right one:**

```bash
unzip -j microdados_enem_2023.zip "DADOS/MICRODADOS_ENEM_2023.csv" -d enem_extracted/enem_2023/
```

The `-j` flag strips the `DADOS/` prefix so the CSV lands directly in the target dir. Without `-j`, you'd get `DADOS/MICRODADOS_ENEM_2023.csv` and `spark.read.csv` would fail (no nested folders in `OPTIONS(path=...)`).

## Censo Escolar zip internal structure

The 2023 zip is **flat** (no nested folder):

```
microdados_censo_escolar_2023.zip
├── microdados_ed basica_2023.csv         # 201 MB, main file
└── suplemento_cursos_tecnicos_2023.csv  # 4 MB, supplemental
```

Note the **space in the filename** (`microdados_ed basica_2023.csv`). When unzipping, the space can break shell scripts that don't quote properly. Always quote:

```bash
unzip -j microdados_censo_escolar_2023.zip \
    "microdados_ed basica_2023.csv" \
    "suplemento_cursos_tecnicos_2023.csv" \
    -d censo_extracted/
```

## ENEM CSV columns you'll actually use

ENEM has ~80 columns in the raw CSV. Most are noise for analysis. The ones you need:

| Column | What | Notes |
|---|---|---|
| `NU_INSCRICAO` | Inscrição (anonymized participant id) | Use as the participant key |
| `TP_SEXO` | Sex (M/F) | One-letter, 2 distinct values |
| `TP_COR_RACA` | Race/color | 0=not declared, 1=branca, 2=preta, 3=parda, 4=amarela, 5=indígena |
| `TP_FAIXA_ETARIA` | Age bracket | Integer |
| `TP_ESCOLA` | School type (1=public, 2=private) | Critical for the inequidade analysis |
| `Q001`..`Q006` | Family background Q's | Q006 is family income bracket A-Q |
| `CO_ESCOLA` (pre-2020) / `CO_ESCOLA_EDUCACENSO_2023` (2023) | School code | Join key to Censo Escolar |
| `NU_NOTA_CN`, `NU_NOTA_CH`, `NU_NOTA_LC`, `NU_NOTA_MT`, `NU_NOTA_REDACAO` | Scores | The 5 exam areas |

**Naming drift warning:** column names changed across years. `CO_ESCOLA` (2020-2022) → `CO_ESCOLA_EDUCACENSO_<YEAR>` (2023+). Map in Silver.

## Power BI connection string in 2026+ Free Edition

The `brazilian-public-data-lakehouse` skill's Power BI section shows Azure-style hostnames (`adb-...`); those are **wrong for 2026+ Free Edition**. Updated pattern:

```
Server:  dbc-ad8bbac7-4dce.cloud.databricks.com    (your workspace URL, not the alias)
HTTP:    /sql/1.0/warehouses/<warehouse-id>
Auth:    OAuth (Microsoft / Google / GitHub)        (PAT is deprecated)
```

You can get the warehouse ID from the SQL Editor URL bar or `SHOW WAREHOUSES` in a notebook.

Power BI Desktop → Get Data → Databricks → paste the server + HTTP path → choose "Organizational account" → sign in with the same OAuth account you used to log into Databricks. The token is short-lived (~1h), but for DirectQuery from a local `.pbix`, Power BI re-auths automatically.

**Don't use the alias** `community.cloud.databricks.com` in Power BI — it redirects to a specific workspace that may not be yours. Use the per-workspace URL.
