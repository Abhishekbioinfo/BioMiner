import os

# ---------------------------------------------------
# NCBI / PubMed Configuration
# ---------------------------------------------------

EMAIL = "your_email@example.com"

# Optional but recommended (set as environment variable if available)
NCBI_API_KEY = os.getenv("xxxxxvxfkldfjfjhiq8789fjkxxxxx")

# PubMed Query (Prostate Cancer + India + Humans + English)
QUERY = (
    '(("Prostatic Neoplasms"[Mesh] OR "prostate cancer"[Title/Abstract]) '
    'AND ("India"[Affiliation] OR "Indian population"[Title/Abstract])) '
    'AND (Humans[Mesh]) AND (English[lang])'
)

MAX_RESULTS = 400
BATCH_SIZE = 50
REQUEST_DELAY = 0.34   # Respect NCBI rate limits
MAX_RETRIES = 5

# ---------------------------------------------------
# Database Configuration (PostgreSQL)
# ---------------------------------------------------

DB_NAME = "prostate_india_db"
DB_USER = "prostate_user"
DB_PASSWORD = "your_secure_password"
DB_HOST = "localhost"
DB_PORT = 8888

# ---------------------------------------------------
# Transformer Model Configuration
# ---------------------------------------------------

TRANSFORMER_MODEL = "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract"
