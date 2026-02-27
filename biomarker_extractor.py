import re
import spacy
import torch
from transformers import pipeline
from negspacy.termsets import termset
from negspacy.negation import Negex
from gene_dictionary import load_gene_symbols
from config import TRANSFORMER_MODEL  # Assumes 'microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract' is defined here

# ---------------------------------------------------
# Dictionaries & Lexicons
# ---------------------------------------------------
GENE_SYMBOLS_SET = load_gene_symbols()
GENE_SYMBOLS_LOWER = {g.lower(): g for g in GENE_SYMBOLS_SET}

# The Blacklist: Prevents common English words from being tagged as genes
BLACKLIST_GENES = {"was", "impact", "set", "met", "all", "large", "type", "cell"}

# Combined list of Prostate and Colorectal Cancer therapies
TARGET_DRUGS = [
    # Prostate Cancer Specific
    "docetaxel", "enzalutamide", "abiraterone", "cabazitaxel", "bicalutamide", 
    "flutamide", "mitoxantrone", "apalutamide", "darolutamide", "leuprolide", 
    "degarelix", "goserelin", "triptorelin", "ketoconazole", "radium-223", 
    "sipuleucel-t", "lutetium", "pluvicto", "adt", "androgen deprivation therapy", 
    "antiandrogen", "castration", "androgen receptor pathway inhibitor", "arpi",
    
    # Colorectal Cancer Specific
    "fluorouracil", "5-fu", "capecitabine", "oxaliplatin", "irinotecan", 
    "bevacizumab", "cetuximab", "panitumumab", "regorafenib", "trifluridine", 
    "tipiracil", "folfox", "folfiri", "xelox", "capox", "folfirinox", 
    "vegf inhibitor", "egfr inhibitor",

    # Shared / General Targeted / Immunotherapy
    "olaparib", "rucaparib", "niraparib", "talazoparib", "pembrolizumab",
    "chemotherapy", "radiotherapy", "radiation", "taxane", "parp inhibitor", 
    "parpi", "platinum", "cisplatin", "carboplatin"
]

# ---------------------------------------------------
# NLP Pipeline Initialization (SciSpacy + PubMedBERT)
# ---------------------------------------------------
# 1. Spacy for Entity and Negation Extraction
try:
    nlp = spacy.load("en_core_sci_sm")
except OSError:
    nlp = spacy.load("en_core_web_sm")

ts = termset("en_clinical")
ts.add_patterns({
    "preceding_negations": [
        "not associated", "no association", "not significant", 
        "did not correlate", "no effect", "lack of association"
    ]
})

if "negex" not in nlp.pipe_names:
    nlp.add_pipe("negex", config={"ent_types": ["GENE", "ENTITY"], "neg_termset": ts.get_patterns()})

# 2. Hugging Face PubMedBERT for Semantic Classification
print("Loading PubMedBERT model... this may take a moment.")
try:
    classifier = pipeline(
        "zero-shot-classification",
        model=TRANSFORMER_MODEL,
        # Explicitly declare "cuda:0" to force the NVIDIA card
        device="cuda:0" if torch.cuda.is_available() else "cpu"
    )
    print("PubMedBERT loaded successfully.")
except Exception as e:
    print(f"Loading PubMedBERT failed: {e}. Falling back to keyword logic.")
    classifier = None

# ---------------------------------------------------
# Regex Patterns
# ---------------------------------------------------
HR_PATTERN = r'hazard ratio\s*[:=]?\s*([\d\.]+)'
OR_PATTERN = r'odds ratio\s*[:=]?\s*([\d\.]+)'
CI_PATTERN = r'CI\s*[:=]?\s*([\d\.]+)[–\-\s]+([\d\.]+)'
P_PATTERN = r'p\s*[<>=]\s*([0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)'
VARIANT_PATTERN = r'\b(?:rs\d+|[A-Z]\d{1,5}[A-Z]|c\.\d+[A-Za-z>+_-]+|p\.[A-Z][a-z]{2}\d+[A-Z][a-z]{2})\b'
RESPONSE_PATTERN = r'\b(resistanc[ea]|resistant|sensitiv[ei]|sensiti[vz]ed|toxic|toxicity|adverse effect|efficac[iy]|response|responder|refractory|relapse)\b'

