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
import streamlit as st
import pandas as pd
from PIL import Image, ImageOps, ImageDraw

# AWS Configuration
agentId = "MY8SXCS91N"  # INPUT YOUR AGENT ID HERE
agentAliasId = "MTGL815AGD"  # Hits draft alias, set to a specific alias id for a deployed version
theRegion = "us-west-2"
os.environ["AWS_REGION"] = theRegion
region = os.environ.get("AWS_REGION")

# Streamlit Configuration
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

# AWS Functions
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
    """Sends an HTTP request signed with SigV4"""
    req = AWSRequest(
        method=method,
        url=url,
        data=body,
        params=params,
        headers=headers
    )
    SigV4Auth(credentials, service, region).add_auth(req)
    req = req.prepare()

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
    string = ""
    for line in response.iter_content():
        try:
            string += line.decode(encoding='utf-8')
        except:
            continue

    split_response = string.split(":message-type")

    for idx in range(len(split_response)):
        if "bytes" in split_response[idx]:
            encoded_last_response = split_response[idx].split("\"")[3]
            decoded = base64.b64decode(encoded_last_response)
            final_response = decoded.decode('utf-8')
        else:
            split_response[idx]

    last_response = split_response[-1]
    if "bytes" in last_response:
        encoded_last_response = last_response.split("\"")[3]
        decoded = base64.b64decode(encoded_last_response)
        final_response = decoded.decode('utf-8')
    else:
        part1 = string[string.find('finalResponse')+len('finalResponse":'):] 
        part2 = part1[:part1.find('"}')+2]
        final_response = json.loads(part2)['text']

    final_response = final_response.replace("\"", "")
    final_response = final_response.replace("{input:{value:", "")
    final_response = final_response.replace(",source:null}}", "")
    llm_response = final_response

    return llm_response

# Handling user input and responses
if submit_button and prompt:
    event = {
        "sessionId": "MYSESSION",
        "question": prompt
    }
    response = askQuestion(prompt, url, endSession)

    all_data = response  # Assuming response is formatted as needed
    the_response = response  # Assuming response is formatted as needed

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

python_icon = "🐍"
human_image = Image.open('images/human_face.png')
robot_image = Image.open('images/robot_face.jpg')
circular_human_image = crop_to_circle(human_image)
circular_robot_image = crop_to_circle(robot_image)

for index, chat in enumerate(reversed(st.session_state['history'])):
    col1_q, col2_q = st.columns([2, 10])
    with col1_q:
        st.image(circular_human_image, width=125, caption=python_icon)
    with col2_q:
        st.text_area("Q:", value=chat["question"], height=50, key=f"question_{index}", disabled=True)

    col1_a, col2_a = st.columns([2, 10])
    if isinstance(chat["answer"], pd.DataFrame):
        with col1_a:
            st.image(circular_robot_image, width=100, caption=python_icon)
        with col2_a:
            st.dataframe(chat["answer"], key=f"answer_df_{index}")
    else:
        with col1_a:
            st.image(circular_robot_image, width=150, caption=python_icon)
        with col2_a:
            st.text_area("A:", value=chat["answer"], height=100, key=f"answer_{index}")
