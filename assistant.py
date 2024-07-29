# assistant.py
import os
import streamlit as st
from pinecone import Pinecone
from pinecone_plugins.assistant.models.chat import Message
from database import save_conversation, get_conversation, get_all_conversations, create_new_conversation, rename_conversation, delete_conversation
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@st.cache_resource
def initialize_pinecone():
    api_key = get_api_key()
    if not api_key:
        st.error("Pinecone API key not found. Please set it in your environment variables or Streamlit secrets.")
        return None
    try:
        return Pinecone(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Pinecone: {e}")
        st.error(f"Failed to initialize Pinecone. Please check your API key and try again.")
        return None

def get_api_key():
    return os.environ.get("PINECONE_API_KEY") or st.secrets.get("PINECONE_API_KEY")

def get_assistant(pinecone_instance, config, username):
    try:
        assistant_name = config['credentials']['usernames'][username]['assistant']
        logger.info(f"Connecting to assistant: {assistant_name}")
        return pinecone_instance.assistant.describe_assistant(assistant_name)
    except Exception as e:
        logger.error(f"Error connecting to assistant: {e}")
        st.error(f"Error connecting to assistant. Please check your configuration and try again.")
        return None

def query_assistant(assistant, query, chat_history, stream=True):
    try:
        chat_context = [Message(content=m["content"], role=m["role"]) for m in chat_history]
        chat_context.append(Message(content=query, role="user"))
        logger.info(f"Sending query to assistant: {query}")
        return assistant.chat_completions(messages=chat_context, stream=stream)
    except Exception as e:
        logger.error(f"Error querying assistant: {str(e)}")
        return f"Error querying assistant: {str(e)}"

def get_or_create_initial_conversation(username):
    conversations = get_all_conversations(username)
    if conversations:
        return conversations[0]["conversation_id"]
    else:
        return create_new_conversation(username)

def cleanup_response(response):
    cleaned = re.sub(r'\n\d+\.\s*$', '', response, flags=re.MULTILINE)
    cleaned = cleaned.rstrip()
    last_line = cleaned.split('\n')[-1]
    if "what would you like to do" in last_line.lower() or "what do you want to do" in last_line.lower():
        cleaned = re.sub(r'\n\d+\.?\s*$', '', cleaned, flags=re.MULTILINE)
    return cleaned

def chat_interface(assistant, username):
    if assistant is None:
        st.error("Assistant not initialized. Please check your configuration and API key.")
        return

    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = get_or_create_initial_conversation(username)
    if "renaming_conversation" not in st.session_state:
        st.session_state.renaming_conversation = None
    if "deleting_conversation" not in st.session_state:
        st.session_state.deleting_conversation = None

    conversations = get_all_conversations(username)

    with st.sidebar:
        st.title("Conversations")
        if st.button("New Conversation"):
            new_id = create_new_conversation(username)
            st.session_state.current_conversation_id = new_id
            st.session_state.messages = []
            st.rerun()

        for conv in conversations:
            conv_id = conv["conversation_id"]
            conv_name = conv.get("name", f"Conversation {conv['created_at'].strftime('%Y-%m-%d %H:%M')}")
            
            col1, col2, col3 = st.columns([3, 1, 1])
            
            if col1.button(conv_name, key=f"conv_{conv_id}"):
                st.session_state.current_conversation_id = conv_id
                st.session_state.messages = get_conversation(username, conv_id)
                st.rerun()
            
            if col2.button("Rename", key=f"rename_{conv_id}"):
                st.session_state.renaming_conversation = conv_id
            
            if col3.button("Delete", key=f"delete_{conv_id}"):
                st.session_state.deleting_conversation = conv_id

        if st.session_state.renaming_conversation:
            handle_rename(username, conversations)

        if st.session_state.deleting_conversation:
            handle_delete(username, conversations)

    if "messages" not in st.session_state:
        st.session_state.messages = get_conversation(username, st.session_state.current_conversation_id)

    display_current_conversation(conversations)
    display_chat_messages()
    handle_chat_input(assistant, username)

def handle_rename(username, conversations):
    conv_to_rename = next((c for c in conversations if c["conversation_id"] == st.session_state.renaming_conversation), None)
    if conv_to_rename:
        new_name = st.text_input("New name", value=conv_to_rename.get("name", ""))
        col1, col2 = st.columns(2)
        if col1.button("Confirm Rename"):
            if rename_conversation(username, st.session_state.renaming_conversation, new_name):
                st.success("Conversation renamed successfully!")
                st.session_state.renaming_conversation = None
                st.rerun()
            else:
                st.error("Failed to rename conversation.")
        if col2.button("Cancel Rename"):
            st.session_state.renaming_conversation = None
            st.rerun()

def handle_delete(username, conversations):
    conv_to_delete = next((c for c in conversations if c["conversation_id"] == st.session_state.deleting_conversation), None)
    if conv_to_delete:
        st.warning(f"Are you sure you want to delete '{conv_to_delete.get('name', 'this conversation')}'?")
        col1, col2 = st.columns(2)
        if col1.button("Confirm Delete"):
            if delete_conversation(username, st.session_state.deleting_conversation):
                st.success("Conversation deleted successfully!")
                if st.session_state.current_conversation_id == st.session_state.deleting_conversation:
                    st.session_state.current_conversation_id = create_new_conversation(username)
                    st.session_state.messages = []
                st.session_state.deleting_conversation = None
                st.rerun()
            else:
                st.error("Failed to delete conversation.")
        if col2.button("Cancel Delete"):
            st.session_state.deleting_conversation = None
            st.rerun()

def display_current_conversation(conversations):
    current_conv = next((conv for conv in conversations if conv["conversation_id"] == st.session_state.current_conversation_id), None)
    if current_conv:
        st.header(current_conv.get("name", f"Conversation {current_conv['created_at'].strftime('%Y-%m-%d %H:%M')}"))

def display_chat_messages():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def handle_chat_input(assistant, username):
    if prompt := st.chat_input("What would you like to know about?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response = query_assistant(assistant, prompt, st.session_state.messages)
            
            if isinstance(response, str):  # Error occurred
                st.error(response)
                return

            message_placeholder = st.empty()
            full_response = ""
            
            try:
                if isinstance(response, dict):  # Non-streaming response
                    full_response = response['choices'][0]['message']['content']
                    message_placeholder.markdown(full_response)
                else:  # Streaming response
                    for chunk in response:
                        if chunk.choices:
                            content = chunk.choices[0].delta.content
                            if content:
                                full_response += content
                                cleaned_response = cleanup_response(full_response)
                                message_placeholder.markdown(cleaned_response + "▌")
            except Exception as e:
                logger.error(f"Error while processing response: {str(e)}")
                st.error("An error occurred while processing the response. Please try again.")
                return
            
            final_cleaned_response = cleanup_response(full_response)
            message_placeholder.markdown(final_cleaned_response)
        
        st.session_state.messages.append({"role": "assistant", "content": final_cleaned_response})
        save_conversation(username, st.session_state.current_conversation_id, st.session_state.messages)