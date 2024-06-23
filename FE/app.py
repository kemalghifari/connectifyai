import os
import yaml
import requests
import chainlit as cl
import openai

# Construct the absolute path to config.yaml
config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../config.yaml'))

# Check if the config file exists
if not os.path.exists(config_path):
    raise FileNotFoundError(f"config.yaml file not found. Please ensure it is located at {config_path}")

# Load configuration from config.yaml
with open(config_path, 'r') as config_file:
    config = yaml.safe_load(config_file)

openai.api_key = config['openai_api_key']
backend_url = config.get('backend_url', "http://127.0.0.1:8001")


@cl.on_chat_start
def on_chat_start():
    cl.user_session.set("profile_data", {})
    cl.user_session.set("question_index", 0)
    return cl.Message(
        content="Hi, I'm here to help you find a job. Could you tell me a bit about what you're looking for?"
    )


@cl.on_message
async def on_message(message: cl.Message):
    profile_data = cl.user_session.get("profile_data")
    conversation_history = profile_data.get("conversation", "")

    # Update conversation history
    conversation_history += f"User: {message.content}\n"
    profile_data["conversation"] = conversation_history
    cl.user_session.set("profile_data", profile_data)

    # Ask OpenAI API what to do next
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": conversation_history}
        ],
        max_tokens=150,
        stop=["User:", "Assistant:"]
    )
    next_step = response.choices[0].message['content'].strip()

    # Determine if all information is complete
    if "all information complete" in next_step.lower():
        # Send data to backend for processing
        response = requests.post(f"{backend_url}/profile", json={"profile_data": profile_data})
        if response.ok:
            job_recommendation = response.json().get('recommendation', 'No recommendations found.')
            await cl.Message(
                content=f"Based on your profile, here are some job recommendations: {job_recommendation}"
            ).send()
            cl.user_session.set("profile_data", {})  # Reset session
        else:
            await cl.Message(content="Failed to process your profile, please try again later.").send()
    else:
        conversation_history += f"Assistant: {next_step}\n"
        profile_data["conversation"] = conversation_history
        cl.user_session.set("profile_data", profile_data)
        await cl.Message(content=next_step).send()


if __name__ == "__main__":
    from chainlit.cli import run_chainlit

    run_chainlit("app.py")
