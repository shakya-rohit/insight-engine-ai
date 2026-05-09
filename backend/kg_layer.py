from openai import OpenAI
import pickle
import os

client = OpenAI()

KG_FILE = "kg.pkl"

# -------------------------------
# Load / Save KG
# -------------------------------
def load_kg():
    if os.path.exists(KG_FILE):
        with open(KG_FILE, "rb") as f:
            return pickle.load(f)
    return []

def save_kg(kg):
    with open(KG_FILE, "wb") as f:
        pickle.dump(kg, f)


# -------------------------------
# Extract triplets using LLM
# -------------------------------
def extract_triplets(text):
    prompt = f"""
Extract relationships as triplets:
(subject, relation, object)

Return ONLY in format:
("A","relation","B")

Text:
{text[:1000]}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        max_output_tokens=200
    )

    raw = response.output_text

    triplets = []

    for line in raw.split("\n"):
        if "(" in line and ")" in line:
            parts = line.strip("()").split(",")
            if len(parts) == 3:
                triplets.append(tuple([p.strip().strip('"') for p in parts]))

    return triplets


# -------------------------------
# Update KG from chunks
# -------------------------------
def update_kg(chunks):
    kg = load_kg()

    for chunk in chunks:
        triplets = extract_triplets(chunk["text"])
        kg.extend(triplets)

    save_kg(kg)


# -------------------------------
# Query KG
# -------------------------------
# def query_kg(question):
#     kg = load_kg()
#     results = []

#     for s, r, o in kg:
#         if s.lower() in question.lower():
#             results.append((s, r, o))

#     return results[:5]

def query_kg(question):
    kg = load_kg()
    results = []

    q = question.lower()
    q_tokens = set(q.split())

    scored_results = []

    for s, r, o in kg:
        s_l = s.lower()
        r_l = r.lower()
        o_l = o.lower()

        score = 0

        # -----------------------
        # Token matching
        # -----------------------
        for token in q_tokens:
            if token in s_l:
                score += 2
            if token in o_l:
                score += 2
            if token in r_l:
                score += 1

        # -----------------------
        # Exact phrase bonus
        # -----------------------
        if s_l in q:
            score += 3
        if o_l in q:
            score += 3

        # -----------------------
        # Keep relevant results
        # -----------------------
        if score > 0:
            scored_results.append((score, (s, r, o)))

    # -----------------------
    # Sort by score
    # -----------------------
    scored_results.sort(reverse=True, key=lambda x: x[0])

    # -----------------------
    # Return top results
    # -----------------------
    results = [item[1] for item in scored_results[:5]]

    return results