import os
import streamlit as st
from datetime import datetime
from llama_index.core.llms import ChatMessage
import logging
import time
import json
import re
from bs4 import BeautifulSoup
from llama_index.llms.ollama import Ollama
from dotenv import load_dotenv
from openai import AzureOpenAI
import utils.context_explorer as context_explorer

load_dotenv()
openai_key = os.getenv("OPENAIKEY")
azure_endpoint = "https://els-patientpass.openai.azure.com/"
gpt4o_model = "gpt-4o"
models = [
    gpt4o_model,
    "llama3.2:latest",
    "llama3.1:latest",
    "phi3.5:latest"
]
version = "0.2.0-halloween-demo"

logging.basicConfig(level=logging.INFO)

def stream_chat(messages):
    try:
        client = AzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_version="2024-02-01",
            api_key=openai_key
        )
        resp = client.chat.completions.create(
            model=gpt4o_model,
            messages=messages,
            stream=True
        )
        response = ""
        response_placeholder = st.empty()
        for chunk in resp:
            if len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                response += chunk.choices[0].delta.content
                response_placeholder.write(response)
        logging.info(f"Model: {gpt4o_model}, Messages: {messages}, Response: {response}")
        return response
    except Exception as e:
        logging.error(f"Error during streaming: {str(e)}")
        raise e

def stream_chat_ollama(messages):
    try:
        llm = Ollama(model=st.session_state.model, request_timeout=120.0)
        resp = llm.stream_chat(messages)
        response = ""
        response_placeholder = st.empty()
        for r in resp:
            response += r.delta
            response_placeholder.write(response)
        logging.info(f"Model: {st.session_state.model}, Messages: {messages}, Response: {response}")
        return response
    except Exception as e:
        logging.error(f"Error during streaming: {str(e)}")
        raise e

def intel_input_change():
    intel_url = st.session_state.intel_input_box
    logging.info(f"Intel: {intel_url}")
    confluence_page_id = context_explorer.extract_confluence_page_id(intel_url)
    if confluence_page_id:
        st.session_state.confluence_page_search = intel_url
        return
    else:
        text_content = context_explorer.extract_text_from_url(intel_url)
        append_intel([{"url": intel_url, "text": text_content}])
        st.session_state.intel_urls.append(intel_url)
        st.session_state.intel_input_box = ""

def append_intel(pages_with_texts):
    urls = ", ".join([page["url"] for page in pages_with_texts])
    st.session_state.real_messages.append({"role": "user", "content": f"I would like you to brief yourself on information from {urls}. When responding, make it clear where the information is coming from and use quotes from the source where necessary. If you understand, please respond with today's date."})
    st.session_state.real_messages.append({"role": "assistant", "content": f"I understand, and today's date is {"{:%B %d, %Y}".format(datetime.now())}."})
    for page in pages_with_texts:
        st.session_state.real_messages.append({"role": "user", "content": f"Information from {page["url"]}:\r\n\r\n{page["text"]}\r\n\r\nRetrieved on {datetime.now()}."})
    st.session_state.user_facing_messages.append({"role": "system", "content": f"(Contents of {urls} retrieved and stored in the conversation)"})

def show():
    logging.info("App started")

    if 'model' not in st.session_state:
        st.session_state.model = gpt4o_model

    if 'intel_urls' not in st.session_state:
        st.session_state.intel_urls = []

    if 'user_facing_messages' not in st.session_state:
        st.session_state.user_facing_messages = []

    if 'real_messages' not in st.session_state:
        st.session_state.real_messages = [{"role": "system", "content": f"You are an analyst who processes given information and makes inferences. Today's date is {"{:%B %d, %Y}".format(datetime.now())}."}]

    st.title("Comp Intel Exchange")

    subtitle = f"Version: '{version}'"

    st.code(subtitle)
    st.selectbox("Model", models, key="model")

    if st.session_state.urls_to_add:
        append_intel(st.session_state.urls_to_add)
        st.session_state.urls_to_add.clear()

    st.sidebar.text_input("Copy URLs of Intel Here", key="intel_input_box", on_change=intel_input_change)
    for intel_url in st.session_state.intel_urls:
        st.sidebar.write(intel_url)

    for message in st.session_state.user_facing_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if prompt := st.chat_input("Your question"):
        logging.info(f"User input: {prompt}")

        st.session_state.real_messages.append({"role": "user", "content": prompt})
        st.session_state.user_facing_messages.append({"role": "user", "content": prompt})
        st.write(prompt)

    if st.session_state.real_messages and st.session_state.real_messages[-1]["role"] != "assistant" and st.session_state.real_messages[-1]["role"] != "system":
        with st.chat_message("assistant"):
            start_time = time.time()
            logging.info("Generating response")

            with st.spinner("Writing..."):
                try:
                    messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in st.session_state.real_messages]
                    if st.session_state.model == gpt4o_model:
                        response_message = stream_chat(messages)
                    else:
                        response_message = stream_chat_ollama(messages)
                    duration = time.time() - start_time
                    st.session_state.real_messages.append({"role": "assistant", "content": response_message})
                    st.session_state.user_facing_messages.append({"role": "assistant", "content": response_message})
                    logging.info(f"Response: {response_message}, Duration: {duration:.2f} s")

                except Exception as e:
                    st.session_state.real_messages.append({"role": "assistant", "content": str(e)})
                    st.session_state.user_facing_messages.append({"role": "assistant", "content": str(e)})
                    st.error("An error occurred while generating the response.")
                    logging.error(f"Error: {str(e)}")
