# Design Decisions and Limitations

---

## Design Decisions

**Mutation table decomposition**
Previously, all the mutation data had been included in a single MUTATION table, which was
related to genes through the MUTATION_GENE table. This was resolved in the finalized version
by segregating the mutation data into three different tables: GENOMIC_VARIANT,
VARIANT_ANNOTATION, and SAMPLE_MUTATION. The decision was made based on the
notion that raw variant positions and alleles, biological annotations, and sample mutations
constitute different facts.

**VARIANT_HASH as a generated column**
VARIANT_HASH is a generated technical column used to enforce uniqueness across
chromosome, start position, end position, reference allele, and alternate alleles. This was used
instead of a large unique key over multiple TEXT columns because MySQL can have index
length limitations. The hash does not violate normalization because it is generated from existing
fields and does not introduce new biological information.

**AGE placed in PATIENT_CLINICAL, not PATIENT_DEMOGRAPHIC**
AGE was intentionally moved out of PATIENT_DEMOGRAPHIC because age changes over time
and is better treated as a clinical-context value, such as age at diagnosis or enrollment.

**CANCER_TYPE as a separate lookup table**
Cancer type information can repeat across many samples. Moving ONCOTREE_CODE,
CANCER_TYPE, and CANCER_TYPE_DETAILED into a lookup table avoids repeated values
in the SAMPLE table and removes transitive dependency. This table was added to satisfy 3NF
more clearly.

**Full matrix inclusion for CNA and mRNA**
The CNA and mRNA expression will not be filtered by genes. Even though they will result in a
few million rows upon converting them into the relational model, this situation is accepted since
the aim is to create a good and complete database rather than to reduce rows.

**Large tables split into part files**
CNA, mRNA, and RPPA SQL load files were each split into four part files because phpMyAdmin
has a default execution timeout that causes single large imports to fail. Each part file uses
INSERT IGNORE so that a failed or partial import can be safely rerun without creating
duplicates.

**One-to-one child tables for patient and sample facts**
One-to-one child tables such as PATIENT_DEMOGRAPHIC, PATIENT_CLINICAL,
PATIENT_SURVIVAL, SAMPLE_STAGE, and SAMPLE_METRIC were kept separate because
they represent different categories of facts.

**Surrogate primary keys**
Surrogate primary keys such as PATIENT_ID, SAMPLE_ID, GENE_ID, VARIANT_ID, and
ANNOTATION_ID were used to simplify joins. Natural identifiers such as PATIENT_BARCODE,
SAMPLE_BARCODE, HUGO_SYMBOL, and ONCOTREE_CODE were still protected with unique
constraints.

---

## Limitations

**DFS_STATUS and DFS_MONTHS are missing**
Disease-free survival fields were completely absent in the source data and were excluded.
Survival analysis is limited to overall survival (OS_STATUS, OS_MONTHS).

**228 of 250 mutation columns were excluded**
The mutation source file contains external annotation fields from COSMIC, ExAC, GO,
DrugBank, and UniProt. These were excluded to keep the schema focused on core biological
fields. They could be added in a future extension table if needed.

**TTN appears as a top mutated gene but is likely a false positive**
TTN is one of the largest genes in the human genome and accumulates mutations by chance
rather than because of biological selection. It consistently appears at the top of mutation
frequency lists in cancer genomics and should be interpreted with caution.

**Schema assumes one record per patient per clinical category**
PATIENT_CLINICAL, PATIENT_SURVIVAL, PATIENT_DEMOGRAPHIC, and
PATIENT_SMOKING_HISTORY each have a unique constraint on PATIENT_ID. This is
appropriate for a cross-sectional TCGA-style dataset but would require constraint changes and
date fields if longitudinal follow-up records were needed.

**RPPA covers fewer samples than CNA and mRNA**
The RPPA file contains 181 samples compared to 230 samples in the CNA and mRNA files.
Not all samples have protein expression data. Queries joining PROTEIN_EXPRESSION with
other molecular tables will return fewer rows than equivalent CNA or mRNA joins.

**Full formal 5NF is not claimed**
The mutation model follows 5NF-style decomposition in its separation of raw variant facts,
biological annotations, and sample observations. However, strict 5NF compliance would
require proving all join dependencies and business rules explicitly, which is beyond the scope
of this project.
