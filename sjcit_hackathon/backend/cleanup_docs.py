from database import get_connection
from vector_store import InMemoryVectorDB
from sop_graph import SOPKnowledgeGraph

with get_connection() as conn:
    rows = conn.execute("SELECT id, title FROM documents WHERE tenant_id = 'tenant_a' AND title NOT LIKE '%Northstar%' AND title NOT LIKE '%Starlink%'").fetchall()
    print("Deleting extra documents:")
    for r in rows:
        print(f" - {r['title']} ({r['id']})")
        conn.execute("DELETE FROM document_chunks WHERE doc_id = ?", (r["id"],))
        conn.execute("DELETE FROM document_versions WHERE doc_id = ?", (r["id"],))
        conn.execute("DELETE FROM documents WHERE id = ?", (r["id"],))

# Rebuild vector index and graph
vdb = InMemoryVectorDB.get_instance()
vdb.rebuild_tenant("tenant_a")
graph = SOPKnowledgeGraph.get_instance()
graph.build_graph()

print("\nRemaining documents in tenant_a:")
with get_connection() as conn:
    for r in conn.execute("SELECT id, title, created_by FROM documents WHERE tenant_id = 'tenant_a'").fetchall():
        print(dict(r))
print("Done!")
