import os
import yaml
import requests
import chainlit as cl
import threading
from PyPDF2 import PdfFileReader
from io import BytesIO
import logging

# Construct the absolute path to config.yaml
config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../config.yaml'))

# Check if the config file exists
if not os.path.exists(config_path):
    raise FileNotFoundError(f"config.yaml file not found. Please ensure it is located at {config_path}")

# Load configuration from config.yaml
with open(config_path, 'r') as config_file:
    config = yaml.safe_load(config_file)

backend_url = config.get('backend_url', "http://127.0.0.1:8000")

# Initialize a thread-safe lock
lock = threading.Lock()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_text_from_pdf(file: BytesIO):
    pdf_reader = PdfFileReader(file)
    text = ''
    for page_num in range(pdf_reader.getNumPages()):
        text += pdf_reader.getPage(page_num).extract_text()
    return text


@cl.on_chat_start
def on_chat_start():
    cl.user_session.set("profile_data", {})
    cl.user_session.set("question_index", 0)
    return cl.Message(
        content="Hi, I'm here to help you find a job. Please upload your CV as a PDF file to begin!"
    )


@cl.on_message
async def on_message(message: cl.Message):
    profile_data = cl.user_session.get("profile_data")
    conversation_history = profile_data.get("conversation", "")

    # Update conversation history
    conversation_history += f"User: {message.content}\n"
    profile_data["conversation"] = conversation_history
    cl.user_session.set("profile_data", profile_data)

    # Ask GPT assistant what to do next
    next_step = await cl.run_in_thread(get_next_step, conversation_history)

    # Determine if all information is complete
    if "all information complete" in next_step.lower():
        # Send data to backend for processing
        try:
            response = requests.post(f"{backend_url}/profile", json={"profile_data": profile_data})
            response.raise_for_status()
            job_recommendation = response.json().get('recommendation', 'No recommendations found.')
            await cl.Message(
                content=f"Based on your profile, here are some job recommendations: {job_recommendation}"
            ).send()
            cl.user_session.set("profile_data", {})  # Reset session
        except requests.exceptions.RequestException as e:
            logger.error(f"Error in on_message (profile): {e}")
            await cl.Message(content="Failed to process your profile, please try again later.").send()
    else:
        conversation_history += f"Assistant: {next_step}\n"
        profile_data["conversation"] = conversation_history
        cl.user_session.set("profile_data", profile_data)
        await cl.Message(content=next_step).send()


@cl.on_file_upload
async def on_file_upload(file):
    if file.name.endswith('.pdf'):
        # Extract text from the PDF file
        pdf_text = extract_text_from_pdf(BytesIO(file.content))

        # Save the extracted text to profile data
        profile_data = cl.user_session.get("profile_data")
        profile_data["cv_text"] = pdf_text
        cl.user_session.set("profile_data", profile_data)

        await cl.Message(content=f"{file.name} uploaded successfully. It contains {len(pdf_text)} characters.").send()

        # Continue the conversation by asking for more details
        await cl.Message(
            content="I've extracted your CV. Can you tell me more about your work experience and skills?").send()
    else:
        await cl.Message(content="Please upload a PDF file.").send()


def get_next_step(conversation_history):
    with lock:
        try:
            response = requests.post(f"{backend_url}/chat",
                                     json={"profile_data": {"conversation": conversation_history}})
            response.raise_for_status()
            response_data = response.json()
            return response_data.get("response", "I'm sorry, I couldn't process that. Could you please rephrase?")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error in get_next_step: {e}")
            return "There was an error processing your request. Please try again later."


if __name__ == "__main__":
    from chainlit.cli import run_chainlit

    run_chainlit("app.py")