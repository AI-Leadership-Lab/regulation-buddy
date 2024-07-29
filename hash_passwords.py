# hash_passwords.py
import streamlit_authenticator as stauth
import yaml

def hash_passwords(config_path):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)

    for username, user_data in config['credentials']['usernames'].items():
        if 'password' in user_data:
            hashed_password = stauth.Hasher([user_data['password']]).generate()[0]
            user_data['password'] = hashed_password

    with open(config_path, 'w') as file:
        yaml.dump(config, file, default_flow_style=False)

    print("Passwords hashed and config file updated.")

if __name__ == "__main__":
    hash_passwords('config.yaml')