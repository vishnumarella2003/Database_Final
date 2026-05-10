from pathlib import Path
import pandas as pd
import math

# ============================================================
# LUAD FINAL ERD SQL GENERATOR - FULL VERSION WITH SPLIT LARGE FILES
#
# Purpose:
#   Generate SQL load scripts for all final ERD tables.
#
# Fixes included:
#   1. All output files are saved under:
#        /Users/vishnumarella/Desktop/load data sql
#
#   2. Every generated SQL file starts with:
#        USE check123;
#
#   3. GENOMIC_VARIANT.VARIANT_HASH is a generated column.
#      This script DOES NOT insert into VARIANT_HASH.
#
#   4. Large tables are split into smaller SQL files:
#        COPY_NUMBER_ALTERATION -> 05_cna_part_1.sql ... 05_cna_part_4.sql
#        MRNA_EXPRESSION        -> 06_mrna_part_1.sql ... 06_mrna_part_4.sql
#        PROTEIN_EXPRESSION     -> 07_rppa_part_1.sql ... 07_rppa_part_4.sql
#
# Input folder:
#   /Users/vishnumarella/Downloads/luad_cleaned_staging_files
#
# Output folder:
#   /Users/vishnumarella/Desktop/load data sql
# ============================================================


# ============================================================
# 1. PATHS AND DATABASE NAME
# ============================================================

DATABASE_NAME = "check123"

INPUT_DIR = Path("/Users/vishnumarella/Downloads/luad_cleaned_staging_files")
OUTPUT_DIR = Path("/Users/vishnumarella/Desktop/load data sql")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. OPTIONS
# ============================================================

INCLUDE_CNA = True
INCLUDE_MRNA = True
INCLUDE_RPPA = True

# Small chunks for normal tables.
SMALL_CHUNK = 100
MEDIUM_CHUNK = 50

# Split settings for large tables.
NUM_LARGE_PARTS = 4

# Smaller INSERT statements are safer for phpMyAdmin.
# If phpMyAdmin still times out, reduce this to 10.
LARGE_INSERT_CHUNK = 25


# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================

def is_blank(x):
    if x is None:
        return True

    try:
        if pd.isna(x):
            return True
    except Exception:
        pass

    if isinstance(x, float) and math.isnan(x):
        return True

    s = str(x).strip()
    return s == "" or s.lower() in {"nan", "none", "null", "<na>"}


def clean_text(x):
    if is_blank(x):
        return None
    return str(x).strip()


def sql_str(x):
    if is_blank(x):
        return "NULL"

    return "'" + str(x).replace("'", "''").strip() + "'"


def sql_int(x):
    if is_blank(x):
        return "NULL"

    try:
        return str(int(float(x)))
    except Exception:
        return "NULL"


def sql_decimal(x):
    if is_blank(x):
        return "NULL"

    try:
        return str(float(x))
    except Exception:
        return "NULL"


def read_csv_required(filename):
    path = INPUT_DIR / filename

    print("Looking for:", path)

    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    df = pd.read_csv(path, dtype=object, low_memory=False)
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df


def chunks(lst, n=100):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def bulk_insert(table, cols, rows, chunk_size=100, insert_ignore=True):
    if not rows:
        return f"-- No rows for {table}\n\n"

    col_list = ", ".join(cols)
    insert_keyword = "INSERT IGNORE" if insert_ignore else "INSERT"

    out = []

    for part in chunks(rows, chunk_size):
        values = ",\n  ".join(["(" + ", ".join(r) + ")" for r in part])
        out.append(
            f"{insert_keyword} INTO {table} ({col_list})\n"
            f"VALUES\n"
            f"  {values};\n\n"
        )

    return "".join(out)


def write_sql_file(filename, sql_parts):
    output_path = OUTPUT_DIR / filename

    final_sql = []
    final_sql.append(f"USE {DATABASE_NAME};\n\n")
    final_sql.extend(sql_parts)

    output_path.write_text("".join(final_sql), encoding="utf-8")
    size_mb = output_path.stat().st_size / (1024 * 1024)

    print(f"Created: {output_path} ({size_mb:.2f} MB)")
    return output_path


def patient_fk(patient_barcode):
    return (
        f"(SELECT PATIENT_ID FROM PATIENT "
        f"WHERE PATIENT_BARCODE = {sql_str(patient_barcode)} LIMIT 1)"
    )


