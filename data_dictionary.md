# Data Dictionary

All tables use InnoDB storage engine with utf8mb4_unicode_ci collation.  
PK = Primary Key, FK = Foreign Key, UK = Unique Key, NN = Not Null, NULL = Nullable

---

## CANCER_TYPE
Stores cancer type lookup information. Source: `data_clinical_sample.txt`

| Field | Type | Constraints | Definition |
|---|---|---|---|
| CANCER_TYPE_ID | int | PK, NN | Surrogate primary key |
| ONCOTREE_CODE | varchar(50) | NN | OncoTree cancer code |
| CANCER_TYPE | varchar(100) | NN | Broad cancer category |
| CANCER_TYPE_DETAILED | varchar(255) | NN | Detailed cancer type description |

---

## PATIENT
Stores one row per patient. Source: `data_clinical_patient.txt`

| Field | Type | Constraints | Definition |
|---|---|---|---|
| PATIENT_ID | int | PK, NN | Surrogate primary key |
| PATIENT_BARCODE | varchar(50) | UK, NN | TCGA patient barcode |

---

## PATIENT_DEMOGRAPHIC
Stores static patient demographic information. Source: `data_clinical_patient.txt`

| Field | Type | Constraints | Definition |
|---|---|---|---|
| DEMOGRAPHIC_ID | int | PK, NN | Surrogate primary key |
| PATIENT_ID | int | FK → PATIENT, UK, NN | Links to PATIENT table |
| SEX | varchar(20) | NULL | Patient sex |

---

## PATIENT_CLINICAL
Stores general diagnosis and clinical background information. Source: `data_clinical_patient.txt`

| Field | Type | Constraints | Definition |
|---|---|---|---|
| CLINICAL_ID | int | PK, NN | Surrogate primary key |
| PATIENT_ID | int | FK → PATIENT, UK, NN | Links to PATIENT table |
| AGE | int | NULL | Age at diagnosis or enrollment |
| HISTOLOGICAL_SUBTYPE | varchar(255) | NULL | Cancer histological subtype |
| PRETREATMENT_HISTORY | varchar(255) | NULL | Prior treatment before study enrollment |
| PRIMARY_TUMOR_PATHOLOGIC_SPREAD | varchar(255) | NULL | Pathologic spread of the primary tumor |
| PRIOR_DIAGNOSIS | varchar(255) | NULL | Whether the patient had a prior cancer diagnosis |
| RESIDUAL_TUMOR | varchar(255) | NULL | Residual tumor status after treatment |

---

## PATIENT_SURVIVAL
Stores survival outcome information. Source: `data_clinical_patient.txt`

| Field | Type | Constraints | Definition |
|---|---|---|---|
| SURVIVAL_ID | int | PK, NN | Surrogate primary key |
| PATIENT_ID | int | FK → PATIENT, UK, NN | Links to PATIENT table |
| OS_STATUS | varchar(100) | NULL | Overall survival status |
| OS_MONTHS | decimal(10,4) | NULL | Overall survival time in months |

---

## PATIENT_SMOKING_HISTORY
Stores smoking history information. Source: `data_clinical_patient.txt`

| Field | Type | Constraints | Definition |
|---|---|---|---|
| SMOKING_ID | int | PK, NN | Surrogate primary key |
| PATIENT_ID | int | FK → PATIENT, UK, NN | Links to PATIENT table |
| TOBACCO_SMOKING_HISTORY_INDICATOR | varchar(255) | NULL | Coded smoking history category |

---

## SAMPLE
Stores one row per tumor sample. Source: `data_clinical_sample.txt`

| Field | Type | Constraints | Definition |
|---|---|---|---|
| SAMPLE_ID | int | PK, NN | Surrogate primary key |
| SAMPLE_BARCODE | varchar(80) | UK, NN | TCGA sample barcode |
| PATIENT_ID | int | FK → PATIENT, NN | Links to PATIENT table |
| CANCER_TYPE_ID | int | FK → CANCER_TYPE, NN | Links to CANCER_TYPE lookup table |
| SOMATIC_STATUS | varchar(100) | NULL | Somatic mutation status of the sample |

---

## SAMPLE_STAGE
Stores tumor staging and metastasis information. Source: `data_clinical_sample.txt`

| Field | Type | Constraints | Definition |
|---|---|---|---|
| STAGE_ID | int | PK, NN | Surrogate primary key |
| SAMPLE_ID | int | FK → SAMPLE, UK, NN | Links to SAMPLE table |
| TUMOR_STAGE_2009 | varchar(100) | NULL | AJCC 2009 pathologic tumor stage |
| DISTANT_METASTASIS_PATHOLOGIC_SPREAD | varchar(255) | NULL | Pathologic distant metastasis classification |

---

## SAMPLE_METRIC
Stores sample-level quantitative metrics. Source: `data_clinical_sample.txt`

| Field | Type | Constraints | Definition |
|---|---|---|---|
| SAMPLE_METRIC_ID | int | PK, NN | Surrogate primary key |
| SAMPLE_ID | int | FK → SAMPLE, UK, NN | Links to SAMPLE table |
| TMB_NONSYNONYMOUS | decimal(18,6) | NULL | Tumor mutation burden (nonsynonymous mutations per megabase) |

---

