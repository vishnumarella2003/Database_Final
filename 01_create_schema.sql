-- =============================================================================
-- Lung Cancer Database (TCGA LUAD)
-- File:    01_create_schema.sql
-- Purpose: Creates all 16 tables in dependency order (no FK violations)
-- Engine:  MySQL 8.0+  |  Charset: utf8mb4
-- Run order: This file must be executed BEFORE 02_load_cleaned_data.sql
-- =============================================================================

CREATE DATABASE IF NOT EXISTS lung_cancer_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE lung_cancer_db;

-- Disable FK checks during setup to allow flexible table creation ordering
SET FOREIGN_KEY_CHECKS = 0;


-- =============================================================================
-- TIER 1: Independent reference / lookup tables (no foreign keys)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. CANCER_TYPE
--    Lookup table for cancer type information. Separated from SAMPLE to
--    remove transitive dependency and satisfy 3NF.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS CANCER_TYPE (
    CANCER_TYPE_ID      INT             NOT NULL AUTO_INCREMENT,
    ONCOTREE_CODE       VARCHAR(50)     NOT NULL,
    CANCER_TYPE         VARCHAR(100)    NOT NULL,
    CANCER_TYPE_DETAILED VARCHAR(255)   DEFAULT NULL,

    CONSTRAINT pk_cancer_type PRIMARY KEY (CANCER_TYPE_ID),
    CONSTRAINT uq_oncotree_code UNIQUE (ONCOTREE_CODE)
);


-- -----------------------------------------------------------------------------
-- 2. PATIENT
--    Central patient table. One row per patient. All other patient-level
--    tables reference this via PATIENT_ID.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS PATIENT (
    PATIENT_ID          INT             NOT NULL AUTO_INCREMENT,
    PATIENT_BARCODE     VARCHAR(50)     NOT NULL,

    CONSTRAINT pk_patient PRIMARY KEY (PATIENT_ID),
    CONSTRAINT uq_patient_barcode UNIQUE (PATIENT_BARCODE)
);


-- -----------------------------------------------------------------------------
-- 3. GENE
--    Central gene reference table. Genes appear in mutation, CNA, mRNA,
--    and RPPA datasets. Stored once here and reused via foreign keys.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS GENE (
    GENE_ID             INT             NOT NULL AUTO_INCREMENT,
    HUGO_SYMBOL         VARCHAR(100)    NOT NULL,
    ENTREZ_GENE_ID      INT             DEFAULT NULL,

    CONSTRAINT pk_gene PRIMARY KEY (GENE_ID),
    CONSTRAINT uq_hugo_symbol UNIQUE (HUGO_SYMBOL)
);


-- -----------------------------------------------------------------------------
-- 4. GENOMIC_VARIANT
--    Stores raw genomic variant position and allele information only.
--    Biological annotations are stored separately in VARIANT_ANNOTATION
--    because one raw variant can have multiple annotations.
--    VARIANT_HASH enforces uniqueness across multi-column TEXT key
--    (SHA2 hash of chr + start + end + ref + alt1 + alt2).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS GENOMIC_VARIANT (
    VARIANT_ID          BIGINT          NOT NULL AUTO_INCREMENT,
    CHROMOSOME          VARCHAR(50)     NOT NULL,
    START_POSITION      BIGINT          NOT NULL,
    END_POSITION        BIGINT          NOT NULL,
    REFERENCE_ALLELE    TEXT            NOT NULL,
    TUMOR_SEQ_ALLELE1   TEXT            DEFAULT NULL,
    TUMOR_SEQ_ALLELE2   TEXT            DEFAULT NULL,
    VARIANT_HASH        CHAR(64)        NOT NULL,    -- SHA2-256 of position+allele fields

    CONSTRAINT pk_genomic_variant PRIMARY KEY (VARIANT_ID),
    CONSTRAINT uq_variant_hash UNIQUE (VARIANT_HASH)
);


-- =============================================================================
-- TIER 2: Tables that depend only on Tier 1 tables
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 5. SAMPLE
--    One row per tumor sample. Links each sample to its patient and cancer type.
--    Molecular datasets (mutation, CNA, mRNA, RPPA) all reference SAMPLE_ID.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SAMPLE (
    SAMPLE_ID           INT             NOT NULL AUTO_INCREMENT,
    SAMPLE_BARCODE      VARCHAR(80)     NOT NULL,
    PATIENT_ID          INT             NOT NULL,
    CANCER_TYPE_ID      INT             NOT NULL,
    SOMATIC_STATUS      VARCHAR(100)    DEFAULT NULL,

    CONSTRAINT pk_sample PRIMARY KEY (SAMPLE_ID),
    CONSTRAINT uq_sample_barcode UNIQUE (SAMPLE_BARCODE),
    CONSTRAINT fk_sample_patient
        FOREIGN KEY (PATIENT_ID)        REFERENCES PATIENT (PATIENT_ID)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_sample_cancer_type
        FOREIGN KEY (CANCER_TYPE_ID)    REFERENCES CANCER_TYPE (CANCER_TYPE_ID)
        ON DELETE RESTRICT ON UPDATE CASCADE
);


