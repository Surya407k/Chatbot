from boto3.session import Session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
import json
import os
from requests import request
import base64
import io
import sys
import InvokeAgent as agenthelper
import streamlit as st
import pandas as pd
from PIL import Image, ImageOps, ImageDraw
import requests

# Constants
agentId = "MY8SXCS91N"  # INPUT YOUR AGENT ID HERE
agentAliasId = "MTGL815AGD"  # Hits draft alias, set to a specific alias id for a deployed version
theRegion = "us-west-2"
os.environ["AWS_REGION"] = theRegion

# Streamlit page configuration
st.set_page_config(page_title="Sciphics Technology Private Limited", page_icon=":robot_face:", layout="wide")

# Function to crop image into a circle
def crop_to_circle(image):
    mask = Image.new('L', image.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0) + image.size, fill=255)
    result = ImageOps.fit(image, mask.size, centering=(0.5, 0.5))
    result.putalpha(mask)
    return result

# Title
st.title("Sciphics Technology Private Limited")

# Display a text box for input
prompt = st.text_input("Please enter your query?", max_chars=2000)
prompt = prompt.strip()

# Display a primary button for submission
submit_button = st.button("Submit", type="primary")

# Display a button to end the session
end_session_button = st.button("End Session")

# Sidebar for user input
st.sidebar.title("Trace Data")

def filter_trace_data(trace_data, query):
    if query:
        # Filter lines that contain the query
        return "\n".join([line for line in trace_data.split('\n') if query.lower() in line.lower()])
    return trace_data

# Session State Management
if 'history' not in st.session_state:
    st.session_state['history'] = []

# Function to parse and format response
def format_response(response_body):
    try:
        # Try to load the response as JSON
        data = json.loads(response_body)
        # If it's a list, convert it to a DataFrame for better visualization
        if isinstance(data, list):
            return pd.DataFrame(data)
        else:
            return response_body
    except json.JSONDecodeError:
        # If response is not JSON, return as is
        return response_body

# Handling user input and responses
if submit_button and prompt:
    event = {
        "sessionId": "MYSESSION",
        "question": prompt
    }
    response = agenthelper.lambda_handler(event, None)

    try:
        # Parse the JSON string
        if response and 'body' in response and response['body']:
            response_data = json.loads(response['body'])
            print("TRACE & RESPONSE DATA -> ", response_data)
        else:
            print("Invalid or empty response received")
    except json.JSONDecodeError as e:
        print("JSON decoding error:", e)
        response_data = None

    try:
        # Extract the response and trace data
        all_data = format_response(response_data['response'])
        the_response = response_data['trace_data']
    except:
        all_data = "..."
        the_response = "Apologies, but an error occurred. Please rerun the application"

    # Use trace_data and formatted_response as needed
    st.sidebar.text_area("", value=all_data, height=300)
    st.session_state['history'].append({"question": prompt, "answer": the_response})
    st.session_state['trace_data'] = the_response

if end_session_button:
    st.session_state['history'].append({"question": "Session Ended", "answer": "Thank you for using AnyCompany Support Agent!"})
    event = {
        "sessionId": "MYSESSION",
        "question": "placeholder to end session",
        "endSession": True
    }
    agenthelper.lambda_handler(event, None)
    st.session_state['history'].clear()

# Display conversation history
st.write("## Conversation History")

# Load images outside the loop to optimize performance
human_image_url = "https://www.cryptopolitan.com/wp-content/uploads/20"

