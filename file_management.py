# file_management.py
import streamlit as st
import os

def file_management_sidebar(assistant):
    st.title("File Management")

    if assistant:
        # File upload
        uploaded_file = st.file_uploader("Choose a file to upload", type=["txt", "pdf"])
        if uploaded_file is not None:
            if st.button("Upload"):
                if upload_file(assistant, uploaded_file):
                    st.rerun()

        # Display file list
        st.subheader("Uploaded Files")
        files = list_files(assistant)
        if isinstance(files, list):
            for file in files:
                col1, col2 = st.columns([3, 1])
                col1.write(f"{file.get('name', 'Unknown')}")
                if col2.button("Delete", key=file.get('id')):
                    if delete_file(assistant, file.get('id')):
                        st.success(f"Deleted {file.get('name', 'Unknown')}")
                        st.rerun()
        else:
            st.error(files)  # This will be the error message if listing failed
    else:
        st.error("Assistant not initialized. Unable to manage files.")

def list_files(assistant):
    try:
        return assistant.list_files()
    except Exception as e:
        return f"Error listing files: {str(e)}"

def upload_file(assistant, file):
    try:
        max_size = 200 * 1024 * 1024
        if file.size > max_size:
            st.error(f"File is too large. Maximum size is {max_size/1024/1024:.2f}MB. Your file is {file.size/1024/1024:.2f}MB.")
            return False

        with st.spinner("Uploading file..."):
            temp_file_path = f"temp_{file.name}"
            with open(temp_file_path, "wb") as f:
                f.write(file.getbuffer())
            response = assistant.upload_file(file_path=temp_file_path)
            os.remove(temp_file_path)
        st.success(f"File uploaded successfully: {response.get('name', 'Unknown')}")
        return True
    except Exception as e:
        st.error(f"Error uploading file: {str(e)}")
        return False

def delete_file(assistant, file_id):
    try:
        assistant.delete_file(file_id=file_id)
        return True
    except Exception as e:
        st.error(f"Error deleting file: {str(e)}")
        return False