-- -----------------------------------------------------------------------------
-- 6. PATIENT_DEMOGRAPHIC
--    Static demographic attributes for each patient (sex).
--    AGE is intentionally excluded here — it is time-contextual and lives in
--    PATIENT_CLINICAL (age at diagnosis/enrollment).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS PATIENT_DEMOGRAPHIC (
    DEMOGRAPHIC_ID      INT             NOT NULL AUTO_INCREMENT,
    PATIENT_ID          INT             NOT NULL,
    SEX                 VARCHAR(20)     DEFAULT NULL,

    CONSTRAINT pk_patient_demographic PRIMARY KEY (DEMOGRAPHIC_ID),
    CONSTRAINT uq_demographic_patient UNIQUE (PATIENT_ID),    -- one record per patient
    CONSTRAINT fk_demographic_patient
        FOREIGN KEY (PATIENT_ID)        REFERENCES PATIENT (PATIENT_ID)
        ON DELETE CASCADE ON UPDATE CASCADE
);


-- -----------------------------------------------------------------------------
-- 7. PATIENT_CLINICAL
--    Cancer diagnosis and clinical background per patient.
--    AGE is stored here because it represents age at diagnosis/enrollment,
--    making it time-contextual rather than a static demographic attribute.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS PATIENT_CLINICAL (
    CLINICAL_ID                         INT             NOT NULL AUTO_INCREMENT,
    PATIENT_ID                          INT             NOT NULL,
    AGE                                 INT             DEFAULT NULL,
    HISTOLOGICAL_SUBTYPE                VARCHAR(255)    DEFAULT NULL,
    PRETREATMENT_HISTORY                VARCHAR(255)    DEFAULT NULL,
    PRIMARY_TUMOR_PATHOLOGIC_SPREAD     VARCHAR(255)    DEFAULT NULL,
    PRIOR_DIAGNOSIS                     VARCHAR(255)    DEFAULT NULL,
    RESIDUAL_TUMOR                      VARCHAR(255)    DEFAULT NULL,

    CONSTRAINT pk_patient_clinical PRIMARY KEY (CLINICAL_ID),
    CONSTRAINT uq_clinical_patient UNIQUE (PATIENT_ID),    -- one record per patient
    CONSTRAINT fk_clinical_patient
        FOREIGN KEY (PATIENT_ID)        REFERENCES PATIENT (PATIENT_ID)
        ON DELETE CASCADE ON UPDATE CASCADE
);


-- -----------------------------------------------------------------------------
-- 8. PATIENT_SURVIVAL
--    Overall survival outcome per patient. Stored separately to allow
--    independent survival analysis queries without joining clinical fields.
--    DFS_STATUS and DFS_MONTHS excluded — completely missing in source data.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS PATIENT_SURVIVAL (
    SURVIVAL_ID         INT             NOT NULL AUTO_INCREMENT,
    PATIENT_ID          INT             NOT NULL,
    OS_STATUS           VARCHAR(100)    DEFAULT NULL,
    OS_MONTHS           DECIMAL(10,4)   DEFAULT NULL,

    CONSTRAINT pk_patient_survival PRIMARY KEY (SURVIVAL_ID),
    CONSTRAINT uq_survival_patient UNIQUE (PATIENT_ID),    -- one record per patient
    CONSTRAINT fk_survival_patient
        FOREIGN KEY (PATIENT_ID)        REFERENCES PATIENT (PATIENT_ID)
        ON DELETE CASCADE ON UPDATE CASCADE
);


-- -----------------------------------------------------------------------------
-- 9. PATIENT_SMOKING_HISTORY
--    Tobacco smoking history per patient. Kept in its own table because
--    smoking is a key lung cancer risk factor and may need multiple records
--    per patient in a future longitudinal extension.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS PATIENT_SMOKING_HISTORY (
    SMOKING_ID                          INT             NOT NULL AUTO_INCREMENT,
    PATIENT_ID                          INT             NOT NULL,
    TOBACCO_SMOKING_HISTORY_INDICATOR   VARCHAR(255)    DEFAULT NULL,

    CONSTRAINT pk_smoking_history PRIMARY KEY (SMOKING_ID),
    CONSTRAINT uq_smoking_patient UNIQUE (PATIENT_ID),    -- one record per patient
    CONSTRAINT fk_smoking_patient
        FOREIGN KEY (PATIENT_ID)        REFERENCES PATIENT (PATIENT_ID)
        ON DELETE CASCADE ON UPDATE CASCADE
);


