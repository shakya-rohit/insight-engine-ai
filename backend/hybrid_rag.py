from rag_faiss import retrieve
from kg_layer import query_kg
from openai import OpenAI

client = OpenAI()

def hybrid_answer(query, index, chunks):
    # -------------------
    # RAG retrieval
    # -------------------
    rag_docs = retrieve(query, index, chunks)

    # -------------------
    # KG retrieval
    # -------------------
    kg_facts = query_kg(query)

    # -------------------
    # Build contexts
    # -------------------
    context_rag = "\n\n".join(
        [f"[{c['source']}]: {c['text']}" for c in rag_docs]
    )

    context_kg = "\n".join(
        [f"{s} {r} {o}" for s, r, o in kg_facts]
    )

    # -------------------
    # Final prompt
    # -------------------
    prompt = f"""
Use BOTH structured knowledge and context.

Structured Knowledge:
{context_kg}

Context:
{context_rag}

If answer is not found, say "I don't know".

Question:
{query}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        max_output_tokens=200
    )

    return response.output_text