def sample_fk(sample_barcode):
    return (
        f"(SELECT SAMPLE_ID FROM SAMPLE "
        f"WHERE SAMPLE_BARCODE = {sql_str(sample_barcode)} LIMIT 1)"
    )


def gene_fk(hugo_symbol):
    return (
        f"(SELECT GENE_ID FROM GENE "
        f"WHERE HUGO_SYMBOL = {sql_str(hugo_symbol)} LIMIT 1)"
    )


def cancer_type_fk(oncotree_code):
    if is_blank(oncotree_code):
        return "NULL"

    return (
        f"(SELECT CANCER_TYPE_ID FROM CANCER_TYPE "
        f"WHERE ONCOTREE_CODE = {sql_str(oncotree_code)} LIMIT 1)"
    )


def variant_fk(variant_hash):
    return (
        f"(SELECT VARIANT_ID FROM GENOMIC_VARIANT "
        f"WHERE VARIANT_HASH = {sql_str(variant_hash)} LIMIT 1)"
    )


def validate_columns(df, required_cols, label):
    missing = set(required_cols) - set(df.columns)

    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


# ============================================================
# 4. READ CLEANED CSV FILES
# ============================================================

clinical_patient = read_csv_required("clinical_patient_clean.csv")
clinical_sample = read_csv_required("clinical_sample_clean.csv")
cancer_type_ref = read_csv_required("cancer_type_ref_source.csv")
gene_source = read_csv_required("gene_source_all.csv")
genomic_variant_source = read_csv_required("genomic_variant_source.csv")
variant_annotation_source = read_csv_required("variant_annotation_source.csv")
sample_mutation_source = read_csv_required("sample_mutation_source.csv")

if INCLUDE_CNA:
    cna_long = read_csv_required("cna_long_clean.csv")
    validate_columns(cna_long, ["SAMPLE_BARCODE", "HUGO_SYMBOL", "CNA_VALUE"], "cna_long_clean.csv")
else:
    cna_long = pd.DataFrame()

if INCLUDE_MRNA:
    mrna_long = read_csv_required("mrna_long_clean.csv")
    validate_columns(mrna_long, ["SAMPLE_BARCODE", "HUGO_SYMBOL", "RSEM_VALUE"], "mrna_long_clean.csv")
else:
    mrna_long = pd.DataFrame()

if INCLUDE_RPPA:
    rppa_long = read_csv_required("rppa_long_clean.csv")
    validate_columns(
        rppa_long,
        ["SAMPLE_BARCODE", "HUGO_SYMBOL", "ANTIBODY_REF", "EXPRESSION_VALUE"],
        "rppa_long_clean.csv"
    )
else:
    rppa_long = pd.DataFrame()


# ============================================================
# 5. PATIENT TABLES
# ============================================================

patient_rows = []
patient_demo_rows = []
patient_clinical_rows = []
patient_survival_rows = []
patient_smoking_rows = []

for _, r in clinical_patient.iterrows():
    patient_barcode = clean_text(r.get("PATIENT_BARCODE"))

    if is_blank(patient_barcode):
        continue

    patient_rows.append((
        sql_str(patient_barcode),
    ))

    patient_demo_rows.append((
        patient_fk(patient_barcode),
        sql_str(r.get("SEX")),
    ))

    patient_clinical_rows.append((
        patient_fk(patient_barcode),
        sql_int(r.get("AGE")),
        sql_str(r.get("HISTOLOGICAL_SUBTYPE")),
        sql_str(r.get("PRETREATMENT_HISTORY")),
        sql_str(r.get("PRIMARY_TUMOR_PATHOLOGIC_SPREAD")),
        sql_str(r.get("PRIOR_DIAGNOSIS")),
        sql_str(r.get("RESIDUAL_TUMOR")),
    ))

    patient_survival_rows.append((
        patient_fk(patient_barcode),
        sql_str(r.get("OS_STATUS")),
        sql_decimal(r.get("OS_MONTHS")),
    ))

    patient_smoking_rows.append((
        patient_fk(patient_barcode),
        sql_str(r.get("TOBACCO_SMOKING_HISTORY_INDICATOR")),
    ))

patient_sql = []
patient_sql.append("-- ============================================================\n")
patient_sql.append("-- 01 PATIENT TABLES\n")
patient_sql.append("-- ============================================================\n\n")
patient_sql.append("START TRANSACTION;\n\n")

