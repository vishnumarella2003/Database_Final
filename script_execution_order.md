# Script Execution Order

Run all scripts in the order listed below. Do not skip steps or change the order,
as each script depends on the outputs of the previous one.

---

## Step 1 — Data Exploration

**File:** `database_exploration_cleaning.py` (Part 1: Exploration)  
**Environment:** Google Colab  
**Input:** Six raw `.txt` files from cBioPortal in Google Drive  
**Output:** Decision-support CSVs and a written report (zipped and downloaded)

What it does:
- Loads all six raw cBioPortal files
- Generates column-by-column missingness reports and keep/discard recommendations
- Summarizes sample and gene overlap across datasets
- Identifies top mutated genes and variant classifications
- Checks presence of known LUAD driver genes (EGFR, KRAS, TP53, etc.)
- Produces a recommended table plan and written decision report

---

## Step 2 — Data Cleaning

**File:** `database_exploration_cleaning.py` (Part 2: Cleaning)  
**Environment:** Google Colab  
**Input:** Six raw `.txt` files from cBioPortal in Google Drive  
**Output:** Cleaned CSV staging files (zipped and downloaded)

What it does:
- Standardizes all missing values to NaN
- Normalizes column names to uppercase with underscores
- Standardizes sample barcodes (underscores replaced with hyphens)
- Derives patient barcodes from sample barcodes where needed
- Standardizes gene symbols to uppercase
- Parses RPPA identifiers into HUGO_SYMBOL and ANTIBODY_REF
- Coerces numeric fields to correct types
- Deduplicates patients, samples, variants, and genes
- Converts CNA, mRNA, and RPPA matrices from wide to long format
- Splits mutation data into three staging files:
  - `genomic_variant_source.csv` — raw variant positions and alleles
  - `variant_annotation_source.csv` — biological annotation
  - `sample_mutation_source.csv` — sample-specific read counts
- Generates VARIANT_HASH for each unique genomic variant
- Produces a validation report of row counts and overlap checks

Cleaned files produced:

| File | Supports Table(s) |
|---|---|
| `clinical_patient_clean.csv` | PATIENT, PATIENT_DEMOGRAPHIC, PATIENT_CLINICAL, PATIENT_SURVIVAL, PATIENT_SMOKING_HISTORY |
| `clinical_sample_clean.csv` | SAMPLE, SAMPLE_STAGE, SAMPLE_METRIC |
| `cancer_type_ref_source.csv` | CANCER_TYPE |
| `genomic_variant_source.csv` | GENOMIC_VARIANT |
| `variant_annotation_source.csv` | VARIANT_ANNOTATION |
| `sample_mutation_source.csv` | SAMPLE_MUTATION |
| `cna_long_clean.csv` | COPY_NUMBER_ALTERATION |
| `mrna_long_clean.csv` | MRNA_EXPRESSION |
| `rppa_long_clean.csv` | PROTEIN_EXPRESSION |
| `gene_source_all.csv` | GENE |

---

## Step 3 — SQL File Generation

**File:** `Database_loadsql.py`  
**Environment:** Local Python (run on your machine)  
**Input:** Cleaned CSV staging files from Step 2  
**Output:** Numbered SQL files ready for import into MySQL

What it does:
- Reads all cleaned CSV files
- Generates INSERT statements for all 16 tables
- Resolves foreign keys using subquery lookups on natural identifiers
- Splits large tables (CNA, mRNA, RPPA) into 4 part files each to avoid phpMyAdmin timeouts
- Generates a master load file and a validation counts file

SQL files produced and their load order:

| Order | File | Contents |
|---|---|---|
| 1 | `01_patient_tables.sql` | PATIENT, PATIENT_DEMOGRAPHIC, PATIENT_CLINICAL, PATIENT_SURVIVAL, PATIENT_SMOKING_HISTORY |
| 2 | `02_sample_tables.sql` | CANCER_TYPE, SAMPLE, SAMPLE_STAGE, SAMPLE_METRIC |
| 3 | `03_gene_variant_tables.sql` | GENE, GENOMIC_VARIANT, VARIANT_ANNOTATION |
| 4 | `04_mutation_bridge_tables.sql` | SAMPLE_MUTATION |
| 5 | `05_cna_part_1.sql` to `05_cna_part_4.sql` | COPY_NUMBER_ALTERATION |
| 6 | `06_mrna_part_1.sql` to `06_mrna_part_4.sql` | MRNA_EXPRESSION |
| 7 | `07_rppa_part_1.sql` to `07_rppa_part_4.sql` | PROTEIN_EXPRESSION |
| 8 | `99_validation_counts.sql` | Row count checks for all 16 tables |

---

## Step 4 — Schema Creation

**File:** `01_create_schema.sql`  
**Environment:** MySQL / phpMyAdmin  
**Input:** None  
**Output:** All 16 empty tables with primary keys, foreign keys, and constraints

Run this before any data is loaded.

---

## Step 5 — Data Loading

**Environment:** MySQL / phpMyAdmin  
**Input:** SQL files generated in Step 3

Import each SQL file in the order shown in Step 3.
For the large part files (CNA, mRNA, RPPA), import one part at a time.
If a part times out, rerunning it is safe because all inserts use INSERT IGNORE.
