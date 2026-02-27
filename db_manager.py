import psycopg2
import psycopg2.extras
from config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

# ---------------------------------------------------
# Database Connection
# ---------------------------------------------------

def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# ---------------------------------------------------
# Insert Article Metadata
# ---------------------------------------------------

def insert_article(conn, pmid, title, abstract, year):
    """Inserts an article into the database, ignoring if it already exists."""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO articles (pmid, title, abstract, year)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (pmid) DO NOTHING;
    """, (pmid, title, abstract, year))
    conn.commit()
    cur.close()

# ---------------------------------------------------
# Insert Biomarker Evidence (Sentence-Level)
# ---------------------------------------------------

def insert_biomarker(conn, entry):
    cur = conn.cursor()

    # 1. Insert the biomarker data
    cur.execute("""
        INSERT INTO biomarkers (
            gene, variant, cancer_type, drug_name, drug_response, 
            sentence, hr_value, or_value, ci_lower, ci_upper, 
            p_value, section_label, clinical_relevance_score
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id;
    """, (
        entry.get("gene"), entry.get("variant"), entry.get("cancer_type"),
        entry.get("drug_name"), entry.get("drug_response"), entry.get("sentence"),
        entry.get("hr_value"), entry.get("or_value"), entry.get("ci_lower"),
        entry.get("ci_upper"), entry.get("p_value"), entry.get("section_label"),
        entry.get("clinical_relevance_score")
    ))
    
    biomarker_id = cur.fetchone()[0]
    
    # 2. THE BRIDGE: Link the variant to the PubMed ID
    pmid = entry.get("pmid")
    if pmid:
        cur.execute("""
            INSERT INTO article_biomarker (pmid, biomarker_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
        """, (pmid, biomarker_id))

    conn.commit()
    cur.close()
    return biomarker_id

# ---------------------------------------------------
# Link Article to Biomarker
# ---------------------------------------------------

def link_article_biomarker(conn, pmid, biomarker_id):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO article_biomarker (pmid, biomarker_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
        """, (pmid, biomarker_id))
    conn.commit()


# ===================================================
# OPTIMIZATION BONUS: Bulk Insertion 
# (Use this if you update pipeline.py to pass lists)
# ===================================================

def bulk_insert_biomarkers(conn, pmid, biomarker_entries):
    if not biomarker_entries:
        return

    insert_query = """
        INSERT INTO biomarkers (
            gene, variant, drug_name, drug_response, sentence, 
            hr_value, or_value, ci_lower, ci_upper, p_value, 
            section_label, clinical_relevance_score
        ) VALUES %s RETURNING id;
    """
    
    values = [
        (e["gene"], e["variant"], e["drug_name"], e["drug_response"], e["sentence"], 
         e["hr_value"], e["or_value"], e["ci_lower"], e["ci_upper"], e["p_value"], 
         e["section_label"], e["clinical_relevance_score"]) 
        for e in biomarker_entries
    ]

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, insert_query, values, fetch=True)
        inserted_ids = [row[0] for row in cur.fetchall()]

        link_query = "INSERT INTO article_biomarker (pmid, biomarker_id) VALUES %s"
        link_values = [(pmid, bid) for bid in inserted_ids]
        psycopg2.extras.execute_values(cur, link_query, link_values)

    conn.commit()


# ===================================================
# Prevents redundant PubMed API calls
# ===================================================

def get_existing_pmids(conn):
    """Retrieves a set of all PMIDs currently in the database."""
    cur = conn.cursor()
    cur.execute("SELECT pmid FROM articles;")
    # Store as strings to match the format returned by PubMed
    existing_pmids = {str(row[0]) for row in cur.fetchall()}
    cur.close()
    return existing_pmids
