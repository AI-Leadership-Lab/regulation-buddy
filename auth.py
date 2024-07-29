# auth.py
import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

def load_config():
    with open('config.yaml', 'r', encoding='utf-8') as file:
        return yaml.load(file, Loader=SafeLoader)

def save_config(config):
    with open('config.yaml', 'w', encoding='utf-8') as file:
        yaml.dump(config, file, default_flow_style=False)

def initialize_auth(config):
    return stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config['pre-authorized']
    )

def handle_authentication(authenticator):
    try:
        authenticator.login()
    except Exception as e:
        st.error(e)

    if st.session_state["authentication_status"]:
        return st.session_state["username"]
    elif st.session_state["authentication_status"] is False:
        st.error('Username/password is incorrect')
    elif st.session_state["authentication_status"] is None:
        st.warning('Please enter your username and password')
    
    return None

def handle_logout(authenticator):
    if st.session_state["authentication_status"]:
        if authenticator.logout('Logout', 'sidebar'):
            st.rerun()