from openai import OpenAI
from config import KG_FILE, OPENAI_CHAT_MODEL, OPENAI_MAX_OUTPUT_TOKENS
import logging
import pickle
from textwrap import dedent

logger = logging.getLogger(__name__)
client = OpenAI()

# Read and write the locally persisted knowledge graph.
def load_kg():
    if KG_FILE.exists():
        with open(KG_FILE, "rb") as f:
            return pickle.load(f)
    return []

def save_kg(kg):
    with open(KG_FILE, "wb") as f:
        pickle.dump(kg, f)


# Extract subject-relation-object facts from a text chunk.
def extract_triplets(text):
    prompt = dedent("""\
        Extract relationships as triplets:
        (subject, relation, object)

        Return ONLY in format:
        ("A","relation","B")

        Text:
        {text}
        """).format(text=text[:1000])

    response = client.responses.create(
        model=OPENAI_CHAT_MODEL,
        input=prompt,
        max_output_tokens=OPENAI_MAX_OUTPUT_TOKENS
    )

    raw = response.output_text

    triplets = []

    for line in raw.split("\n"):
        if "(" in line and ")" in line:
            parts = line.strip("()").split(",")
            if len(parts) == 3:
                triplets.append(tuple([p.strip().strip('"') for p in parts]))

    return triplets


# Add extracted facts from newly indexed chunks to the graph.
def update_kg(chunks):
    logger.info("Extracting knowledge graph facts from %d chunks", len(chunks))
    kg = load_kg()

    for chunk in chunks:
        triplets = extract_triplets(chunk["text"])
        kg.extend(triplets)

    save_kg(kg)
    logger.info("Knowledge graph saved with %d facts", len(kg))


# Rank graph facts by their overlap with the question.
def query_kg(question):
    kg = load_kg()

    q = question.lower()
    q_tokens = set(q.split())

    scored_results = []

    for s, r, o in kg:
        s_l = s.lower()
        r_l = r.lower()
        o_l = o.lower()

        score = 0

        # Entity matches count more than relation matches.
        for token in q_tokens:
            if token in s_l:
                score += 2
            if token in o_l:
                score += 2
            if token in r_l:
                score += 1

        # Boost facts whose subject or object appears as a phrase.
        if s_l in q:
            score += 3
        if o_l in q:
            score += 3

        if score > 0:
            scored_results.append((score, (s, r, o)))

    scored_results.sort(reverse=True, key=lambda x: x[0])

    results = [item[1] for item in scored_results[:5]]

    return results