patient_sql.append(
    bulk_insert(
        "PATIENT",
        ["PATIENT_BARCODE"],
        patient_rows,
        chunk_size=SMALL_CHUNK
    )
)

patient_sql.append(
    bulk_insert(
        "PATIENT_DEMOGRAPHIC",
        ["PATIENT_ID", "SEX"],
        patient_demo_rows,
        chunk_size=SMALL_CHUNK
    )
)

patient_sql.append(
    bulk_insert(
        "PATIENT_CLINICAL",
        [
            "PATIENT_ID",
            "AGE",
            "HISTOLOGICAL_SUBTYPE",
            "PRETREATMENT_HISTORY",
            "PRIMARY_TUMOR_PATHOLOGIC_SPREAD",
            "PRIOR_DIAGNOSIS",
            "RESIDUAL_TUMOR"
        ],
        patient_clinical_rows,
        chunk_size=SMALL_CHUNK
    )
)

patient_sql.append(
    bulk_insert(
        "PATIENT_SURVIVAL",
        ["PATIENT_ID", "OS_STATUS", "OS_MONTHS"],
        patient_survival_rows,
        chunk_size=SMALL_CHUNK
    )
)

patient_sql.append(
    bulk_insert(
        "PATIENT_SMOKING_HISTORY",
        ["PATIENT_ID", "TOBACCO_SMOKING_HISTORY_INDICATOR"],
        patient_smoking_rows,
        chunk_size=SMALL_CHUNK
    )
)

patient_sql.append("COMMIT;\n")

write_sql_file("01_patient_tables.sql", patient_sql)


# ============================================================
# 6. SAMPLE TABLES
# ============================================================

cancer_type_rows = []
sample_rows = []
sample_stage_rows = []
sample_metric_rows = []

for _, r in cancer_type_ref.iterrows():
    cancer_type_rows.append((
        sql_str(r.get("ONCOTREE_CODE")),
        sql_str(r.get("CANCER_TYPE")),
        sql_str(r.get("CANCER_TYPE_DETAILED")),
    ))

for _, r in clinical_sample.iterrows():
    sample_barcode = clean_text(r.get("SAMPLE_BARCODE"))
    patient_barcode = clean_text(r.get("PATIENT_BARCODE"))

    if is_blank(sample_barcode) or is_blank(patient_barcode):
        continue

    sample_rows.append((
        sql_str(sample_barcode),
        patient_fk(patient_barcode),
        cancer_type_fk(r.get("ONCOTREE_CODE")),
        sql_str(r.get("SOMATIC_STATUS")),
    ))

    sample_stage_rows.append((
        sample_fk(sample_barcode),
        sql_str(r.get("TUMOR_STAGE_2009")),
        sql_str(r.get("DISTANT_METASTASIS_PATHOLOGIC_SPREAD")),
    ))

    sample_metric_rows.append((
        sample_fk(sample_barcode),
        sql_decimal(r.get("TMB_NONSYNONYMOUS")),
    ))

sample_sql = []
sample_sql.append("-- ============================================================\n")
sample_sql.append("-- 02 SAMPLE TABLES\n")
sample_sql.append("-- ============================================================\n\n")
sample_sql.append("START TRANSACTION;\n\n")

sample_sql.append(
    bulk_insert(
        "CANCER_TYPE",
        ["ONCOTREE_CODE", "CANCER_TYPE", "CANCER_TYPE_DETAILED"],
        cancer_type_rows,
        chunk_size=SMALL_CHUNK
    )
)

sample_sql.append(
    bulk_insert(
        "SAMPLE",
        ["SAMPLE_BARCODE", "PATIENT_ID", "CANCER_TYPE_ID", "SOMATIC_STATUS"],
        sample_rows,
        chunk_size=SMALL_CHUNK
    )
)

sample_sql.append(
    bulk_insert(
        "SAMPLE_STAGE",
        ["SAMPLE_ID", "TUMOR_STAGE_2009", "DISTANT_METASTASIS_PATHOLOGIC_SPREAD"],
        sample_stage_rows,
        chunk_size=SMALL_CHUNK
    )
)

