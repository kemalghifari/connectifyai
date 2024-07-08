import openai
import yaml
import logging
import os
import requests

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

backend_url = config.get('backend_url', "http://127.0.0.1:8001")


def call_function(endpoint: str, function_args: dict, method: str = "post"):
    try:
        if method == "post":
            response = requests.post(f"{backend_url}/{endpoint}", json=function_args)
        elif method == "get":
            response = requests.get(f"{backend_url}/{endpoint}", params=function_args)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error calling backend endpoint {endpoint}: {e}")
        return {"result": "Error"}


class GPTAssistant:
    def __init__(self, assistant_id):
        self.assistant_id = assistant_id

    @staticmethod
    def create_conversation():
        return []

    @staticmethod
    def send_message(conversation, role, message):
        conversation.append({"role": role, "content": message})
        return conversation

    def get_response(self, conversation):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=conversation,
                functions=[
                    {
                        "name": "get_profile",
                        "description": "Retrieve the profile information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "The name of the profile to retrieve"}
                            },
                            "required": ["name"]
                        }
                    },
                    {
                        "name": "recommend_jobs",
                        "description": "Get job recommendations based on profile data",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "profile_data": {
                                    "type": "object",
                                    "properties": {
                                        "conversation": {"type": "string",
                                                         "description": "The conversation history for generating "
                                                                        "recommendations"}
                                    },
                                    "required": ["conversation"]
                                }
                            }
                        }
                    },
                    {
                        "name": "get_jobs",
                        "description": "Get the list of all jobs",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "create_job",
                        "description": "Create a new job listing",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "job_data": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "title": {"type": "string"},
                                            "description": {"type": "string"}
                                        },
                                        "required": ["title", "description"]
                                    }
                                }
                            }
                        }
                    }
                ]
            )
            assistant_message = response['choices'][0]['message']['content']
            if response['choices'][0]['finish_reason'] == 'function_call':
                function_call = response['choices'][0]['message']['function_call']
                result = self.handle_function_call(function_call)
                conversation.append({"role": "assistant", "content": str(result)})
                return result
            else:
                conversation.append({"role": "assistant", "content": assistant_message})
                return assistant_message
        except Exception as e:
            logger.error(f"Error getting response: {e}")
            return "Sorry, I'm having trouble understanding. Please try again."

    @staticmethod
    def handle_function_call(function_call):
        function_name = function_call.get("name")
        function_args = function_call.get("arguments", {})

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
            return {"result": "Unknown function"}


