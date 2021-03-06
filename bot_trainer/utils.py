from typing import Text, List, Dict
from mongoengine.document import BaseDocument, Document
import os
import yaml
from mongoengine import StringField, ListField
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from bot_trainer.exceptions import AppException
import glob
import os
import requests
from rasa.constants import DEFAULT_MODELS_PATH
import string
import random

class Utility:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
    environment = None

    @staticmethod
    def check_empty_string(value: str):
        if not value:
            return True
        if not value.strip():
            return True
        else:
            return False

    @staticmethod
    def prepare_nlu_text(example: Text, entities: List[Dict]):
        if not Utility.check_empty_string(example):
            if entities:
                for entity in entities:
                    example = example.replace(
                        entity["value"],
                        "[" + entity["value"] + "](" + entity["entity"] + ")",
                    )
        return example

    @staticmethod
    def validate_document_list(documents: List[BaseDocument]):
        if documents:
            for document in documents:
                document.validate()

    @staticmethod
    def load_yaml(file: Text):
        with open(file) as fp:
            return yaml.load(fp, yaml.FullLoader)

    @staticmethod
    def load_evironment():
        environment = Utility.load_yaml(os.getenv("system_file", "./system.yaml"))
        for key in environment:
            if key in os.environ:
                environment[key] = os.getenv(key)
        Utility.environment = environment

    @staticmethod
    def validate_fields(fields: Dict, data: Dict):
        error = ""
        for key, value in fields.items():
            if isinstance(value, StringField):
                if data[key] != None and str(data["key"]).strip():
                    error += "\n " + key + " cannot be empty or blank spaces"
            elif isinstance(value, ListField):
                if value.required and value:
                    error += "\n " + key + " cannot be empty"
        if error:
            raise error

    @staticmethod
    def is_exist(
        document: Document, query: Dict, exp_message: Text = None, raise_error=True,
    ):
        doc = document.objects(status=True, __raw__=query)
        if doc.__len__():
            if raise_error:
                if Utility.check_empty_string(exp_message):
                    raise AppException("Exception message cannot be empty")
                raise AppException(exp_message)
            else:
                return True
        else:
            if not raise_error:
                return False

    @staticmethod
    def verify_password(plain_password, hashed_password):
        return Utility.pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password):
        if not Utility.check_empty_string(password):
            return Utility.pwd_context.hash(password)

    @staticmethod
    def get_latest_file(folder):
        if not os.path.exists(folder):
            raise AppException("Folder does not exists!")
        return max(glob.iglob(folder + "/*"), key=os.path.getctime)

    @staticmethod
    def check_empty_list_elements(items: List[Text]):
        for item in items:
            if Utility.check_empty_string(item):
                return True
        return False

    @staticmethod
    def deploy_model(endpoint: Dict, bot: Text):
        if not endpoint or not endpoint.get("bot_endpoint"):
            raise AppException("Please configure the bot endpoint for deployment!")
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        url = endpoint["bot_endpoint"].get("url")
        if endpoint["bot_endpoint"].get("token_type") and endpoint["bot_endpoint"].get("token"):
            headers['Authorization'] = endpoint["bot_endpoint"].get("token_type") +" "+ endpoint["bot_endpoint"].get("token")

        try:
            response = requests.put(url + "/model",
                                    json={"model_file": Utility.get_latest_file(os.path.join(DEFAULT_MODELS_PATH, bot))},
                                    headers=headers)
            json_response = response.json()
            if 'message' in json_response:
                result = json_response['message']
            elif 'reason' in json_response:
                result = json_response['reason']
            else:
                result = json_response
        except requests.exceptions.ConnectionError as e:
            raise AppException("Host is not reachable")
        return result

    @staticmethod
    def generate_password(size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))