sample_sql.append(
    bulk_insert(
        "SAMPLE_METRIC",
        ["SAMPLE_ID", "TMB_NONSYNONYMOUS"],
        sample_metric_rows,
        chunk_size=SMALL_CHUNK
    )
)

sample_sql.append("COMMIT;\n")

write_sql_file("02_sample_tables.sql", sample_sql)


# ============================================================
# 7. GENE AND GENOMIC_VARIANT
# ============================================================

gene_rows = []
variant_rows = []

for _, r in gene_source.iterrows():
    hugo = clean_text(r.get("HUGO_SYMBOL"))

    if is_blank(hugo):
        continue

    gene_rows.append((
        sql_str(hugo),
        sql_int(r.get("ENTREZ_GENE_ID")),
    ))

for _, r in genomic_variant_source.iterrows():
    # IMPORTANT:
    # Do NOT insert VARIANT_HASH here.
    # VARIANT_HASH is a generated column in MySQL.
    variant_rows.append((
        sql_str(r.get("CHROMOSOME")),
        sql_int(r.get("START_POSITION")),
        sql_int(r.get("END_POSITION")),
        sql_str(r.get("REFERENCE_ALLELE")),
        sql_str(r.get("TUMOR_SEQ_ALLELE1")),
        sql_str(r.get("TUMOR_SEQ_ALLELE2")),
    ))

gene_variant_sql = []
gene_variant_sql.append("-- ============================================================\n")
gene_variant_sql.append("-- 03 GENE AND GENOMIC VARIANT TABLES\n")
gene_variant_sql.append("-- FIXED: VARIANT_HASH is generated by MySQL, not inserted.\n")
gene_variant_sql.append("-- ============================================================\n\n")
gene_variant_sql.append("START TRANSACTION;\n\n")

gene_variant_sql.append(
    bulk_insert(
        "GENE",
        ["HUGO_SYMBOL", "ENTREZ_GENE_ID"],
        gene_rows,
        chunk_size=SMALL_CHUNK
    )
)

gene_variant_sql.append(
    bulk_insert(
        "GENOMIC_VARIANT",
        [
            "CHROMOSOME",
            "START_POSITION",
            "END_POSITION",
            "REFERENCE_ALLELE",
            "TUMOR_SEQ_ALLELE1",
            "TUMOR_SEQ_ALLELE2"
        ],
        variant_rows,
        chunk_size=MEDIUM_CHUNK
    )
)

gene_variant_sql.append("COMMIT;\n")

write_sql_file("03_gene_variant_tables.sql", gene_variant_sql)


# ============================================================
# 8. VARIANT_ANNOTATION AND SAMPLE_MUTATION
# ============================================================

variant_annotation_rows = []
sample_mutation_rows = []

for _, r in variant_annotation_source.iterrows():
    variant_hash = clean_text(r.get("VARIANT_HASH"))
    hugo = clean_text(r.get("HUGO_SYMBOL"))

    if is_blank(variant_hash) or is_blank(hugo):
        continue

    variant_annotation_rows.append((
        variant_fk(variant_hash),
        gene_fk(hugo),
        sql_str(r.get("VARIANT_CLASSIFICATION")),
        sql_str(r.get("VARIANT_TYPE")),
        sql_str(r.get("CONSEQUENCE")),
        sql_str(r.get("IMPACT")),
        sql_str(r.get("HGVSC")),
        sql_str(r.get("HGVSP")),
        sql_str(r.get("HGVSP_SHORT")),
        sql_str(r.get("TRANSCRIPT_ID")),
        sql_str(r.get("PROTEIN_POSITION")),
        sql_str(r.get("CODONS")),
        sql_str(r.get("HOTSPOT")),
    ))

for _, r in sample_mutation_source.iterrows():
    sample_barcode = clean_text(r.get("SAMPLE_BARCODE"))
    variant_hash = clean_text(r.get("VARIANT_HASH"))

    if is_blank(sample_barcode) or is_blank(variant_hash):
        continue

    sample_mutation_rows.append((
        sample_fk(sample_barcode),
        variant_fk(variant_hash),
        sql_int(r.get("T_REF_COUNT")),
        sql_int(r.get("T_ALT_COUNT")),
    ))

mutation_sql = []
mutation_sql.append("-- ============================================================\n")
mutation_sql.append("-- 04 VARIANT ANNOTATION AND SAMPLE MUTATION TABLES\n")
mutation_sql.append("-- ============================================================\n\n")
mutation_sql.append("START TRANSACTION;\n\n")