## GENE
Stores one row per gene. Source: `data_mutations.txt`, `data_cna.txt`, `data_mrna_seq_v2_rsem.txt`, `data_rppa.txt`

| Field | Type | Constraints | Definition |
|---|---|---|---|
| GENE_ID | int | PK, NN | Surrogate primary key |
| HUGO_SYMBOL | varchar(100) | UK, NN | HUGO gene symbol |
| ENTREZ_GENE_ID | int | NULL | NCBI Entrez gene identifier |

---

## GENOMIC_VARIANT
Stores raw genomic variant position and allele information. Source: `data_mutations.txt`

| Field | Type | Constraints | Definition |
|---|---|---|---|
| VARIANT_ID | bigint | PK, NN | Surrogate primary key |
| CHROMOSOME | varchar(50) | NN | Chromosome where the variant occurs |
| START_POSITION | bigint | NN | Genomic start position of the variant |
| END_POSITION | bigint | NN | Genomic end position of the variant |
| REFERENCE_ALLELE | text | NULL | Reference allele at the variant position |
| TUMOR_SEQ_ALLELE1 | text | NULL | First tumor allele observed |
| TUMOR_SEQ_ALLELE2 | text | NULL | Second tumor allele observed |
| VARIANT_HASH | char(64) | UK, Generated | SHA-256 hash of the six variant coordinate fields used to enforce uniqueness |

---

## VARIANT_ANNOTATION
Stores biological annotation and interpretation of genomic variants. Source: `data_mutations.txt`

| Field | Type | Constraints | Definition |
|---|---|---|---|
| ANNOTATION_ID | bigint | PK, NN | Surrogate primary key |
| VARIANT_ID | bigint | FK → GENOMIC_VARIANT, NN | Links to GENOMIC_VARIANT table |
| GENE_ID | int | FK → GENE, NN | Links to GENE table |
| VARIANT_CLASSIFICATION | varchar(150) | NULL | Mutation class (e.g. Missense_Mutation, Nonsense_Mutation) |
| VARIANT_TYPE | varchar(100) | NULL | Mutation category (e.g. SNP, DEL, INS) |
| CONSEQUENCE | varchar(255) | NULL | Sequence ontology consequence term |
| IMPACT | varchar(100) | NULL | Predicted functional impact (HIGH, MODERATE, LOW, MODIFIER) |
| HGVSC | text | NULL | HGVS coding sequence notation |
| HGVSP | text | NULL | HGVS protein sequence notation |
| HGVSP_SHORT | varchar(255) | NULL | Abbreviated HGVS protein notation |
| TRANSCRIPT_ID | varchar(255) | NULL | Ensembl transcript identifier |
| PROTEIN_POSITION | varchar(100) | NULL | Amino acid position affected |
| CODONS | text | NULL | Reference and alternate codon change |
| HOTSPOT | varchar(50) | NULL | Mutation hotspot flag |

---

## SAMPLE_MUTATION
Connects samples to genomic variants. Source: `data_mutations.txt`

| Field | Type | Constraints | Definition |
|---|---|---|---|
| SAMPLE_MUTATION_ID | bigint | PK, NN | Surrogate primary key |
| SAMPLE_ID | int | FK → SAMPLE, NN | Links to SAMPLE table |
| VARIANT_ID | bigint | FK → GENOMIC_VARIANT, NN | Links to GENOMIC_VARIANT table |
| T_REF_COUNT | int | NULL | Number of reads supporting the reference allele in the tumor |
| T_ALT_COUNT | int | NULL | Number of reads supporting the alternate allele in the tumor |

---

## COPY_NUMBER_ALTERATION
Stores CNA values for every gene-sample pair. Source: `data_cna.txt`

| Field | Type | Constraints | Definition |
|---|---|---|---|
| CNA_ID | bigint | PK, NN | Surrogate primary key |
| SAMPLE_ID | int | FK → SAMPLE, NN | Links to SAMPLE table |
| GENE_ID | int | FK → GENE, NN | Links to GENE table |
| CNA_VALUE | tinyint | NULL | CNA value (2 = amplification, 1 = gain, 0 = neutral, -1 = shallow deletion, -2 = deep deletion) |

---

## MRNA_EXPRESSION
Stores mRNA expression values for every gene-sample pair. Source: `data_mrna_seq_v2_rsem.txt`

| Field | Type | Constraints | Definition |
|---|---|---|---|
| MRNA_ID | bigint | PK, NN | Surrogate primary key |
| SAMPLE_ID | int | FK → SAMPLE, NN | Links to SAMPLE table |
| GENE_ID | int | FK → GENE, NN | Links to GENE table |
| RSEM_VALUE | decimal(20,6) | NULL | RSEM-normalized mRNA expression value |

---

## PROTEIN_EXPRESSION
Stores RPPA protein expression values. Source: `data_rppa.txt`

| Field | Type | Constraints | Definition |
|---|---|---|---|
| PROTEIN_EXPRESSION_ID | bigint | PK, NN | Surrogate primary key |
| SAMPLE_ID | int | FK → SAMPLE, NN | Links to SAMPLE table |
| GENE_ID | int | FK → GENE, NN | Links to GENE table |
| ANTIBODY_REF | varchar(255) | NULL | Antibody or protein marker identifier |
| EXPRESSION_VALUE | decimal(20,6) | NULL | RPPA protein expression value |
