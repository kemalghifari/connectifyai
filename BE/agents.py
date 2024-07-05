import openai
import yaml
import logging
import os

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


def call_function(function_name, function_args):
    try:
        # This is a placeholder. Actual function calling logic will depend on your backend API setup.
        response = {"result": f"Function {function_name} called with arguments {function_args}"}
        return response
    except Exception as e:
        logger.error(f"Error calling function {function_name}: {e}")
        return {"result": "Error"}


class GPTAssistant:
    def __init__(self, assistant_id):
        self.assistant_id = assistant_id

    def create_conversation(self):
        return []

    def send_message(self, conversation, role, message):
        conversation.append({"role": role, "content": message})
        return conversation

    def get_response(self, conversation):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=conversation
            )
            assistant_message = response['choices'][0]['message']['content']
            conversation.append({"role": "assistant", "content": assistant_message})
            return assistant_message
        except Exception as e:
            logger.error(f"Error getting response: {e}")
            return "Sorry, I'm having trouble understanding. Please try again."
