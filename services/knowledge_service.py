from typing import List, Dict, Any, Optional
from db import get_db
from models.domain import Domain
from models.curriculum import Curriculum, CurriculumArea

def get_all_domains() -> List[Domain]:
    """
    Retrieves all supported learning domains from database.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description FROM domains ORDER BY id;")
    rows = cursor.fetchall()
    conn.close()
    return [Domain.from_row(r) for r in rows]

def get_domain_by_id(domain_id: str) -> Optional[Domain]:
    """
    Retrieves a single learning domain by ID.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description FROM domains WHERE id = ?;", (domain_id,))
    row = cursor.fetchone()
    conn.close()
    return Domain.from_row(row) if row else None

def get_domain_curriculum(domain_id: str) -> Curriculum:
    """
    Constructs the curriculum structure (topics and KCs) for a given learning domain.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT topic_id, topic_name, description 
        FROM knowledge_topics 
        WHERE domain_id = ?;
    """, (domain_id,))
    topic_rows = cursor.fetchall()

    areas = []
    for t in topic_rows:
        tid = t["topic_id"]
        tname = t["topic_name"]
        tdesc = t["description"]
        
        # Add topic as high-level area
        areas.append(CurriculumArea(
            id=tid,
            name=tname,
            type="topic",
            description=tdesc,
            parent_id=None,
            prerequisites=[]
        ))

        # Add KCs belonging to topic as sub-concepts
        cursor.execute("""
            SELECT kc_id, kc_name, description 
            FROM knowledge_components 
            WHERE topic_id = ?;
        """, (tid,))
        kc_rows = cursor.fetchall()
        for k in kc_rows:
            areas.append(CurriculumArea(
                id=k["kc_id"],
                name=k["kc_name"],
                type="concept",
                description=k["description"],
                parent_id=tid,
                prerequisites=[]
            ))

    conn.close()
    return Curriculum(domain_id=domain_id, areas=areas)
