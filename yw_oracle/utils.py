
import os
import requests
import json
import secrets
import time
import hmac
import hashlib
import base64
import urllib.parse
import uuid
from dotenv import load_dotenv

load_dotenv()

class NetSuiteClient:
    def __init__(self):
        if os.getenv("ENV") == "PROD":
            self.account_id = os.getenv("ACCOUNT_ID")
            self.consumer_key = os.getenv("NETSUITE_CONSUMER_KEY")
            self.consumer_secret = os.getenv("NETSUITE_CONSUMER_SECRET")
            self.token_id = os.getenv("NETSUITE_TOKEN_ID")
            self.token_secret = os.getenv("NETSUITE_TOKEN_SECRET")
            self.restlet_url = os.getenv("URL_RESTLET")
            self.realm = os.getenv("REALM_ID")
        else:
            self.account_id = os.getenv("ACCOUNT_ID_SB")
            self.consumer_key = os.getenv("NETSUITE_CONSUMER_KEY_SB")
            self.consumer_secret = os.getenv("NETSUITE_CONSUMER_SECRET_SB")
            self.token_id = os.getenv("NETSUITE_TOKEN_ID_SB")
            self.token_secret = os.getenv("NETSUITE_TOKEN_SECRET_SB")
            self.restlet_url = os.getenv("URL_RESTLET_SB")
        # Format account ID for URL (e.g., 11615603_SB1 -> 11615603-sb1)
        self.url_account_id = self.account_id.lower().replace('_', '-').replace('sb', '-sb')
        self.base_url = f"https://{self.url_account_id}.suitetalk.api.netsuite.com/services/rest"
        self.realm = os.getenv("REALM_ID")

        # Initialize Auth
        try:
            from requests_oauthlib import OAuth1
            self.auth = OAuth1(
                #client_key=self.consumer_key,
                #client_secret=self.consumer_secret,
                #resource_owner_key=self.token_id,
                #resource_owner_secret=self.token_secret,
                #realm=self.realm,
                client_key="3ff9db30b4658b7be5fe32eacd6052c25818272c536fd4434151b02af0e1053c",
                client_secret="6fee669bd1c4bdbeea1a6709e8e73455f93ddf436a65647f98a3d71a6a6ce1ff",
                resource_owner_key="86d36eee18b861fa90bf4246a25652732974252aed3551647932fbca7667592b",
                resource_owner_secret="149648322f6d8c128b26468c37b6290f7e1c7428481cf0e8a733fa6d02913061",
                realm="11615603",
                signature_method='HMAC-SHA256'
            )
        except ImportError:
            self.auth = None
            print("Warning: requests_oauthlib not installed. NetSuite authentication will fail.")

    def execute_suiteql(self, query):
        if not self.auth:
            raise ImportError("requests_oauthlib is required for NetSuite authentication")

        url = f"{self.base_url}/query/v1/suiteql"
        
        headers = {
            "Prefer": "transient",
            "Content-Type": "application/json"
        }
        
        body = {
            "q": query
        }

        response = requests.post(url, auth=self.auth, headers=headers, json=body)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"NetSuite Error: {response.status_code} - {response.text}")

    def send_data(self, endpoint, data, method="POST"):
        """
        Send data to a specific NetSuite endpoint (Record API or RESTlet).
        endpoint: e.g. 'record/v1/journalEntry' or a RESTlet script url
        data: dict containing the payload
        """
        if not self.auth:
            raise ImportError("requests_oauthlib is required for NetSuite authentication")

        url = f"{self.base_url}/{endpoint}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if method.upper() == "POST":
            response = requests.post(url, auth=self.auth, headers=headers, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, auth=self.auth, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")

        if 200 <= response.status_code < 300:
            # 204 No Content is common for success in some APIs, generic 2xx check
            try:
                return response.json() if response.content else {"status": "success", "code": response.status_code}
            except:
                return {"status": "success", "code": response.status_code}
        else:
            raise Exception(f"NetSuite Error {response.status_code}: {response.text}")
    def restlet(self, data):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-NetSuite-Idempotency-Key": str(uuid.uuid4())
        }
        
        response = requests.post("https://11615603.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=940&deploy=1", auth=self.auth, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"NetSuite Error: {response.status_code} - {response.text}")