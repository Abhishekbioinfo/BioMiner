import pandas as pd

def analyze_biomarkers(file_path):
    print("Loading 48,000+ extracted biomarkers...\n")
    df = pd.read_csv(file_path)

    # 1. High-Level Summary
    print("=== OVERVIEW ===")
    print(df['cancer_type'].value_counts())
    print("-" * 30)

    # 2. Filter for High-Confidence Drug-Gene Interactions
    # Looking for rows where a drug is mentioned and BERT scored it highly
    actionable_df = df[(df['drug_name'].notna()) & (df['clinical_relevance_score'] > 0)]

    print("\n=== TOP 10 DRUG-GENE TARGETS: COLORECTAL CANCER ===")
    crc_df = actionable_df[actionable_df['cancer_type'] == 'Colorectal']
    crc_top = crc_df.groupby(['gene', 'drug_name']).size().reset_index(name='evidence_count')
    print(crc_top.sort_values(by='evidence_count', ascending=False).head(10).to_string(index=False))

    print("\n=== TOP 10 DRUG-GENE TARGETS: PROSTATE CANCER ===")
    pc_df = actionable_df[actionable_df['cancer_type'] == 'Prostate']
    pc_top = pc_df.groupby(['gene', 'drug_name']).size().reset_index(name='evidence_count')
    print(pc_top.sort_values(by='evidence_count', ascending=False).head(10).to_string(index=False))

    # 3. Find specific variants (e.g., KRAS G12D)
    print("\n=== MOST FREQUENT SPECIFIC MUTATIONS ===")
    variants_df = df[df['variant'].notna()]
    top_variants = variants_df.groupby(['cancer_type', 'gene', 'variant']).size().reset_index(name='mentions')
    print(top_variants.sort_values(by='mentions', ascending=False).head(10).to_string(index=False))

if __name__ == "__main__":
    analyze_biomarkers('biomarkers_only.csv')
