# PHI-base v5.3 JSON Data Structure

Practical reference for `phiexplorer/dereference/chain.py`. For the formal schema,
see `phi-base.schema.json` in the data folder (see
[content-links/data-index.md](../content-links/data-index.md)).

Ported and updated from James Seager's `DATA_STRUCTURE_GUIDE.md`
(`PHI5-zenodo-datamining`) — see [PORTING-NOTES.md](PORTING-NOTES.md).

## Top-level structure

```json
{
  "curation_sessions": { "...": "..." },
  "schema_version": 1
}
```

`publications` is **not** top-level in v5.3 — it's nested under each session
(`session["publications"]`), keyed by PMID.

## Curation session structure

Each session (hex key, e.g. `"ae5f4ed044163d0c"`) contains:

```json
{
  "genes": {},
  "alleles": {},
  "genotypes": {},
  "metagenotypes": {},
  "annotations": [],
  "organisms": {},
  "metadata": {},
  "publications": {}
}
```

**Gotcha:** the formal schema documents `annotations` as an object keyed by
annotation ID, but the actual v5.3 export — and every validated script that reads
it — treats it as a **list** of annotation objects. `phiexplorer` follows the
validated (list) behaviour.

## The dereferencing chain

```
Gene -> Allele -> Genotype -> Metagenotype -> Annotation
```

Implemented in `phiexplorer/dereference/chain.py`:

| Step | Function | Returns |
|---|---|---|
| Sessions containing an organism | `sessions_with_organism(export, sciname)` | iterator of session dicts |
| Genes for an organism | `genes_for_organism(session, sciname)` | `{uniprot_id: gene_dict}` |
| Allele -> gene | `allele_to_gene_map(session, sciname)` | `{allele_id: uniprot_id}` |
| Genotype -> genes | `genotype_to_genes_map(session, taxid, allele_to_gene)` | `{genotype_id: {uniprot_id, ...}}` |
| Metagenotype -> genes | `metagenotype_to_genes_map(session, genotype_to_genes)` | `{metagenotype_id: {uniprot_id, ...}}` |
| Annotation -> genes | `resolve_annotation_gene_ids(annotation, metagenotype_to_genes, genotype_to_genes, sciname)` | `{uniprot_id, ...}` |
| Taxon ID -> name | `taxid_to_name_map(session)` | `{taxid: full_name}` |
| Metagenotype -> host | `host_species_for_metagenotype(session, metagenotype, taxid_to_name)` | `str or None` |

An allele reference inside `genotype["loci"][n][m]` carries `id` (references
`alleles`) and `expression` (expression level — this lives on the locus reference,
not the allele object itself).

## Key annotation types

For pathogen-host interaction analysis:

| Type | Purpose |
|---|---|
| `pathogen_host_interaction_phenotype` | High-level phenotype via the `infective_ability` extension |
| `pathogen_phenotype` | PHIPO ontology terms |
| `disease_name` | Disease classifications |
| `biological_process` / `molecular_function` / `cellular_component` | GO terms |

### High-level phenotype extraction

Look for `extension` entries where `relation == "infective_ability"`
(`phiexplorer.extract.phenotypes.INFECTIVE_ABILITY_TERMS`):

```python
{
    "PHIPO:0000004": "unaffected pathogenicity",
    "PHIPO:0000010": "loss of pathogenicity",
    "PHIPO:0000014": "increased virulence",
    "PHIPO:0000015": "reduced virulence",
}
```

### Host and tissue extraction

`infects_organism` and `infects_tissue` extension relations carry `rangeValue`
(ontology ID) and `rangeDisplayName` (label).

## Organism filtering gotchas

- Organism keys in `session["organisms"]` are **strings**; `genotype["organism_taxonid"]`
  is an **int**. `taxid_to_name_map()` normalizes both to int.
- Gene keys are `"{sciname} {uniprot_id}"` (species name, a single space, then the
  UniProt accession) — `allele_to_gene_map()` strips this prefix.

## Undocumented fields

- `alleles[*].description` — mutation details (e.g. `"R699C"`), present on some
  allele types but not in the formal schema.

## Performance notes

- Pre-filter sessions by organism early (`sessions_with_organism`) rather than
  scanning every session's full content.
- The full v5.3 export is 110MB — load it once per process, not per function call.