-- =============================================================================
-- TIER 3: Tables that depend on Tier 2 tables
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 10. SAMPLE_STAGE
--     Tumor staging and metastasis information per sample. Separated from
--     SAMPLE to isolate staging facts from core sample identity fields.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SAMPLE_STAGE (
    STAGE_ID                            INT             NOT NULL AUTO_INCREMENT,
    SAMPLE_ID                           INT             NOT NULL,
    TUMOR_STAGE_2009                    VARCHAR(100)    DEFAULT NULL,
    DISTANT_METASTASIS_PATHOLOGIC_SPREAD VARCHAR(255)   DEFAULT NULL,

    CONSTRAINT pk_sample_stage PRIMARY KEY (STAGE_ID),
    CONSTRAINT uq_stage_sample UNIQUE (SAMPLE_ID),    -- one staging record per sample
    CONSTRAINT fk_stage_sample
        FOREIGN KEY (SAMPLE_ID)         REFERENCES SAMPLE (SAMPLE_ID)
        ON DELETE CASCADE ON UPDATE CASCADE
);


-- -----------------------------------------------------------------------------
-- 11. SAMPLE_METRIC
--     Quantitative genomic metrics per sample (tumor mutation burden).
--     Stored separately from staging and identity fields because it represents
--     a different category of sample-level fact.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SAMPLE_METRIC (
    SAMPLE_METRIC_ID    INT             NOT NULL AUTO_INCREMENT,
    SAMPLE_ID           INT             NOT NULL,
    TMB_NONSYNONYMOUS   DECIMAL(18,6)   DEFAULT NULL,

    CONSTRAINT pk_sample_metric PRIMARY KEY (SAMPLE_METRIC_ID),
    CONSTRAINT uq_metric_sample UNIQUE (SAMPLE_ID),    -- one metric record per sample
    CONSTRAINT fk_metric_sample
        FOREIGN KEY (SAMPLE_ID)         REFERENCES SAMPLE (SAMPLE_ID)
        ON DELETE CASCADE ON UPDATE CASCADE
);


-- -----------------------------------------------------------------------------
-- 12. VARIANT_ANNOTATION
--     Biological annotation and interpretation of genomic variants.
--     One raw variant can have multiple annotations (different transcripts
--     or genes), so annotation is stored separately from the raw variant.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS VARIANT_ANNOTATION (
    ANNOTATION_ID           BIGINT          NOT NULL AUTO_INCREMENT,
    VARIANT_ID              BIGINT          NOT NULL,
    GENE_ID                 INT             NOT NULL,
    VARIANT_CLASSIFICATION  VARCHAR(150)    DEFAULT NULL,
    VARIANT_TYPE            VARCHAR(100)    DEFAULT NULL,
    CONSEQUENCE             VARCHAR(255)    DEFAULT NULL,
    IMPACT                  VARCHAR(100)    DEFAULT NULL,
    HGVSC                   TEXT            DEFAULT NULL,
    HGVSP                   TEXT            DEFAULT NULL,
    HGVSP_SHORT             VARCHAR(255)    DEFAULT NULL,
    TRANSCRIPT_ID           VARCHAR(255)    DEFAULT NULL,
    PROTEIN_POSITION        VARCHAR(100)    DEFAULT NULL,
    CODONS                  TEXT            DEFAULT NULL,
    HOTSPOT                 VARCHAR(50)     DEFAULT NULL,

    CONSTRAINT pk_variant_annotation PRIMARY KEY (ANNOTATION_ID),
    CONSTRAINT fk_annotation_variant
        FOREIGN KEY (VARIANT_ID)        REFERENCES GENOMIC_VARIANT (VARIANT_ID)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_annotation_gene
        FOREIGN KEY (GENE_ID)           REFERENCES GENE (GENE_ID)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    INDEX idx_annotation_variant (VARIANT_ID),
    INDEX idx_annotation_gene (GENE_ID),
    INDEX idx_annotation_impact (IMPACT),
    INDEX idx_annotation_classification (VARIANT_CLASSIFICATION)
);


-- -----------------------------------------------------------------------------
-- 13. SAMPLE_MUTATION
--     Bridge table connecting samples to genomic variants (many-to-many).
--     T_REF_COUNT and T_ALT_COUNT are sample-specific observations — the same
--     variant in a different sample will have different read counts.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SAMPLE_MUTATION (
    SAMPLE_MUTATION_ID  BIGINT          NOT NULL AUTO_INCREMENT,
    SAMPLE_ID           INT             NOT NULL,
    VARIANT_ID          BIGINT          NOT NULL,
    T_REF_COUNT         INT             DEFAULT NULL,
    T_ALT_COUNT         INT             DEFAULT NULL,

    CONSTRAINT pk_sample_mutation PRIMARY KEY (SAMPLE_MUTATION_ID),
    CONSTRAINT uq_sample_variant UNIQUE (SAMPLE_ID, VARIANT_ID),
    CONSTRAINT fk_mutation_sample
        FOREIGN KEY (SAMPLE_ID)         REFERENCES SAMPLE (SAMPLE_ID)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_mutation_variant
        FOREIGN KEY (VARIANT_ID)        REFERENCES GENOMIC_VARIANT (VARIANT_ID)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    INDEX idx_mutation_sample (SAMPLE_ID),
    INDEX idx_mutation_variant (VARIANT_ID)
);


