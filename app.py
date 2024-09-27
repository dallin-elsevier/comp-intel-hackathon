import streamlit as st
from llama_index.core.llms import ChatMessage
import logging
import time
from llama_index.llms.ollama import Ollama

logging.basicConfig(level=logging.INFO)

if 'messages' not in st.session_state:
    st.session_state.messages = []

def stream_chat(model, messages):
    try:
        llm = Ollama(model=model, request_timeout=120.0)
        resp = llm.stream_chat(messages)
        response = ""
        response_placeholder = st.empty()
        for r in resp:
            response += r.delta
            response_placeholder.write(response)
        logging.info(f"Model: {model}, Messages: {messages}, Response: {response}")
        return response
    except Exception as e:
        logging.error(f"Error during streaming: {str(e)}")
        raise e

def intel_input_change():
    intel_prompt = st.session_state.intel_input_box
    logging.info(f"Intel: {intel_prompt}")
    st.session_state.messages.append({"role": "system", "content": f"Background Information:\r\n\r\n{intel_prompt}\r\n\r\n"})
    st.session_state.intel_input_box = ""

def main():
    st.title("Comp Intel Exchange")
    logging.info("App started")

    model = "llama3.2:latest"

    st.sidebar.text_input("Copy Intel Here", key="intel_input_box", on_change=intel_input_change)

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "system":
                st.write("(Memory Updated)")
                st.sidebar.write(message["content"])
            else:
                st.write(message["content"])

    if prompt := st.chat_input("Your question"):
        logging.info(f"User input: {prompt}")

        st.session_state.messages.append({"role": "user", "content": prompt})
        st.write(prompt)

        if st.session_state.messages[-1]["role"] != "assistant" and st.session_state.messages[-1]["role"] != "system":
            with st.chat_message("assistant"):
                start_time = time.time()
                logging.info("Generating response")

                with st.spinner("Writing..."):
                    try:
                        messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in st.session_state.messages]
                        response_message = stream_chat(model, messages)
                        duration = time.time() - start_time
                        st.session_state.messages.append({"role": "assistant", "content": response_message})
                        logging.info(f"Response: {response_message}, Duration: {duration:.2f} s")

                    except Exception as e:
                        st.session_state.messages.append({"role": "assistant", "content": str(e)})
                        st.error("An error occurred while generating the response.")
                        logging.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
