from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Blog agent is alive"}

@app.get("/run")
def run_job():
    # TODO: later:
    # 1) Generate SEO blog post with OpenAI
    # 2) Publish to Blogger
    return {"status": "pending", "message": "Blog job will run here"}
