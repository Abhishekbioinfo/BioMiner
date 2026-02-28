# BioMiner: Deep-Learning PubMed Biomarker Extractor
BioMiner is an automated bioinformatics pipeline designed to extract structured genomic biomarker data from PubMed literature. Utilizing PubMedBERT (a transformer model pre-trained on biomedical text) and SciSpacy, the tool identifies gene-variant-drug interactions and scores their clinical relevance.

## 🧬 Project Context
This tool was developed to support the identification of IHC-feasible biomarkers and actionable genomic variants for Indian Colorectal Cancer (CRC) and Prostate Cancer cohorts. By mining the global knowledgebase, we can cross-reference local patient data against established clinical evidence.

## 🚀 Key Features
* **Deep NLP Extraction:** Uses PubMedBERT for high-accuracy semantic classification of drug-response relationships.

* **Traceable Evidence:** Every extracted variant is linked back to its source PubMed ID (PMID) and the specific sentence of evidence.

* **Hybrid GPU Support:** Optimized to run on dedicated NVIDIA GPUs (e.g., RTX 3050) using CUDA.

* **Relational Database:** Stores data in a structured PostgreSQL schema, allowing for complex SQL queries across nearly 50,000 evidence points.

## 📂 Repository Structure
* **pipeline.py:** The main orchestrator that manages batch processing and logic flow.

* **pubmed_client.py:** Handles API communication with NCBI and XML parsing.

* **biomarker_extractor.py:** The NLP engine performing Named Entity Recognition (NER) and relationship scoring.

* **db_manager.py:** Manages PostgreSQL connections and the relational "bridge" between articles and biomarkers.

* **gene_dictionary.py:** A helper utility for standardized gene nomenclature.

* **config.py.example:** A template for local environment configuration.

## 🛠️ Installation & Setup
1. Prerequisites
* **Python 3.10+**

* **PostgreSQL 14+**

* **NVIDIA GPU + CUDA Drivers**

2. Environment Setup
```Bash
git clone https://github.com/yourusername/biominer.git
cd biominer
pip install -r requirements.txt
python -m spacy download en_core_web_sm
# Install SciSpacy for biomedical entity recognition
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.1/en_core_sci_sm-0.5.1.tar.gz
```
3. Configuration
Copy the example config and fill in your credentials:

```Bash
cp config.py.example config.py
# Open config.py and add your DB_PASSWORD and NCBI_API_KEY
```

## 📈 Usage
Run the pipeline using your dedicated GPU:

```Bash
python3 pipeline.py

or

CUDA_VISIBLE_DEVICES=0 python3 pipeline.py
```

## 📊 Data Interpretation: Clinical Relevance Score
The pipeline generates a clinical_relevance_score between -1.0 and +1.0:

+0.7 to +1.0: Strong evidence of drug sensitivity.

-0.7 to -1.0: Strong evidence of drug resistance (e.g., KRAS or BRAF mutations in CRC).