# ---------------------------------------------------
# Advanced Classification & Scoring
# ---------------------------------------------------
def classify_section_with_bert(sentence):
    """Uses PubMedBERT to determine if a sentence is a clinical result."""
    if not classifier:
        s_low = sentence.lower()
        if any(x in s_low for x in ["we found", "results showed", "associated with"]):
            return "RESULT"
        return "UNKNOWN"

    candidate_labels = ["clinical result", "background information", "methodology"]
    result = classifier(sentence, candidate_labels)
    top_label = result['labels'][0]
    
    if top_label == "clinical result":
        return "RESULT"
    elif top_label == "background information":
        return "BACKGROUND"
    return "UNKNOWN"

def compute_clinical_score(entry, is_negated, section_label):
    score = 0
    if is_negated: return -2
    
    # Semantic boost: BERT confirms this is an actual finding
    if section_label == "RESULT": score += 1
    
    # Statistical and Pharmacological boosts
    if entry["p_value"] and entry["p_value"] < 0.05: score += 2
    if entry["drug_response"]: score += 2
    
    return score

# ---------------------------------------------------
# Main Extraction Function
# ---------------------------------------------------
# Added cancer_type parameter to tag the data properly
def extract_biomarkers(text, cancer_type="Unknown"):
    if not text:
        return []

    # 1. ABSTRACT-LEVEL CONTEXT: Scan the whole paper for therapies first
    abstract_lower = text.lower()
    abstract_drugs = []
    for drug in TARGET_DRUGS:
        if re.search(rf'\b{re.escape(drug)}\b', abstract_lower):
            abstract_drugs.append(drug)
    abstract_drug_str = ", ".join(abstract_drugs) if abstract_drugs else None

    doc = nlp(text)
    results = []
    seen_pairs = set()

    for sent in doc.sents:
        sentence_text = sent.text
        sentence_lower = sentence_text.lower()
        
        found_genes = []
        is_negated = any(ent._.negex for ent in sent.ents)

        # 2. Identify Genes (with Blacklist filter)
        for token in sent:
            word_lower = token.text.lower()
            if len(word_lower) >= 3 and word_lower in GENE_SYMBOLS_LOWER and word_lower not in BLACKLIST_GENES:
                found_genes.append(GENE_SYMBOLS_LOWER[word_lower])

        found_genes = list(dict.fromkeys(found_genes))
        if not found_genes:
            continue

        # 3. Extract Variants
        variant_matches = re.findall(VARIANT_PATTERN, sentence_text)
        valid_variants = [v for v in variant_matches if not (len(v) <= 4 and v.isalpha())]
        variant_str = ", ".join(set(valid_variants)) if valid_variants else None

        # 4. Extract Drugs (Sentence fallback to Abstract context)
        sentence_drugs = []
        for drug in TARGET_DRUGS:
            if re.search(rf'\b{re.escape(drug)}\b', sentence_lower):
                sentence_drugs.append(drug)
        
        drug_str = ", ".join(sentence_drugs) if sentence_drugs else abstract_drug_str
        
        response_match = re.search(RESPONSE_PATTERN, sentence_lower)
        drug_response_str = response_match.group(1) if response_match and drug_str else None

        # 5. Extract Statistics
        hr_match = re.search(HR_PATTERN, sentence_lower)
        or_match = re.search(OR_PATTERN, sentence_lower)
        ci_match = re.search(CI_PATTERN, sentence_text)
        p_match = re.search(P_PATTERN, sentence_lower)

        # 6. Classify semantics using BERT
        section_label = classify_section_with_bert(sentence_text)

        # 7. Build Entries
        for gene in found_genes:
            pair_key = (gene, sentence_text)
            if pair_key in seen_pairs: continue
            seen_pairs.add(pair_key)

            entry = {
                "gene": gene,
                "variant": variant_str,
                "cancer_type": cancer_type,            # <-- NEW ADDITION
                "drug_name": drug_str,                 
                "drug_response": drug_response_str,    
                "sentence": sentence_text,
                "hr_value": float(hr_match.group(1)) if hr_match else None,
                "or_value": float(or_match.group(1)) if or_match else None,
                "ci_lower": float(ci_match.group(1)) if ci_match else None,
                "ci_upper": float(ci_match.group(2)) if ci_match else None,
                "p_value": float(p_match.group(1)) if p_match else None,
                "section_label": section_label
            }
            entry["clinical_relevance_score"] = compute_clinical_score(entry, is_negated, section_label)
            results.append(entry)

    return results
