import os
import logging
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List
from jobsseekers_db import save_profile, get_profile, UserProfile, generate_embedding
from jobs_db import save_job, query_similar_jobs, list_all_jobs, Job
from agents import GPTAssistant

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

assistant_id = "asst_Tl89JdZvyaw8kKR2D83s2TXT"
gpt_assistant = GPTAssistant(assistant_id)


class ProfileData(BaseModel):
    profile_data: dict


class JobData(BaseModel):
    title: str
    description: str


@app.get("/")
def read_root():
    return "Welcome to Connectify AI, we help job seekers enhance their employability through an interactive chatbot"


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
        return {"recommendation": recommendations}
    except Exception as e:
        logger.error(f"Error in embedding or querying jobs: {e}")
        raise HTTPException(status_code=500, detail="Error processing profile")


@app.get("/jobs")
async def get_jobs():
    try:
        jobs = list_all_jobs()
        return {"jobs": jobs}
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/jobs")
async def create_job(job_data: List[JobData]):
    try:
        for job in job_data:
            job_instance = Job(title=job.title, description=job.description)
            save_job(job_instance)
        return {"message": "Jobs saved successfully"}
    except Exception as e:
        logger.error(f"Error saving jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


@app.post("/chat")
async def chat(profile_data: ProfileData):
    profile_info = profile_data.profile_data
    conversation_history = profile_info.get("conversation", "")
    conversation = gpt_assistant.create_conversation()
    conversation = gpt_assistant.send_message(conversation, "user", conversation_history)
    response = gpt_assistant.get_response(conversation)
    return {"response": response}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
