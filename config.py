import os 
from dotenv import load_dotenv

load_dotenv()


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama-3.1-8b-instant"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

CAT_PATH = "data/catalog_phase.json"

MAX_TURNS = 8 
TOP_K = 10 

TEST_TYPES = {
    "A": "Ability & Aptitude",
    "B": "Biodata & Situational Judgement",
    "C": "Competencies",
    "D": "Development & 360",
    "E": "Assessment Exercises",
    "K": "Knowledge & Skills",
    "P": "Personality & Behavior",
    "S": "Simulations"
}

INTENT_MAP = {
    "developer":   ["K", "A"],
    "engineer":    ["K", "A"],
    "programmer":  ["K", "A"],
    "manager":     ["P", "C", "A"],
    "sales":       ["P", "B", "S"],
    "graduate":    ["A", "B"],
    "leadership":  ["P", "C", "D"],
    "personality": ["P"],
    "aptitude":    ["A"],
    "situational": ["B"],
    "knowledge":   ["K"],
    "simulation":  ["S"],
    "competency":  ["C"],
    "360":         ["D"],
    "behavior":    ["P"],
    "cognitive":   ["A"],
}