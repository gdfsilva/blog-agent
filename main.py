import os
import random
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from openai import OpenAI

# ---------- Config ----------

# Create the OpenAI client. It reads OPENAI_API_KEY from env vars.
client = OpenAI()

# You can change these to fit your niche later.
DEFAULT_TOPICS = [
    {
        "topic": "How to start a profitable niche blog with AI",
        "keyword": "ai niche blog",
    },
    {
        "topic": "Beginner’s guide to affiliate marketing with low budget",
        "keyword": "beginner affiliate marketing",
    },
    {
        "topic": "Best side hustles you can automate with AI tools",
        "keyword": "automated side hustles with ai",
    },
    {
        "topic": "How to use ChatGPT to write product reviews that convert",
        "keyword": "chatgpt product reviews",
    },
    {
        "topic": "SEO tips for small blogs in competitive niches",
        "keyword": "seo tips for small blog",
    },
]


# ---------- FastAPI models ----------

class RunResponse(BaseModel):
    topic: str
    keyword: str
    language: str
    min_words: int
    created_at: str
    article_markdown: str


# ---------- FastAPI app ----------

app = FastAPI(
    title="Blog Agent",
    description="Small API that generates long-form SEO blog posts using OpenAI.",
    version="0.1.0",
)


@app.get("/")
def read_root():
    """
    Simple health/status endpoint.
    """
    return {
        "status": "ok",
        "message": "Blog agent is alive",
        "docs": "/docs",
    }


def build_prompt(
    topic: str,
    keyword: str,
    language: str,
    min_words: int,
) -> str:
    """
    Build the user prompt given to the model.
    """
    return f"""
Write a long-form blog post in {language}.

Topic: {topic}
Target keyword: {keyword}

Requirements:
- Minimum length: {min_words} words (aim for at least this, not less).
- Use clean Markdown only (no HTML).
- Start with a strong H1 title (using #).
- After the introduction, include a short "Table of contents" as a bullet list.
- Use clear H2 and H3 headings to structure the content.
- Naturally weave the target keyword into the title, introduction, and several headings, but keep it natural (no keyword stuffing).
- Use short paragraphs (2–4 sentences), bullet lists and numbered lists where helpful.
- Provide practical, actionable tips and examples, not just theory.
- End with:
  - A short conclusion section
  - A "Key takeaways" bullet list
  - A "FAQ" section with 5 questions and answers related to the topic.
- Do NOT mention that you are an AI or that you were given instructions; just write the article.
"""


async def generate_article(
    topic: str,
    keyword: str,
    language: str = "English",
    min_words: int = 1800,
) -> str:
    """
    Call OpenAI Chat Completions to generate the blog article.
    """
    # Safety check: make sure API key is set
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Configure it as an environment variable."
        )

    user_prompt = build_prompt(topic, keyword, language, min_words)

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",  # you can change to gpt-4.1 or gpt-4o if you want
            temperature=0.7,
            max_tokens=3000,  # enough for ~1800–2200 words
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert SEO content writer. "
                        "You write engaging, helpful long-form articles that read naturally."
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as e:
        raise RuntimeError(f"Error calling OpenAI API: {e}")

    article = completion.choices[0].message.content
    if not article:
        raise RuntimeError("OpenAI returned an empty article.")

    return article


@app.get("/run", response_model=RunResponse)
async def run_job(
    topic: Optional[str] = Query(
        default=None,
        description="Optional custom topic. If not provided, a random one is chosen.",
    ),
    keyword: Optional[str] = Query(
        default=None,
        description="Optional custom SEO keyword. If not provided, a random one is chosen.",
    ),
    language: str = Query(
        default="English",
        description="Language of the article (e.g. English, Portuguese-BR, Spanish).",
    ),
    min_words: int = Query(
        default=1800,
        ge=500,
        le=5000,
        description="Minimum word count target for the article.",
    ),
):
    """
    Generate a long-form SEO blog article.

    - If `topic` and `keyword` are not provided, we pick one from DEFAULT_TOPICS.
    - Returns article in Markdown so you can publish it to your blog or CMS.
    """
    # Choose topic/keyword if not provided
    if not topic or not keyword:
        choice = random.choice(DEFAULT_TOPICS)
        topic = topic or choice["topic"]
        keyword = keyword or choice["keyword"]

    try:
        article = await generate_article(
            topic=topic,
            keyword=keyword,
            language=language,
            min_words=min_words,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    now = datetime.utcnow().isoformat() + "Z"

    # For now we only return the article; in a later step we can
    # add automatic publishing to Blogger/WordPress here.
    return RunResponse(
        topic=topic,
        keyword=keyword,
        language=language,
        min_words=min_words,
        created_at=now,
        article_markdown=article,
    )
