from Bio import Entrez
import time
import logging
from config import EMAIL, REQUEST_DELAY, MAX_RETRIES

# Configure Entrez
Entrez.email = "your_email@example.com"
Entrez.api_key = "your_api_key"

def retry_request(func, *args, **kwargs):
    """Retries a network request with exponential backoff."""
    retries = 0
    backoff = 1

    while retries < MAX_RETRIES:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.warning(f"Error: {e}. Retrying in {backoff}s...")
            time.sleep(backoff)
            retries += 1
            backoff *= 2

    raise Exception("Max retries exceeded")

def search_pubmed(query, retmax):
    """Searches PubMed for PMIDs matching the query."""
    print("Searching PubMed...")
    handle = retry_request(
        Entrez.esearch,
        db="pubmed",
        term=query,
        retmax=retmax
    )
    print("Reading response...")
    record = Entrez.read(handle)
    print("Search completed.")
    time.sleep(REQUEST_DELAY)
    return record["IdList"]

def fetch_article_details(pmid_list):
    """Fetches the full XML records for a batch of PMIDs."""
    if not pmid_list:
        return {"PubmedArticle": []}
        
    try:
        # Fetch the full XML records for the batch of PMIDs
        handle = Entrez.efetch(db="pubmed", id=",".join(pmid_list), retmode="xml")
        records = Entrez.read(handle)
        handle.close()
        return records
    except Exception as e:
        print(f"Error fetching article details: {e}")
        return {"PubmedArticle": []}

def parse_articles(records):
    """Parses raw XML records into a structured list of dictionaries."""
    articles = []
    if not records or "PubmedArticle" not in records:
        return articles

    for article in records["PubmedArticle"]:
        try:
            medline = article["MedlineCitation"]
            article_data = medline["Article"]
            
            # 1. Extract Title
            title = article_data.get("ArticleTitle", "No Title Available")
            
            # 2. Extract and format Abstract (handling structured sections)
            abstract_text_list = []
            if "Abstract" in article_data and "AbstractText" in article_data["Abstract"]:
                abstract_chunks = article_data["Abstract"]["AbstractText"]
                for chunk in abstract_chunks:
                    # Get section labels like BACKGROUND, RESULTS, CONCLUSION
                    label = getattr(chunk, 'attributes', {}).get("Label", "").upper()
                    text = str(chunk)
                    if label:
                        abstract_text_list.append(f"[{label}] {text}")
                    else:
                        abstract_text_list.append(text)
            
            abstract = " ".join(abstract_text_list)
            
            # 3. Extract PMID as a string
            pmid = str(medline["PMID"])

            # Use Uppercase keys to match your current pipeline logic
            articles.append({
                "PMID": pmid,
                "Title": title,
                "Abstract": abstract
            })
        except Exception as e:
            logging.warning(f"Error parsing an individual article: {e}")
            continue
            
    return articles