# AWS Code and Functions
def sigv4_request(
    url,
    method='GET',
    body=None,
    params=None,
    headers=None,
    service='execute-api',
    region=os.environ['AWS_REGION'],
    credentials=Session().get_credentials().get_frozen_credentials()
):
    """Sends an HTTP request signed with SigV4
    Args:
    url: The request URL (e.g. 'https://www.example.com').
    method: The request method (e.g. 'GET', 'POST', 'PUT', 'DELETE'). Defaults to 'GET'.
    body: The request body (e.g. json.dumps({ 'foo': 'bar' })). Defaults to None.
    params: The request query params (e.g. { 'foo': 'bar' }). Defaults to None.
    headers: The request headers (e.g. { 'content-type': 'application/json' }). Defaults to None.
    service: The AWS service name. Defaults to 'execute-api'.
    region: The AWS region id. Defaults to the env var 'AWS_REGION'.
    credentials: The AWS credentials. Defaults to the current boto3 session's credentials.
    Returns:
     The HTTP response
    """

    # sign request
    req = AWSRequest(
        method=method,
        url=url,
        data=body,
        params=params,
        headers=headers
    )
    SigV4Auth(credentials, service, region).add_auth(req)
    req = req.prepare()

    # send request
    return request(
        method=req.method,
        url=req.url,
        headers=req.headers,
        data=req.body
    )


def askQuestion(question, url, endSession=False):
    myobj = {
        "inputText": question,
        "enableTrace": True,
        "endSession": endSession
    }

    # send request
    response = sigv4_request(
        url,
        method='POST',
        service='bedrock',
        headers={
            'content-type': 'application/json',
            'accept': 'application/json',
        },
        region=theRegion,
        body=json.dumps(myobj)
    )

    return decode_response(response)


def decode_response(response):
    # Create a StringIO object to capture print statements
    captured_output = io.StringIO()
    sys.stdout = captured_output

    # Your existing logic
    string = ""
    for line in response.iter_content():
        try:
            string += line.decode(encoding='utf-8')
        except:
            continue

    print("Decoded response", string)
    split_response = string.split(":message-type")
    print(f"Split Response: {split_response}")
    print(f"length of split: {len(split_response)}")

    for idx in range(len(split_response)):
        if "bytes" in split_response[idx]:
            #print(f"Bytes found index {idx}")
            encoded_last_response = split_response[idx].split("\"")[3]
            decoded = base64.b64decode(encoded_last_response)
            final_response = decoded.decode('utf-8')
            print(final_response)
        else:
            print(f"no bytes at index {idx}")
            print(split_response[idx])

    last_response = split_response[-1]
    print(f"Lst Response: {last_response}")
    if "bytes" in last_response:
        print("Bytes in last response")
        encoded_last_response = last_response.split("\"")[3]
        decoded = base64.b64decode(encoded_last_response)
        final_response = decoded.decode('utf-8')
    else:
        print("no bytes in last response")
        part1 = string[string.find('finalResponse')+len('finalResponse":'):]
        part2 = part1[:part1.find('"}')+2]
        final_response = json.loads(part2)['text']

    final_response = final_response.replace("\"", "")
    final_response = final_response.replace("{input:{value:", "")
    final_response = final_response.replace(",source:null}}", "")
    llm_response = final_response

    # Restore original stdout
    sys.stdout = sys.__stdout__

    # Get the string from captured output
    captured_string = captured_output.getvalue()

    # Return both the captured output and the final response
    return captured_string, llm_response


def lambda_handler(event, context):

    sessionId = event["sessionId"]
    question = event["question"]
    endSession = False

    print(f"Session: {sessionId} asked question: {question}")

    try:
        if (event["endSession"] == "true"):
            endSession = True
    except:
        endSession = False

    url = f'https://bedrock-agent-runtime.{theRegion}.amazonaws.com/agents/{agentId}/agentAliases/{agentAliasId}/sessions/{sessionId}/text'


    try:
        response, trace_data = askQuestion(question, url, endSession)
        return {
            "status_code": 200,
            "body": json.dumps({"response": response, "trace_data": trace_data})
        }
    except Exception as e:
        return {
            "status_code": 500,
            "body": json.dumps({"error": str(e)})
        }

# Main function
if __name__ == "__main__":
    lambda_handler({"sessionId": "test_session_id", "question": "test_question"}, None)
