"""Quick manual check — run before building any endpoint."""

from app.services.retrieval_service import retrieval_service

QUERIES = [
    "bhat",
    "vaat koto calorie",
    "rice",
    "ভাত",
    "ami raate ki khabo",
    "quantum physics",        # should return NOTHING
    "car engine oil",         # should return NOTHING
]

for q in QUERIES:
    hits = retrieval_service.search(q, top_k=3)
    print(f"\nQuery: {q}")
    if not hits:
        print("  (no results)")
    for h in hits:
        print(f"  total={h['_score']:>6}  bm25={h['_bm25']:>6}  dense={h['_dense']:>6}  {h['name_en']}")