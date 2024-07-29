# streamlit_app.py
import streamlit as st
from auth import load_config, save_config, initialize_auth, handle_authentication, handle_logout
from file_management import file_management_sidebar
from assistant import initialize_pinecone, get_assistant, chat_interface

def main():
    st.title("Regulations Buddy")

    # Load authentication configuration
    config = load_config()

    # Initialize authentication
    authenticator = initialize_auth(config)

    # Handle authentication
    username = handle_authentication(authenticator)

    if username:
        st.write(f'Welcome *{st.session_state["name"]}*')

        # Initialize Pinecone and get the assistant
        pinecone_instance = initialize_pinecone()
        assistant = get_assistant(pinecone_instance, config, username) if pinecone_instance else None

        # Main area
        if assistant:
            chat_interface(assistant, username)
        else:
            st.error("Assistant not initialized. Chat functionality is unavailable.")

        # Sidebar
        with st.sidebar:
            file_management_sidebar(assistant)
            handle_logout(authenticator)  # Logout button in sidebar
    
    # Saving config file
    save_config(config)

if __name__ == "__main__":
    main()