mutation_sql.append(
    bulk_insert(
        "VARIANT_ANNOTATION",
        [
            "VARIANT_ID",
            "GENE_ID",
            "VARIANT_CLASSIFICATION",
            "VARIANT_TYPE",
            "CONSEQUENCE",
            "IMPACT",
            "HGVSC",
            "HGVSP",
            "HGVSP_SHORT",
            "TRANSCRIPT_ID",
            "PROTEIN_POSITION",
            "CODONS",
            "HOTSPOT"
        ],
        variant_annotation_rows,
        chunk_size=MEDIUM_CHUNK
    )
)

mutation_sql.append(
    bulk_insert(
        "SAMPLE_MUTATION",
        ["SAMPLE_ID", "VARIANT_ID", "T_REF_COUNT", "T_ALT_COUNT"],
        sample_mutation_rows,
        chunk_size=MEDIUM_CHUNK
    )
)

mutation_sql.append("COMMIT;\n")

write_sql_file("04_mutation_bridge_tables.sql", mutation_sql)


# ============================================================
# 9. SPLIT LARGE TABLE GENERATOR
# ============================================================

def split_large_measurement_sql(
    df,
    table_name,
    output_prefix,
    value_column,
    value_sql_function,
    extra_column=None,
    extra_column_sql_function=None,
    num_parts=4
):
    print("\n============================================================")
    print(f"STARTING SPLIT SQL GENERATION FOR {table_name}")
    print("============================================================")

    total_rows = len(df)
    part_size = math.ceil(total_rows / num_parts)

    print(f"Total source rows: {total_rows:,}")
    print(f"Rows per part: approximately {part_size:,}")

    generated_files = []

    for part_num in range(1, num_parts + 1):
        start = (part_num - 1) * part_size
        end = min(start + part_size, total_rows)

        part_df = df.iloc[start:end].copy()
        sql_rows = []

        for _, r in part_df.iterrows():
            sample_barcode = clean_text(r.get("SAMPLE_BARCODE"))
            hugo = clean_text(r.get("HUGO_SYMBOL"))

            if is_blank(sample_barcode) or is_blank(hugo):
                continue

            if extra_column:
                sql_rows.append((
                    sample_fk(sample_barcode),
                    gene_fk(hugo),
                    extra_column_sql_function(r.get(extra_column)),
                    value_sql_function(r.get(value_column)),
                ))
            else:
                sql_rows.append((
                    sample_fk(sample_barcode),
                    gene_fk(hugo),
                    value_sql_function(r.get(value_column)),
                ))

        sql_parts = []
        sql_parts.append("SET autocommit = 1;\n\n")
        sql_parts.append("-- ============================================================\n")
        sql_parts.append(f"-- {table_name} LOAD - PART {part_num} OF {num_parts}\n")
        sql_parts.append(f"-- Source rows: {start + 1:,} to {end:,}\n")
        sql_parts.append(f"-- SQL rows generated: {len(sql_rows):,}\n")
        sql_parts.append("-- ============================================================\n\n")

        if extra_column:
            cols = ["SAMPLE_ID", "GENE_ID", extra_column, value_column]
        else:
            cols = ["SAMPLE_ID", "GENE_ID", value_column]

        sql_parts.append(
            bulk_insert(
                table_name,
                cols,
                sql_rows,
                chunk_size=LARGE_INSERT_CHUNK
            )
        )

        output_file_name = f"{output_prefix}_part_{part_num}.sql"
        write_sql_file(output_file_name, sql_parts)

        generated_files.append(output_file_name)

    master_sql = []
    master_sql.append("-- ============================================================\n")
    master_sql.append(f"-- MASTER LOAD FILE FOR {table_name}\n")
    master_sql.append("-- If phpMyAdmin times out, run each part manually instead.\n")
    master_sql.append("-- ============================================================\n\n")

    for filename in generated_files:
        master_sql.append(f"SOURCE {filename};\n")

    master_file_name = f"{output_prefix}_master.sql"
    write_sql_file(master_file_name, master_sql)

    print(f"FINISHED SPLIT SQL GENERATION FOR {table_name}")

    return generated_files


# ============================================================
# 10. CNA SPLIT FILES
# ============================================================

