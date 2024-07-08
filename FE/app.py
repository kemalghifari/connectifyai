import os
import yaml
import aiohttp
import chainlit as cl
from PyPDF2 import PdfReader
from io import BytesIO
import logging
import asyncio

# Ensure the correct import
from BE.agents import call_function

# Construct the absolute path to config.yaml
config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../config.yaml'))

# Check if the config file exists
if not os.path.exists(config_path):
    raise FileNotFoundError(f"config.yaml file not found. Please ensure it is located at {config_path}")

# Load configuration from config.yaml
with open(config_path, 'r') as config_file:
    config = yaml.safe_load(config_file)

backend_url = config.get('backend_url', "http://127.0.0.1:8001")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_text_from_pdf(file: BytesIO):
    logger.info("Starting to extract text from PDF")
    pdf_reader = PdfReader(file)
    text = ''
    for page in pdf_reader.pages:
        text += page.extract_text()
    logger.info(f"Extracted {len(text)} characters from PDF")
    return text


@cl.on_chat_start
async def on_chat_start():
    await cl.Message(content="Hi, I'm here to help you find a job. How can I assist you today?").send()


@cl.on_message
async def on_message(message: cl.Message):
    profile_data = cl.user_session.get("profile_data", {})
    conversation_history = profile_data.get("conversation", "")

    # Update conversation history
    conversation_history += f"User: {message.content}\n"
    profile_data["conversation"] = conversation_history
    cl.user_session.set("profile_data", profile_data)

    logger.info("User message received and added to conversation history")

    # Ask GPT assistant what to do next
    next_step = await get_next_step(conversation_history)

    if "upload your cv" in next_step.lower():
        logger.info("Requesting CV upload from user")
        files = await cl.AskFileMessage(
            content="Please upload your CV as a PDF file.",
            accept=["application/pdf"],
            max_size_mb=20,
            timeout=180
        ).send()

        pdf_file = files[0]
        msg = cl.Message(content=f"Processing `{pdf_file.name}`...", disable_feedback=True)
        await msg.send()

        with open(pdf_file.path, "rb") as f:
            pdf_text = extract_text_from_pdf(BytesIO(f.read()))

        profile_data["cv_text"] = pdf_text
        cl.user_session.set("profile_data", profile_data)

        msg.content = f"Processing `{pdf_file.name}` done. It contains {len(pdf_text)} characters."
        await msg.update()

        logger.info(f"CV uploaded and processed. Extracted text length: {len(pdf_text)}")

        # Continue conversation with the assistant using the updated profile_data
        next_step = await get_next_step(conversation_history + f"CV uploaded with text: {pdf_text}")

    # Determine if all information is complete
    if "all information complete" in next_step.lower():
        logger.info("All information complete, sending profile to backend")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{backend_url}/profile", json={"profile_data": profile_data}) as response:
                    response.raise_for_status()
                    job_recommendation = (await response.json()).get('recommendation', 'No recommendations found.')
                    await cl.Message(
                        content=f"Based on your profile, here are some job recommendations: {job_recommendation}").send()
                    cl.user_session.set("profile_data", {})  # Reset session
                    logger.info("Job recommendations sent to user and session reset")
        except aiohttp.ClientError as e:
            logger.error(f"Error in on_message (profile): {e}")
            await cl.Message(content="Failed to process your profile, please try again later.").send()
    else:
        conversation_history += f"Assistant: {next_step}\n"
        profile_data["conversation"] = conversation_history
        cl.user_session.set("profile_data", profile_data)
        await cl.Message(content=next_step).send()
        logger.info("Next step sent to user")


async def get_next_step(conversation_history):
    logger.info("Starting to get next step from backend")
    try:
        timeout = aiohttp.ClientTimeout(total=120)  # Increase the timeout duration to 120 seconds
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{backend_url}/chat",
                                    json={"profile_data": {"conversation": conversation_history}}) as response:
                logger.info("Request sent to backend")
                response.raise_for_status()
                response_data = await response.json()
                logger.info("Received response from backend")

                # Check if the response includes a function call
                if 'function_call' in response_data:
                    logger.info("Function call detected in backend response")
                    function_call = response_data['function_call']
                    function_response = handle_function_call(function_call)
                    logger.info(f"Function call handled: {function_call['name']}")
                    return function_response

                return response_data.get("response", "I'm sorry, I couldn't process that. Could you please rephrase?")
    except aiohttp.ClientError as e:
        logger.error(f"Error in get_next_step: {e}")
        return "There was an error processing your request. Please try again later."


def handle_function_call(function_call):
    function_name = function_call.get("name")
    function_args = function_call.get("arguments", {})

    logger.info(f"Handling function call: {function_name}")

    # Map function names to the respective function handlers
    function_mapping = {
        "get_profile": lambda args: call_function("profile", args, method="get"),
        "recommend_jobs": lambda args: call_function("recommend", args),
        "get_jobs": lambda args: call_function("jobs", {}, method="get"),
        "create_job": lambda args: call_function("jobs", args)
    }

    # Call the appropriate function
    if function_name in function_mapping:
        return function_mapping[function_name](function_args)
    else:
        logger.warning(f"Unknown function: {function_name}")
        return {"result": "Unknown function"}


if __name__ == "__main__":
    from chainlit.cli import run_chainlit

    run_chainlit("app.py")
