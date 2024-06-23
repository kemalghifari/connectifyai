import os
import json
import logging
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from jobsseekers_db import save_profile, get_profile, UserProfile, generate_embedding
from jobs_db import save_job, query_similar_jobs, list_all_jobs, Job

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProfileData(BaseModel):
    profile_data: dict


class JobData(BaseModel):
    title: str
    description: str


@app.on_event("startup")
async def load_job_data():
    job_data_path = os.path.join(os.path.dirname(__file__), "job_data.json")
    try:
        with open(job_data_path, "r") as f:
            job_data = json.load(f)
            for job in job_data:
                save_job(Job(title=job["title"], description=job["description"]))
        logger.info("Job data loaded successfully.")
    except Exception as e:
        logger.error(f"Error loading job data: {e}")


@app.get("/")
def read_root():
    return "Welcome to Connectify AI, we help jobsseekers enhance their employability through interactive chatbot"


@app.post("/profile")
async def create_profile(profile_data: ProfileData):
    profile_info = profile_data.profile_data

    if 'text' not in profile_info:
        profile_info['text'] = (
            f"Name: {profile_info.get('name', '')}, Education: {profile_info.get('education', '')}, "
            f"Work Experience: {profile_info.get('work_experience', '')}, Volunteer Experience: {profile_info.get('volunteer_experience', '')}, "
            f"Skills: {profile_info.get('skills', '')}, Interests: {profile_info.get('interests', '')}, Motivation: {profile_info.get('motivation', '')}, "
            f"Industry Interest: {profile_info.get('industry_interest', '')}"
        )

    user_profile = UserProfile(**profile_info)
    save_profile(user_profile)
    return {"message": "Profile saved successfully"}


@app.get("/profile")
async def get_profile_endpoint(name: str = Query(..., description="The name of the profile to retrieve")):
    try:
        profile = get_profile(name)
        if profile:
            return profile
        else:
            raise HTTPException(status_code=404, detail="Profile not found")
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/recommend")
async def recommend(profile_data: ProfileData):
    profile_info = profile_data.profile_data
    try:
        embedding = generate_embedding(profile_info['conversation'])
        recommendations = query_similar_jobs(embedding)
    except Exception as e:
        logger.error(f"Error in embedding or querying jobs: {e}")
        raise HTTPException(status_code=500, detail="Error processing profile")

    if recommendations:
        return {"recommendation": recommendations}
    else:
        raise HTTPException(status_code=404, detail="No suitable job found")


@app.get("/jobs")
async def get_jobs():
    try:
        jobs = list_all_jobs()
        return {"jobs": jobs}
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/jobs")
async def create_job(job_data: JobData):
    job = Job(title=job_data.title, description=job_data.description)
    try:
        save_job(job)
        # Append the new job to job_data.json
        job_data_path = os.path.join(os.path.dirname(__file__), "job_data.json")
        try:
            with open(job_data_path, "r") as f:
                job_list = json.load(f)
        except FileNotFoundError:
            job_list = []

        job_list.append(job_data.dict())
        with open(job_data_path, "w") as f:
            json.dump(job_list, f, indent=4)

        return {"message": "Job saved successfully"}
    except Exception as e:
        logger.error(f"Error saving job: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)