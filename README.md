# AI Hiring Copilot

An end-to-end GenAI + NLP + ML web app for resume parsing, ATS scoring, skill gap analysis, resume improvement suggestions, and candidate ranking.

## Features

- Resume parser for skills, education, and experience
- ATS score engine using skill match, experience match, and keyword match
- Skill gap analyzer comparing resume skills against job description skills
- HuggingFace GenAI integration for resume improvement suggestions
- Multi-resume candidate ranking
- Clean HTML/CSS/JS frontend with FastAPI backend

## Scoring Formula

```text
score = (skill_match * 0.5) + (experience * 0.3) + (keywords * 0.2)
```

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000`.

For optional spaCy/scikit-learn experimentation, use Python 3.11 or 3.12 and install:

```bash
pip install -r requirements-ml.txt
```

## HuggingFace Setup

The app works without a token using local rule-based fallback suggestions. For live GenAI suggestions, set:

```bash
set HF_API_TOKEN=your_huggingface_token
```

Optional custom model endpoint:

```bash
set HF_API_URL=https://api-inference.huggingface.co/models/google/flan-t5-large
```

## Recommended Demo Flow

1. Paste the JD for an AI/ML or GenAI internship.
2. Upload one or more `.txt` resumes.
3. Review the ATS score, parsed skills, missing skills, generated suggestions, and ranking.
