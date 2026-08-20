"""Gene -> Allele -> Genotype -> Metagenotype -> Annotation dereferencing chain.

Ported and generalized from James Seager's PHI5-zenodo-datamining scripts
(fg_protein_phenotypes.py, fg_effector_proteins.py) - see docs/PORTING-NOTES.md.
Organism is a parameter throughout, not a hardcoded taxon ID/name.
"""
from __future__ import annotations


def sessions_with_organism(export: dict, sciname: str):
    """Yield curation sessions that include `sciname` among their organisms."""
    for session in export.get("curation_sessions", {}).values():
        organisms = session.get("organisms", {})
        if any(org.get("full_name") == sciname for org in organisms.values()):
            yield session


def genes_for_organism(session: dict, sciname: str) -> dict[str, dict]:
    """Return {uniprot_id: gene_dict} for genes of `sciname` in this session."""
    genes = {}
    for gene in session.get("genes", {}).values():
        if gene.get("organism") != sciname:
            continue
        uid = gene.get("uniquename")
        if uid:
            genes[uid] = gene
    return genes


def allele_to_gene_map(session: dict, sciname: str) -> dict[str, str]:
    """Return {allele_id: uniprot_id} for alleles of genes belonging to `sciname`."""
    prefix = f"{sciname} "
    mapping = {}
    for allele_id, allele in session.get("alleles", {}).items():
        gene_key = allele.get("gene", "")
        if not gene_key.startswith(prefix):
            continue
        mapping[allele_id] = gene_key[len(prefix):]
    return mapping


def genotype_to_genes_map(
    session: dict, taxid: int, allele_to_gene: dict[str, str]
) -> dict[str, set[str]]:
    """Return {genotype_id: {uniprot_id, ...}} for genotypes of `taxid`."""
    mapping: dict[str, set[str]] = {}
    for geno_id, geno in session.get("genotypes", {}).items():
        if geno.get("organism_taxonid") != taxid:
            continue
        uids = set()
        for locus in geno.get("loci", []):
            for locus_allele in locus:
                allele_id = locus_allele.get("id")
                if allele_id in allele_to_gene:
                    uids.add(allele_to_gene[allele_id])
        if uids:
            mapping[geno_id] = uids
    return mapping


def metagenotype_to_genes_map(
    session: dict, genotype_to_genes: dict[str, set[str]]
) -> dict[str, set[str]]:
    """Return {metagenotype_id: {uniprot_id, ...}} via pathogen_genotype linkage."""
    mapping = {}
    for mg_id, mg in session.get("metagenotypes", {}).items():
        uids = genotype_to_genes.get(mg.get("pathogen_genotype"), set())
        if uids:
            mapping[mg_id] = uids
    return mapping


def taxid_to_name_map(session: dict) -> dict[int, str]:
    """Return {taxid: full_name} for all organisms in this session."""
    return {
        int(taxid): org["full_name"]
        for taxid, org in session.get("organisms", {}).items()
    }


def host_species_for_metagenotype(
    session: dict, metagenotype: dict, taxid_to_name: dict[int, str]
) -> str | None:
    """Resolve the host organism's full_name for a metagenotype."""
    host_genotype_id = metagenotype.get("host_genotype")
    host_genotype = session.get("genotypes", {}).get(host_genotype_id, {})
    host_taxid = host_genotype.get("organism_taxonid")
    return taxid_to_name.get(host_taxid)


def resolve_annotation_gene_ids(
    annotation: dict,
    metagenotype_to_genes: dict[str, set[str]],
    genotype_to_genes: dict[str, set[str]],
    sciname: str,
) -> set[str]:
    """Resolve which uniprot_ids an annotation applies to."""
    if "metagenotype" in annotation:
        return metagenotype_to_genes.get(annotation["metagenotype"], set())
    if "genotype" in annotation:
        return genotype_to_genes.get(annotation["genotype"], set())
    if "gene" in annotation:
        gene_key = annotation["gene"]
        prefix = f"{sciname} "
        if gene_key.startswith(prefix):
            return {gene_key[len(prefix):]}
    return set()


def all_organisms(export: dict) -> dict[int, str]:
    """Return {taxid: full_name} for every organism across all curation sessions."""
    organisms: dict[int, str] = {}
    for session in export.get("curation_sessions", {}).values():
        organisms.update(taxid_to_name_map(session))
    return organisms


def resolve_organism(
    export: dict, taxid: int | None = None, sciname: str | None = None
) -> tuple[int, str]:
    """Resolve a (taxid, sciname) pair from either half, validated against `export`.

    - Both given: validated against all_organisms(); raises ValueError if they
      don't refer to the same organism.
    - Only one given: the other is looked up. sciname matching is case-insensitive
      exact match. Raises ValueError if not found, or if a sciname matches more
      than one taxid.
    - Neither given: raises ValueError.
    """
    if taxid is None and sciname is None:
        raise ValueError("must provide --taxid, --sciname, or both")

    organisms = all_organisms(export)

    if taxid is not None:
        resolved_name = organisms.get(taxid)
        if resolved_name is None:
            raise ValueError(f"no organism with taxid {taxid} found in the loaded export")
        if sciname is not None and resolved_name.lower() != sciname.lower():
            raise ValueError(
                f"taxid {taxid} is '{resolved_name}' in the loaded export, not '{sciname}'"
            )
        return taxid, resolved_name

    matches = [(t, name) for t, name in organisms.items() if name.lower() == sciname.lower()]
    if not matches:
        raise ValueError(f"no organism named '{sciname}' found in the loaded export")
    if len(matches) > 1:
        candidates = ", ".join(f"{t} ({name})" for t, name in matches)
        raise ValueError(f"'{sciname}' matches multiple organisms: {candidates}")
    return matches[0]
