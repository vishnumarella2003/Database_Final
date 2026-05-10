# Lung Cancer Database — TCGA LUAD

A normalized relational database built from six TCGA Lung Adenocarcinoma (LUAD) datasets sourced from [cBioPortal](https://www.cbioportal.org/). The database integrates clinical, genomic, transcriptomic, and proteomic data to support biological analysis of lung cancer at the patient and tumor-sample level.

---

## Project Summary

This project transforms six raw TCGA LUAD flat files into a fully normalized relational database (1NF through BCNF/4NF, with 5NF-style mutation decomposition). The final schema consists of 16 tables covering patient demographics, clinical outcomes, tumor samples, somatic mutations, copy-number alterations, mRNA expression, and protein expression. The database is designed to support downstream biological queries such as survival analysis, mutation burden comparison, driver gene identification, and cross-omic integration.

---

## Tools and Technologies

- **DBMS:** MySQL
- **Programming language:** Python 3
- **Key packages:** `pandas`, `numpy`, `hashlib`, `sqlalchemy`, `mysql-connector-python`
- **Design tools:** MySQL Workbench (ERD/schema diagram)
- **Data source:** [cBioPortal — TCGA LUAD](https://www.cbioportal.org/)

---

## Repository Structure

```
lung-cancer-db/
├── README.md                        # Project overview and reproduction instructions
├── .gitignore
├── sql/
│   ├── 01_create_schema.sql         # Creates all 16 tables with keys and constraints
│   ├── 02_load_cleaned_data.sql     # Loads cleaned CSVs into the database
│   └── database_dump.sql            # Full SQL dump of the final populated database
├── scripts/
│   ├── 01_explore_datasets.py       # Preliminary analysis, missingness reports, schema suggestion
│   ├── 02_clean_data.py             # Cleaning, normalization, deduplication, type coercion
│   └── 03_export_for_sql.py         # Exports cleaned data to CSVs ready for SQL loading
├── data/
│   ├── raw/                         # Original source files from cBioPortal (not modified)
│   └── cleaned/                     # Cleaned CSV files used for database loading
├── docs/
│   ├── project_writeup.pdf          # Full design documentation and decision rationale
│   ├── data_dictionary.md           # Table names, field names, types, keys, and definitions
│   ├── script_execution_order.md    # Exact order and purpose of each script
│   └── decisions_and_limitations.md # Design deviations, known issues, and future work
└── diagrams/
    ├── conceptual_model.png         # High-level ER diagram
    └── logical_model_erd.png        # Full 16-table normalized schema diagram
```

---

## Data Sources

All data comes from the **TCGA Lung Adenocarcinoma (LUAD)** dataset available on [cBioPortal](https://www.cbioportal.org/).

| File | Rows | Columns | Description |
|---|---|---|---|
| `data_clinical_patient.txt` | 223 | 15 | Patient-level clinical and demographic data |
| `data_clinical_sample.txt` | 230 | 10 | Tumor sample metadata and cancer type |
| `data_mutations.txt` | 72,566 | 250* | Somatic mutation records (selected columns only) |
| `data_cna.txt` | 23,423 genes | 230 samples | Copy-number alteration matrix |
| `data_mrna_seq_v2_rsem.txt` | 20,466 genes | 230 samples | mRNA expression matrix (RSEM values) |
| `data_rppa.txt` | 160 protein markers | 181 samples | Reverse-phase protein array expression |

\* Only 22 biologically relevant columns were retained from `data_mutations.txt`.

> **Note:** Raw data files are not included in this repository due to size. Download them directly from [cBioPortal](https://www.cbioportal.org/) and place them in `data/raw/` before running any scripts.

---

## Database Schema Overview

The final database contains **16 tables** organized around three core entities: patients, samples, and genes.

**Patient tables:** `PATIENT`, `PATIENT_DEMOGRAPHIC`, `PATIENT_CLINICAL`, `PATIENT_SURVIVAL`, `PATIENT_SMOKING_HISTORY`

**Sample tables:** `CANCER_TYPE`, `SAMPLE`, `SAMPLE_STAGE`, `SAMPLE_METRIC`

**Genomic tables:** `GENE`, `GENOMIC_VARIANT`, `VARIANT_ANNOTATION`, `SAMPLE_MUTATION`

**Expression tables:** `COPY_NUMBER_ALTERATION`, `MRNA_EXPRESSION`, `PROTEIN_EXPRESSION`

See `diagrams/logical_model_erd.png` for the full schema with keys and relationships.

---

## How to Recreate the Database

### 1. Install required software

- Python 3.8 or later
- MySQL 8.0 or later
- Required Python packages:

```bash
pip install pandas numpy sqlalchemy mysql-connector-python
```

### 2. Download the raw data

Download the six TCGA LUAD files from [cBioPortal](https://www.cbioportal.org/) and place them in `data/raw/`.

### 3. Run the Python scripts in order

```bash
python scripts/01_explore_datasets.py   # Generates missingness reports and schema guidance
python scripts/02_clean_data.py         # Cleans, normalizes, and deduplicates all six files
python scripts/03_export_for_sql.py     # Exports 16 cleaned CSVs to data/cleaned/
```

### 4. Create the database schema

In MySQL, create a new database and run the schema script:

```sql
CREATE DATABASE lung_cancer_db;
USE lung_cancer_db;
SOURCE sql/01_create_schema.sql;
```

### 5. Load the cleaned data

```sql
SOURCE sql/02_load_cleaned_data.sql;
```

### 6. (Optional) Import the SQL dump instead

To skip steps 3–5 and load the pre-built database directly:

```bash
mysql -u your_username -p lung_cancer_db < sql/database_dump.sql
```

### Expected result

A fully populated MySQL database with 16 tables containing approximately:
- 223 patients, 230 samples
- 72,000+ mutation records across 3 variant tables
- ~5.4 million mRNA expression records
- ~5.4 million copy-number alteration records
- ~29,000 protein expression records

---

## Key Design Decisions

- **Mutation decomposition:** Mutation data is split into `GENOMIC_VARIANT` (raw position/allele), `VARIANT_ANNOTATION` (biological interpretation), and `SAMPLE_MUTATION` (sample-specific read counts), following 5NF-style decomposition.
- **Cancer type lookup table:** `CANCER_TYPE` was separated from `SAMPLE` to remove transitive dependency and satisfy 3NF.
- **AGE placement:** AGE is stored in `PATIENT_CLINICAL` rather than `PATIENT_DEMOGRAPHIC` because it is time-contextual (age at diagnosis), not a static attribute.
- **VARIANT_HASH:** A SHA-based hash column enforces uniqueness across the multi-column genomic variant key, working around MySQL index length limits on TEXT columns.
- **Full matrix inclusion:** All genes and all samples are retained in the CNA, mRNA, and RPPA tables to support broad biological queries, accepting a larger row count in exchange for completeness.

See `docs/decisions_and_limitations.md` for the full rationale and known limitations.

---

## Documentation and Diagrams

| Resource | Location |
|---|---|
| Full project write-up | `docs/project_writeup.pdf` |
| Data dictionary | `docs/data_dictionary.md` |
| Script execution order | `docs/script_execution_order.md` |
| Design decisions and limitations | `docs/decisions_and_limitations.md` |
| Conceptual ER diagram | `diagrams/conceptual_model.png` |
| Logical normalized schema | `diagrams/logical_model_erd.png` |

---

## Example Query

The following query retrieves the top mutated genes by number of unique samples affected, filtered to missense mutations with MODERATE impact:

```sql
SELECT
    g.HUGO_SYMBOL,
    va.VARIANT_CLASSIFICATION,
    va.IMPACT,
    COUNT(DISTINCT sm.SAMPLE_ID) AS SAMPLES_MUTATED
FROM GENE g
JOIN VARIANT_ANNOTATION va ON va.GENE_ID = g.GENE_ID
JOIN GENOMIC_VARIANT gv ON gv.VARIANT_ID = va.VARIANT_ID
JOIN SAMPLE_MUTATION sm ON sm.VARIANT_ID = gv.VARIANT_ID
GROUP BY g.HUGO_SYMBOL, va.VARIANT_CLASSIFICATION, va.IMPACT
HAVING SAMPLES_MUTATED >= 10
ORDER BY SAMPLES_MUTATED DESC
LIMIT 50;
```

---

## Limitations and Future Work

- `DFS_STATUS` and `DFS_MONTHS` (disease-free survival) were excluded due to complete missingness in the source data.
- 228 of the original 250 mutation columns were excluded; external annotation fields (COSMIC, ExAC, GO, DrugBank) can be added in a future extension table.
- The schema assumes one clinical, survival, and staging record per patient/sample. Longitudinal records would require constraint changes and date fields.
- Full formal 5NF is not claimed, as proving all join dependencies would require explicit business rule documentation beyond the scope of this project.