if INCLUDE_CNA:
    cna_files = split_large_measurement_sql(
        df=cna_long,
        table_name="COPY_NUMBER_ALTERATION",
        output_prefix="05_cna",
        value_column="CNA_VALUE",
        value_sql_function=sql_int,
        num_parts=NUM_LARGE_PARTS
    )
else:
    cna_files = []


# ============================================================
# 11. MRNA SPLIT FILES
# ============================================================

if INCLUDE_MRNA:
    mrna_files = split_large_measurement_sql(
        df=mrna_long,
        table_name="MRNA_EXPRESSION",
        output_prefix="06_mrna",
        value_column="RSEM_VALUE",
        value_sql_function=sql_decimal,
        num_parts=NUM_LARGE_PARTS
    )
else:
    mrna_files = []


# ============================================================
# 12. RPPA / PROTEIN EXPRESSION SPLIT FILES
# ============================================================

if INCLUDE_RPPA:
    rppa_files = split_large_measurement_sql(
        df=rppa_long,
        table_name="PROTEIN_EXPRESSION",
        output_prefix="07_rppa",
        value_column="EXPRESSION_VALUE",
        value_sql_function=sql_decimal,
        extra_column="ANTIBODY_REF",
        extra_column_sql_function=sql_str,
        num_parts=NUM_LARGE_PARTS
    )
else:
    rppa_files = []


# ============================================================
# 13. CLEAN RESTART SCRIPT FOR LARGE TABLES
# ============================================================

restart_sql = []
restart_sql.append("-- ============================================================\n")
restart_sql.append("-- CLEAN RESTART FOR LARGE MOLECULAR TABLES\n")
restart_sql.append("-- WARNING: This deletes CNA, mRNA, and RPPA/protein expression rows.\n")
restart_sql.append("-- Run only if you want to restart loading large tables from zero.\n")
restart_sql.append("-- ============================================================\n\n")

restart_sql.append("SET FOREIGN_KEY_CHECKS = 0;\n\n")
restart_sql.append("TRUNCATE TABLE COPY_NUMBER_ALTERATION;\n")
restart_sql.append("TRUNCATE TABLE MRNA_EXPRESSION;\n")
restart_sql.append("TRUNCATE TABLE PROTEIN_EXPRESSION;\n\n")
restart_sql.append("SET FOREIGN_KEY_CHECKS = 1;\n")

write_sql_file("00_clean_restart_large_tables.sql", restart_sql)


# ============================================================
# 14. MASTER LOAD FILE
# ============================================================

master_sql = []
master_sql.append("-- ============================================================\n")
master_sql.append("-- MASTER LOAD SCRIPT\n")
master_sql.append("-- Run this from the same folder as the generated SQL files.\n")
master_sql.append("-- Recommended: run each part manually in phpMyAdmin if timeout occurs.\n")
master_sql.append("-- ============================================================\n\n")

master_sql.append("SET FOREIGN_KEY_CHECKS = 1;\n\n")
master_sql.append("SOURCE 01_patient_tables.sql;\n")
master_sql.append("SOURCE 02_sample_tables.sql;\n")
master_sql.append("SOURCE 03_gene_variant_tables.sql;\n")
master_sql.append("SOURCE 04_mutation_bridge_tables.sql;\n")

if INCLUDE_CNA:
    for filename in cna_files:
        master_sql.append(f"SOURCE {filename};\n")

if INCLUDE_MRNA:
    for filename in mrna_files:
        master_sql.append(f"SOURCE {filename};\n")

if INCLUDE_RPPA:
    for filename in rppa_files:
        master_sql.append(f"SOURCE {filename};\n")

master_sql.append("SOURCE 99_validation_counts.sql;\n")

write_sql_file("00_master_load_all.sql", master_sql)


# ============================================================
# 15. VALIDATION SQL FILE
# ============================================================

validation_sql = []
validation_sql.append("-- ============================================================\n")
validation_sql.append("-- VALIDATION ROW COUNTS\n")
validation_sql.append("-- ============================================================\n\n")

