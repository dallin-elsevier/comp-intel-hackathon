import os
import streamlit as st
import requests
from functools import lru_cache
from dotenv import load_dotenv
import logging
import utils.context_explorer as context_explorer
import uuid
import pages.chat as chat

load_dotenv()
email = os.getenv("EMAIL")
confluence_token = os.getenv("CONFLUENCE_TOKEN")

logging.basicConfig(level=logging.INFO)

# Stub for context_explorer module
def get_url_context(url):
    # Fake context data; replace with actual calls to context_explorer
    return {"title": f"Title for {url}", "text_preview": f"Preview of content for {url}"}

# Memoized function to check for domain
@lru_cache(maxsize=128)
def check_domain(url, domain):
    return domain in url

# Function to initialize URLs with unique IDs and child structure
def initialize_url(url, parent_id=None):
    unique_id = str(uuid.uuid4())
    context = get_url_context(url)
    return {
        "id": unique_id,
        "url": url,
        "title": context.get("title"),
        "text_preview": context.get("text_preview"),
        "parent_id": parent_id,
        "children": []
    }

# Initialize session state if needed
if 'url_structure' not in st.session_state:
    # Example initial structure
    st.session_state['url_structure'] = [
        initialize_url("https://example.com"),
        initialize_url("https://example.com/notfound"),
        initialize_url("https://anotherdomain.com")
    ]

# Recursive function to display URLs and handle nesting
def display_url_structure(url_structure, level=1, domain="example.com"):
    checked_urls = []
    for item in url_structure:
        indentCol, col1, col2, col3, col4 = st.columns([level*3, 1, 8, 2, 2])

        with col1:
            # Checkbox for each URL
            checked = st.checkbox("", value=True, key=f"check_{item['id']}")
            if checked:
                checked_urls.append(item)  # Append the full item for final output

        with col2:
            st.markdown(f"**{item['title'] or item['url']}**")
            if item["text_preview"]:
                st.markdown(f"{item['text_preview']}")

            # Editable URL input
            edited_url = st.text_input("Edit URL", value=item["url"], key=f"edit_{item['id']}")
            if edited_url != item["url"]:
                # Re-fetch context data if URL is modified
                context = get_url_context(edited_url)
                item.update({
                    "url": edited_url,
                    "title": context.get("title"),
                    "text_preview": context.get("text_preview")
                })

        with col3:
            # Show expansion icon if it matches the domain and hasn't been expanded
            if check_domain(item["url"], domain) and "expanded" not in item:
                if st.button("➕", key=f"expand_{item['id']}"):
                    # Add child URLs (stubs here; replace with actual logic)
                    item["children"].append(initialize_url(f"{item['url']}/subpage1", parent_id=item["id"]))
                    item["children"].append(initialize_url(f"{item['url']}/subpage2", parent_id=item["id"]))
                    item["expanded"] = True
            elif "expanded" in item:
                st.write("✔️")  # Indicate already expanded

        with col4:
            # Optional: show edit icon if necessary (handled via text input above)
            pass

        # Display child URLs recursively
        if "children" in item:
            checked_urls.extend(display_url_structure(item["children"], level + 1, domain))

        # Horizontal line between entries
        st.markdown("<hr>", unsafe_allow_html=True)

    return checked_urls

# Main app function
def show():
    st.title("Nested URL Checker with Context")

    # Input for domain to match
    domain_to_match = st.text_input("Domain to match", "example.com")

    st.write("### URLs:")
    checked_urls = display_url_structure(st.session_state['url_structure'], domain=domain_to_match)

    # Final list of checked URLs based on their unique IDs
    st.session_state['final_checked_urls'] = checked_urls

    st.write("### Final Checked URLs")
    for item in st.session_state['final_checked_urls']:
        st.write(f"{item['title'] or item['url']} - {item['url']}")

    # Button to simulate returning final checked list
    if st.button("Return Final List"):
        st.write("Checked URLs:", [{"id": item["id"], "url": item["url"]} for item in st.session_state['final_checked_urls']])
