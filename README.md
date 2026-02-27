# Prostate Cancer (Indian Population) Clinical Knowledgebase

## Features
- Automated PubMed retrieval
- Retry logic with exponential backoff
- Biomarker extraction (genes, variants, rsIDs)
- Structured JSON + CSV output
- Clinical knowledgebase-ready architecture

## Setup

1. Install dependencies:
   pip install -r requirements.txt

2. Download SciSpacy model:
   pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.1/en_core_sci_lg-0.5.1.tar.gz

3. Set NCBI API key:
   export NCBI_API_KEY="your_key_here"

4. Run pipeline:
   python pipeline.py

Outputs will be saved in /output
Logs will be saved in /logs