validation_sql.append("""
SELECT 'CANCER_TYPE' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM CANCER_TYPE
UNION ALL
SELECT 'COPY_NUMBER_ALTERATION', COUNT(*) FROM COPY_NUMBER_ALTERATION
UNION ALL
SELECT 'GENE', COUNT(*) FROM GENE
UNION ALL
SELECT 'GENOMIC_VARIANT', COUNT(*) FROM GENOMIC_VARIANT
UNION ALL
SELECT 'MRNA_EXPRESSION', COUNT(*) FROM MRNA_EXPRESSION
UNION ALL
SELECT 'PATIENT', COUNT(*) FROM PATIENT
UNION ALL
SELECT 'PATIENT_CLINICAL', COUNT(*) FROM PATIENT_CLINICAL
UNION ALL
SELECT 'PATIENT_DEMOGRAPHIC', COUNT(*) FROM PATIENT_DEMOGRAPHIC
UNION ALL
SELECT 'PATIENT_SMOKING_HISTORY', COUNT(*) FROM PATIENT_SMOKING_HISTORY
UNION ALL
SELECT 'PATIENT_SURVIVAL', COUNT(*) FROM PATIENT_SURVIVAL
UNION ALL
SELECT 'PROTEIN_EXPRESSION', COUNT(*) FROM PROTEIN_EXPRESSION
UNION ALL
SELECT 'SAMPLE', COUNT(*) FROM SAMPLE
UNION ALL
SELECT 'SAMPLE_METRIC', COUNT(*) FROM SAMPLE_METRIC
UNION ALL
SELECT 'SAMPLE_MUTATION', COUNT(*) FROM SAMPLE_MUTATION
UNION ALL
SELECT 'SAMPLE_STAGE', COUNT(*) FROM SAMPLE_STAGE
UNION ALL
SELECT 'VARIANT_ANNOTATION', COUNT(*) FROM VARIANT_ANNOTATION;
""")

write_sql_file("99_validation_counts.sql", validation_sql)


# ============================================================
# 16. README LOAD ORDER FILE
# ============================================================

readme_text = f"""
LUAD SQL Load Files
===================

Database:
{DATABASE_NAME}

Input folder:
{INPUT_DIR}

Output folder:
{OUTPUT_DIR}

Recommended load order in phpMyAdmin:

1. 01_patient_tables.sql
2. 02_sample_tables.sql
3. 03_gene_variant_tables.sql
4. 04_mutation_bridge_tables.sql

Then load large tables one part at a time:

CNA:
{chr(10).join(cna_files)}

mRNA:
{chr(10).join(mrna_files)}

RPPA / Protein:
{chr(10).join(rppa_files)}

Finally:
99_validation_counts.sql

Optional clean restart for large tables:
00_clean_restart_large_tables.sql

Notes:
- Every SQL file begins with USE {DATABASE_NAME};
- GENOMIC_VARIANT.VARIANT_HASH is not inserted manually because it is a generated column.
- CNA, mRNA, and RPPA are split into {NUM_LARGE_PARTS} parts each.
- INSERT IGNORE is used, so rerunning a part is safer if the table has proper unique constraints.
"""

readme_path = OUTPUT_DIR / "README_LOAD_ORDER.txt"
readme_path.write_text(readme_text, encoding="utf-8")
print(f"Created: {readme_path}")


# ============================================================
# 17. SUMMARY
# ============================================================

print("\n============================================================")
print("SQL GENERATION COMPLETE")
print("============================================================")
print(f"Input folder:  {INPUT_DIR}")
print(f"Output folder: {OUTPUT_DIR}")
print(f"Database:      {DATABASE_NAME}")
print("============================================================")
print("Generated files:")

for file in sorted(OUTPUT_DIR.glob("*")):
    if file.is_file():
        size_mb = file.stat().st_size / (1024 * 1024)
        print(f"  {file.name} ({size_mb:.2f} MB)")

print("============================================================")
print("Recommended upload order:")
print("1. 01_patient_tables.sql")
print("2. 02_sample_tables.sql")
print("3. 03_gene_variant_tables.sql")
print("4. 04_mutation_bridge_tables.sql")

print("\n5. CNA split files:")
for filename in cna_files:
    print(f"   {filename}")

print("\n6. mRNA split files:")
for filename in mrna_files:
    print(f"   {filename}")

print("\n7. RPPA split files:")
for filename in rppa_files:
    print(f"   {filename}")

print("\n8. 99_validation_counts.sql")

print("============================================================")
print("If a large file times out:")
print("1. Run SHOW PROCESSLIST;")
print("2. Kill the stuck process if needed.")
print("3. Rerun only the failed part.")
print("============================================================")