-- -----------------------------------------------------------------------------
-- 14. COPY_NUMBER_ALTERATION
--     CNA value for every gene-sample pair (full matrix, long format).
--     CNA_VALUE depends on the combination of sample AND gene, not either alone.
--     tinyint used for CNA values (-2, -1, 0, 1, 2).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS COPY_NUMBER_ALTERATION (
    CNA_ID              BIGINT          NOT NULL AUTO_INCREMENT,
    SAMPLE_ID           INT             NOT NULL,
    GENE_ID             INT             NOT NULL,
    CNA_VALUE           TINYINT         DEFAULT NULL,

    CONSTRAINT pk_cna PRIMARY KEY (CNA_ID),
    CONSTRAINT uq_cna_sample_gene UNIQUE (SAMPLE_ID, GENE_ID),
    CONSTRAINT fk_cna_sample
        FOREIGN KEY (SAMPLE_ID)         REFERENCES SAMPLE (SAMPLE_ID)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_cna_gene
        FOREIGN KEY (GENE_ID)           REFERENCES GENE (GENE_ID)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    INDEX idx_cna_sample (SAMPLE_ID),
    INDEX idx_cna_gene (GENE_ID)
);


-- -----------------------------------------------------------------------------
-- 15. MRNA_EXPRESSION
--     RSEM mRNA expression value for every gene-sample pair (full matrix,
--     long format). ~4.7 million rows after matrix conversion.
--     RSEM_VALUE depends on the combination of sample AND gene.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS MRNA_EXPRESSION (
    MRNA_ID             BIGINT          NOT NULL AUTO_INCREMENT,
    SAMPLE_ID           INT             NOT NULL,
    GENE_ID             INT             NOT NULL,
    RSEM_VALUE          DECIMAL(20,6)   DEFAULT NULL,

    CONSTRAINT pk_mrna PRIMARY KEY (MRNA_ID),
    CONSTRAINT uq_mrna_sample_gene UNIQUE (SAMPLE_ID, GENE_ID),
    CONSTRAINT fk_mrna_sample
        FOREIGN KEY (SAMPLE_ID)         REFERENCES SAMPLE (SAMPLE_ID)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_mrna_gene
        FOREIGN KEY (GENE_ID)           REFERENCES GENE (GENE_ID)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    INDEX idx_mrna_sample (SAMPLE_ID),
    INDEX idx_mrna_gene (GENE_ID)
);


-- -----------------------------------------------------------------------------
-- 16. PROTEIN_EXPRESSION
--     RPPA protein expression value per sample, gene, and antibody marker.
--     Unique constraint on (SAMPLE_ID, GENE_ID, ANTIBODY_REF) because the same
--     gene in the same sample may have multiple measurements for different
--     antibodies/markers.
--     RPPA identifiers parsed from GENE|ANTIBODY format at load time.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS PROTEIN_EXPRESSION (
    PROTEIN_EXPRESSION_ID   BIGINT          NOT NULL AUTO_INCREMENT,
    SAMPLE_ID               INT             NOT NULL,
    GENE_ID                 INT             NOT NULL,
    ANTIBODY_REF            VARCHAR(255)    NOT NULL,
    EXPRESSION_VALUE        DECIMAL(20,6)   DEFAULT NULL,

    CONSTRAINT pk_protein_expression PRIMARY KEY (PROTEIN_EXPRESSION_ID),
    CONSTRAINT uq_protein_sample_gene_antibody UNIQUE (SAMPLE_ID, GENE_ID, ANTIBODY_REF),
    CONSTRAINT fk_protein_sample
        FOREIGN KEY (SAMPLE_ID)         REFERENCES SAMPLE (SAMPLE_ID)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_protein_gene
        FOREIGN KEY (GENE_ID)           REFERENCES GENE (GENE_ID)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    INDEX idx_protein_sample (SAMPLE_ID),
    INDEX idx_protein_gene (GENE_ID)
);


-- =============================================================================
-- Re-enable FK checks
-- =============================================================================
SET FOREIGN_KEY_CHECKS = 1;


-- =============================================================================
-- Verify all 16 tables were created
-- =============================================================================
SELECT
    TABLE_NAME,
    TABLE_ROWS,
    ENGINE,
    TABLE_COLLATION
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'lung_cancer_db'
ORDER BY TABLE_NAME;
