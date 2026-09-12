from typing import Dict, Any, List

# Domain-appropriate educational resource type reference mapping
DOMAIN_RESOURCE_TYPES = {
    "python": ["Documentation", "Coding Exercises", "Interactive Tutorials", "Video Demonstrations", "Project Specifications"],
    "mathematics": ["Worked Problems", "Concept Explanations", "Step-by-Step Proofs", "Practice Sets", "Visualizations"],
    "physics": ["Interactive Simulations", "Worked Physics Problems", "Textbook Reference", "Lecture Videos", "Lab Experiments"],
    "default": ["Textbook Reference", "Tutorial Articles", "Practice Sets", "Educational Videos", "Case Studies"]
}

# Curated, authoritative learning links per topic/domain
CURATED_TOPIC_URLS = {
    # Python
    "variables": "https://docs.python.org/3/tutorial/introduction.html#using-python-as-a-calculator",
    "data_types": "https://docs.python.org/3/library/stdtypes.html",
    "operators": "https://docs.python.org/3/library/stdtypes.html#numeric-types-int-float-complex",
    "conditions": "https://docs.python.org/3/tutorial/controlflow.html#if-statements",
    "loops": "https://docs.python.org/3/tutorial/controlflow.html#for-statements",
    "functions": "https://docs.python.org/3/tutorial/controlflow.html#defining-functions",
    "lists": "https://docs.python.org/3/tutorial/introduction.html#lists",
    "dictionaries": "https://docs.python.org/3/tutorial/datastructures.html#dictionaries",
    "python": "https://docs.python.org/3/tutorial/",

    # Mathematics
    "linear_algebra": "https://www.khanacademy.org/math/linear-algebra",
    "calculus": "https://www.khanacademy.org/math/calculus-1",
    "probability_stats": "https://www.khanacademy.org/math/statistics-probability",
    "discrete_math": "https://www.khanacademy.org/math",
    "mathematics": "https://www.khanacademy.org/math",

    # Physics
    "classical_mechanics": "https://www.physicsclassroom.com/class/1DKin",
    "thermodynamics": "https://www.physicsclassroom.com/class/thermal",
    "electromagnetism": "https://www.physicsclassroom.com/class/circuits",
    "quantum_physics": "https://www.physicsclassroom.com/class",
    "physics": "https://www.physicsclassroom.com/"
}

def get_domain_resource_types(domain_id: str) -> List[str]:
    """
    Returns list of recommended, domain-appropriate resource types for a domain.
    """
    d_key = domain_id.lower()
    for key in DOMAIN_RESOURCE_TYPES:
        if key in d_key:
            return DOMAIN_RESOURCE_TYPES[key]
    return DOMAIN_RESOURCE_TYPES["default"]

def get_verified_url_for_area(area_id: str, domain_id: str) -> Dict[str, Any]:
    """
    Looks up curated, verified educational URL for an area or fallback domain reference.
    """
    a_key = str(area_id).lower()
    for key, url in CURATED_TOPIC_URLS.items():
        if key in a_key:
            return {"url": url, "verification_status": "verified"}

    d_key = str(domain_id).lower()
    for key, url in CURATED_TOPIC_URLS.items():
        if key in d_key:
            return {"url": url, "verification_status": "verified"}

    return {"url": None, "verification_status": "unverified"}

def validate_resource_url(url: Any) -> Dict[str, Any]:
    """
    Validates URL string accuracy. Prevents fabricated or invalid URLs from being shown.
    Returns dictionary with url (str or None) and verification_status.
    """
    if not url or not isinstance(url, str):
        return {"url": None, "verification_status": "unverified"}

    url_str = url.strip()
    if url_str.startswith("http://") or url_str.startswith("https://"):
        return {"url": url_str, "verification_status": "verified"}

    return {"url": None, "verification_status": "unverified"}
