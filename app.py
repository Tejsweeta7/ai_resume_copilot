import os
import re
from collections import Counter
from typing import Any

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


APP_DIR = os.path.dirname(os.path.abspath(__file__))
HF_API_URL = os.getenv("HF_API_URL", "https://api-inference.huggingface.co/models/google/flan-t5-large")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

app = FastAPI(title="AI Hiring Copilot", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


SKILL_LIBRARY = {
    "python", "java", "javascript", "typescript", "html", "css", "react", "next.js",
    "node.js", "express", "fastapi", "flask", "django", "rest api", "sql", "mysql",
    "postgresql", "mongodb", "redis", "git", "github", "docker", "kubernetes", "aws",
    "azure", "gcp", "machine learning", "deep learning", "nlp", "spacy", "regex",
    "scikit-learn", "sklearn", "tensorflow", "pytorch", "huggingface", "transformers",
    "llm", "openai", "prompt engineering", "rag", "langchain", "pandas", "numpy",
    "matplotlib", "seaborn", "data analysis", "api", "cloud", "ci/cd", "mlops",
    "resume parsing", "ats", "candidate ranking", "classification", "regression",
}

DEGREE_TERMS = [
    "b.tech", "bachelor", "computer science", "cse", "m.tech", "master", "mba",
    "bca", "mca", "engineering", "university", "college", "cgpa", "gpa",
]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(APP_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=APP_DIR), name="static")


@app.post("/api/analyze")
async def analyze(
    job_description: str = Form(...),
    resumes: list[UploadFile] = File(...),
) -> dict[str, Any]:
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is required.")
    if not resumes:
        raise HTTPException(status_code=400, detail="Upload at least one resume.")

    jd_profile = parse_document(job_description)
    candidates = []

    for resume in resumes:
        text = await extract_text(resume)
        if not text.strip():
            raise HTTPException(status_code=400, detail=f"{resume.filename} has no readable text.")

        parsed = parse_document(text)
        score = score_candidate(parsed, jd_profile, text, job_description)
        missing_skills = sorted(set(jd_profile["skills"]) - set(parsed["skills"]))
        suggestions = improve_resume(text, job_description, missing_skills)

        candidates.append({
            "name": resume.filename,
            "ats_score": score["total"],
            "breakdown": {
                "skill_match": score["skill_match"],
                "experience": score["experience"],
                "keywords": score["keywords"],
            },
            "parsed": parsed,
            "missing_skills": missing_skills,
            "suggestions": suggestions,
        })

    candidates.sort(key=lambda item: item["ats_score"], reverse=True)
    return {
        "job_profile": jd_profile,
        "candidates": candidates,
    }


async def extract_text(upload: UploadFile) -> str:
    content = await upload.read()
    filename = (upload.filename or "").lower()

    if filename.endswith(".pdf"):
        return extract_pdf(content)
    if filename.endswith(".docx"):
        return extract_docx(content)

    return content.decode("utf-8", errors="ignore")


def extract_pdf(content: bytes) -> str:
    try:
        from pypdf import PdfReader
        from io import BytesIO

        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return content.decode("utf-8", errors="ignore")


def extract_docx(content: bytes) -> str:
    try:
        from docx import Document
        from io import BytesIO

        document = Document(BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    except Exception:
        return content.decode("utf-8", errors="ignore")


def parse_document(text: str) -> dict[str, Any]:
    normalized = normalize(text)
    skills = extract_skills(normalized)
    education = extract_education(text)
    experience_years = extract_experience_years(normalized)

    return {
        "skills": skills,
        "education": education,
        "experience": format_experience(experience_years),
        "experience_years": experience_years,
        "keywords": extract_keywords(normalized),
    }


def extract_skills(normalized_text: str) -> list[str]:
    found = []
    for skill in SKILL_LIBRARY:
        pattern = r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])"
        if re.search(pattern, normalized_text):
            found.append(skill)

    aliases = {"sklearn": "scikit-learn", "api": "rest api"}
    normalized = {aliases.get(skill, skill) for skill in found}
    return sorted(normalized)


