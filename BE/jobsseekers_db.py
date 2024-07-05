import chromadb
import openai
import yaml
from pydantic import BaseModel
import os

# Load configuration from config.yaml
config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config.yaml'))
try:
    with open(config_path, "r") as config_file:
        config = yaml.safe_load(config_file)
except FileNotFoundError:
    raise Exception(f"config.yaml file not found. Please ensure it is located at {config_path}")

openai.api_key = config["openai_api_key"]


class UserProfile(BaseModel):
    name: str
    education: str
    work_experience: str
    volunteer_experience: str
    skills: str
    interests: str
    motivation: str
    industry_interest: str
    text: str


# Initialize ChromaDB client and collection
client = chromadb.Client()
profiles_collection = client.get_or_create_collection(name="job_seeker_profiles")


def generate_embedding(text: str):
    response = openai.Embedding.create(
        input=text,
        model="text-embedding-ada-002"
    )
    embedding = response['data'][0]['embedding']
    return embedding


def save_profile(profile: UserProfile):
    embedding = generate_embedding(profile.text)
    profiles_collection.add(
        ids=[profile.name],
        documents=[profile.json()],
        embeddings=[embedding]
    )


def get_profile(name: str):
    results = profiles_collection.get(ids=[name])
    return results


def query_similar_profiles(text: str, top_k: int = 5):
    embedding = generate_embedding(text)
    results = profiles_collection.query(
        query_embeddings=[embedding],
        n_results=top_k
    )
    return results
