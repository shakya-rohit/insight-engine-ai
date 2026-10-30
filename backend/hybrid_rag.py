from rag_faiss import retrieve
from kg_layer import query_kg
from openai import OpenAI
from textwrap import dedent
from config import OPENAI_CHAT_MODEL, OPENAI_MAX_OUTPUT_TOKENS

client = OpenAI()

def hybrid_answer(query, index, chunks):
    # Combine semantic passages and structured facts in one answer prompt.
    rag_docs = retrieve(query, index, chunks)

    kg_facts = query_kg(query)

    context_rag = "\n\n".join(
        [f"[{c['source']}]: {c['text']}" for c in rag_docs]
    )

    context_kg = "\n".join(
        [f"{s} {r} {o}" for s, r, o in kg_facts]
    )

    prompt = dedent("""\
        Use BOTH structured knowledge and context.

        Structured Knowledge:
        {context_kg}

        Context:
        {context_rag}

        If answer is not found, say "I don't know".

        Question:
        {query}
        """).format(context_kg=context_kg, context_rag=context_rag, query=query)

    response = client.responses.create(
        model=OPENAI_CHAT_MODEL,
        input=prompt,
        max_output_tokens=OPENAI_MAX_OUTPUT_TOKENS
    )

    return response.output_text