def extract_education(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    matches = [
        line for line in lines
        if any(term in line.lower() for term in DEGREE_TERMS)
    ]
    return "; ".join(matches[:3])


def extract_experience_years(text: str) -> float:
    patterns = [
        r"(\d+(?:\.\d+)?)\+?\s*(?:years|year|yrs|yr)\s+(?:of\s+)?experience",
        r"experience\s*(?:of|:)?\s*(\d+(?:\.\d+)?)\+?\s*(?:years|year|yrs|yr)",
    ]
    values = []
    for pattern in patterns:
        values.extend(float(match) for match in re.findall(pattern, text))
    return max(values) if values else 0.0


def extract_keywords(text: str) -> list[str]:
    stop_words = {
        "and", "the", "for", "with", "from", "that", "this", "role", "need",
        "needs", "candidate", "using", "build", "work", "will", "are", "you",
        "your", "our", "job", "description", "required", "skills",
    }
    words = re.findall(r"[a-z][a-z0-9.+#-]{2,}", text)
    counts = Counter(word for word in words if word not in stop_words)
    return [word for word, _ in counts.most_common(24)]


def score_candidate(
    resume_profile: dict[str, Any],
    jd_profile: dict[str, Any],
    resume_text: str,
    jd_text: str,
) -> dict[str, int]:
    required_skills = set(jd_profile["skills"])
    resume_skills = set(resume_profile["skills"])
    skill_match = percentage(len(required_skills & resume_skills), len(required_skills))

    required_experience = jd_profile["experience_years"] or 1
    experience_match = percentage(min(resume_profile["experience_years"], required_experience), required_experience)

    jd_keywords = set(jd_profile["keywords"])
    resume_keywords = set(resume_profile["keywords"]) | resume_skills
    keyword_match = percentage(len(jd_keywords & resume_keywords), len(jd_keywords))

    total = round((skill_match * 0.7) + (experience_match * 0.1) + (keyword_match * 0.2))
    return {
        "skill_match": round(skill_match),
        "experience": round(experience_match),
        "keywords": round(keyword_match),
        "total": total,
    }


def improve_resume(resume_text: str, job_description: str, missing_skills: list[str]) -> list[str]:
    hf_suggestions = generate_with_huggingface(resume_text, job_description, missing_skills)
    if hf_suggestions:
        return hf_suggestions

    gaps = ", ".join(missing_skills[:6]) if missing_skills else "the role's strongest keywords"
    return [
        f"Add a targeted summary that connects your projects to {gaps}.",
        "Rewrite bullets with action verbs, measurable impact, tech stack, and business outcome.",
        "Move the most JD-relevant AI, NLP, ML, API, and deployment skills into the top skills section.",
        "Add one project bullet showing input data, model or LLM method, evaluation logic, and final user value.",
    ]


def generate_with_huggingface(resume_text: str, job_description: str, missing_skills: list[str]) -> list[str]:
    if not HF_API_TOKEN:
        return []

    prompt = (
        "Generate 5 concise resume improvement bullets for this candidate and job. "
        "Focus on ATS keywords, measurable impact, and GenAI/ML relevance.\n\n"
        f"Missing skills: {', '.join(missing_skills[:10])}\n\n"
        f"Resume:\n{resume_text[:2500]}\n\nJob description:\n{job_description[:1800]}"
    )

    try:
        response = requests.post(
            HF_API_URL,
            headers={"Authorization": f"Bearer {HF_API_TOKEN}"},
            json={"inputs": prompt, "parameters": {"max_new_tokens": 220}},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        text = data[0].get("generated_text", "") if isinstance(data, list) else data.get("generated_text", "")
        suggestions = [clean_bullet(line) for line in re.split(r"\n|(?:\d+\.)", text) if clean_bullet(line)]
        return suggestions[:5]
    except Exception:
        return []


def clean_bullet(line: str) -> str:
    return re.sub(r"^[\-*\s]+", "", line).strip()


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def percentage(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 100.0
    return max(0.0, min(100.0, (numerator / denominator) * 100))


def format_experience(years: float) -> str:
    if years <= 0:
        return "Not detected"
    return f"{years:g}+ years"
