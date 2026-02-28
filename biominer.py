import time
import logging
# 1. FIXED IMPORT: parse_articles is now in pubmed_client
from pubmed_client import search_pubmed, fetch_article_details, parse_articles
# 2. FIXED IMPORT: Match the function name used in the loop (extract_biomarkers)
from biomarker_extractor import extract_biomarkers 
from db_manager import get_connection, insert_article, insert_biomarker, get_existing_pmids

# ---------------------------------------------------
# Configuration & Logging
# ---------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MAX_RESULTS = 20000  
BATCH_SIZE = 100    

QUERIES = {
    "Prostate": '("Prostate Neoplasms"[Mesh] OR "prostate cancer") AND ("Mutation"[Mesh] OR "Biomarkers, Tumor"[Mesh] OR "Polymorphism, Genetic"[Mesh])',
    "Colorectal": '("Colorectal Neoplasms"[Mesh] OR "colorectal cancer") AND ("Mutation"[Mesh] OR "Biomarkers, Tumor"[Mesh] OR "Polymorphism, Genetic"[Mesh])'
}

# ---------------------------------------------------
# Main Pipeline Function
# ---------------------------------------------------
def process_cancer_type(cancer_type, query, conn, existing_pmids):
    logging.info(f"========== Starting extraction for: {cancer_type} Cancer ==========")
    
    all_found_pmids = search_pubmed(query, MAX_RESULTS)
    logging.info(f"Total PMIDs found on PubMed for {cancer_type}: {len(all_found_pmids)}")
    
    if not all_found_pmids:
        return existing_pmids

    new_pmids = [pmid for pmid in all_found_pmids if pmid not in existing_pmids]
    logging.info(f"New PMIDs to process: {len(new_pmids)}")

    if not new_pmids:
        return existing_pmids

    for i in range(0, len(new_pmids), BATCH_SIZE):
        batch_pmids = new_pmids[i:i + BATCH_SIZE]
        logging.info(f"Processing batch {i // BATCH_SIZE + 1}...")

        try:
            records = fetch_article_details(batch_pmids)
            articles = parse_articles(records)
            
            for article in articles:
                # 3. FIXED KEYS: Use Uppercase to match pubmed_client.py
                pmid = article.get('PMID')
                title = article.get('Title', 'No Title')
                abstract = article.get('Abstract', '')
                
                if not pmid:
                    continue
                
                # Save Article Metadata
                insert_article(conn, pmid, title, abstract, None)
                
                # 4. FIXED FUNCTION NAME: Using extract_biomarkers as imported
                full_text = f"{title}. {abstract}"
                extracted_data = extract_biomarkers(full_text)
                
                for entry in extracted_data:
                    entry['cancer_type'] = cancer_type
                    entry['pmid'] = pmid  
                    insert_biomarker(conn, entry)
            
            conn.commit()
            # Update existing_pmids set to prevent reprocessing in the same run
            existing_pmids.update(batch_pmids) 

        except Exception as e:
            logging.error(f"Error processing batch: {e}")
            conn.rollback() 

        time.sleep(1)

    return existing_pmids

def run_pipeline():
    logging.info("Starting Dual-Cancer Pipeline...")
    conn = get_connection()
    if not conn:
        return

    try:
        existing_pmids = get_existing_pmids(conn)
        for cancer_type, query in QUERIES.items():
            existing_pmids = process_cancer_type(cancer_type, query, conn, existing_pmids)
    finally:
        conn.close()
        logging.info("Pipeline complete.")

if __name__ == "__main__":
    run_pipeline()
