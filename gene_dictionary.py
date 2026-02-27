import csv

def load_gene_symbols(filepath="hgnc_complete_set.txt"):

    gene_set = set()

    with open(filepath, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:

            if (
                row["status"] == "Approved" and
                row["locus_group"] == "protein-coding gene"
            ):
                gene_set.add(row["symbol"])

    return gene_set
