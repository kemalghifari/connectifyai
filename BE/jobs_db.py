import openai
from pydantic import BaseModel
import chromadb
import logging
import os
import yaml
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration from config.yaml
config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config.yaml'))
try:
    with open(config_path, "r") as config_file:
        config = yaml.safe_load(config_file)
except FileNotFoundError:
    raise Exception(f"config.yaml file not found. Please ensure it is located at {config_path}")

openai.api_key = config["openai_api_key"]


class Job(BaseModel):
    title: str
    description: str
    embedding: list = None


# Initialize ChromaDB client and collection
client = chromadb.Client()
jobs_collection_name = "job_listings"
jobs_collection = client.get_or_create_collection(name=jobs_collection_name)


def generate_embedding(text: str):
    response = openai.Embedding.create(
        input=text,
        model="text-embedding-ada-002"
    )
    embedding = response['data'][0]['embedding']
    logger.info(f"Generated embedding for text: {text}")
    return embedding


def save_job(job: Job):
    embedding = generate_embedding(f"{job.title} {job.description}")
    job.embedding = embedding
    jobs_collection.add(
        ids=[job.title],
        documents=[json.dumps(job.dict())],  # Ensure job is saved as a JSON string
        embeddings=[embedding]
    )
    logger.info(f"Saved job {job.title} with embedding: {embedding}")


def get_job(title: str):
    results = jobs_collection.get(ids=[title])
    logger.info(f"Queried job for {title}: {results}")
    return results


def query_similar_jobs(embedding: list, top_k: int = 5):
    results = jobs_collection.query(
        query_embeddings=[embedding],
        n_results=top_k
    )
    logger.info(f"Queried similar jobs with embedding: {embedding} - Results: {results}")
    recommendations = []
    for document_list in results['documents']:
        for document in document_list:
            job = json.loads(document)  # Convert JSON string back to dictionary
            recommendations.append(f"{job['title']}: {job['description']}")
    return recommendations


def list_all_jobs():
    all_jobs = []
    try:
        job_ids = jobs_collection.list_ids()
        if job_ids:
            results = jobs_collection.get(ids=job_ids)
            all_jobs = [json.loads(doc) for doc in results['documents']]
        logger.info(f"Listing all jobs: {all_jobs}")
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
    return all_jobs
