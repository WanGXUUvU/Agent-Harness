from pathlib import Path

knowledge_file = Path(__file__).parent / "knowledge.txt"
with open(knowledge_file, "r", encoding="utf-8") as f:
    KNOWLEDGE_BASE = [line.strip() for line in f if line.strip()]
