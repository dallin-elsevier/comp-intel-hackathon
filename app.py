import streamlit as st
from llama_index.core.llms import ChatMessage
import logging
import pages.chat as chat
import importlib
import pages.intel_gathering as intel_gathering

importlib.reload(chat)
importlib.reload(intel_gathering)
logging.basicConfig(level=logging.INFO)

def main():
    logging.info("App started")

    if 'confluence_page_search' not in st.session_state:
        st.session_state.confluence_page_search = None

    if 'urls_to_add' not in st.session_state:
        st.session_state.urls_to_add = set([])

    if st.session_state.confluence_page_search != None:
        intel_gathering.show()
    else:
        chat.show()

if __name__ == "__main__":
    main()
