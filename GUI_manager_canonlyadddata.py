import streamlit as st
import openai
import os
from datetime import datetime
import time
import logging

# Initialize OpenAI API key from environment variable
openai.api_key = os.environ.get('API KEY HERE')

# Function to create a new OpenAI client
def initialize_openai_client(api_key):
    return openai.OpenAI(api_key=api_key)

# Function to wait for run completion
def wait_for_run_completion(client, thread_id, run_id, interval=5):
    while True:
        try:
            run = st.session_state.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            if run.completed_at:
                elapsed_time = run.completed_at - run.created_at
                formatted_elapsed_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
                st.write(f"Run completed in {formatted_elapsed_time}")
                logging.info(f"Run completed in {formatted_elapsed_time}")
                break
        except Exception as e:
            logging.error(f"An error occurred while retrieving the run: {e}")
            break
        logging.info("Waiting for run to complete...")
        time.sleep(interval)

# Function to process messages with citations
def process_message_with_citations(message):
    """Extract content and annotations from the message and format citations as footnotes."""
    message_content = message.content[0].text
    annotations = (
        message_content.annotations if hasattr(message_content, "annotations") else []
    )
    citations = []

    # Iterate over the annotations and add footnotes
    for index, annotation in enumerate(annotations):
        # Replace the text with a footnote
        message_content.value = message_content.value.replace(
            annotation.text, f" [{index + 1}]"
        )

        # Gather citations based on annotation attributes
        if file_citation := getattr(annotation, "file_citation", None):
            # Retrieve the cited file details (dummy response here since we can't call OpenAI)
            cited_file = {
                "filename": "all_pdfs_text.txt"
            }  # This should be replaced with actual file retrieval
            citations.append(
                f'[{index + 1}] {file_citation.quote} from {cited_file["filename"]}'
            )
        elif file_path := getattr(annotation, "file_path", None):
            # Placeholder for file download citation
            cited_file = {
                "filename": "all_pdfs_text.txt"
            }  # TODO: This should be replaced with actual file retrieval
            citations.append(
                f'[{index + 1}] Click [here](#) to download {cited_file["filename"]}'
            )  # The download link should be replaced with the actual download path

    # Add footnotes to the end of the message content
    full_response = message_content.value + "\n\n" + "\n".join(citations)
    return full_response

# Function to upload a file to OpenAI
def upload_to_openai(filepath):
    with open(filepath, "rb") as file:
        response = st.session_state.client.files.create(file=file.read(), purpose="assistants")
    return response.id

# Main function for the Streamlit app
def main():
    st.sidebar.title("Sign in")

    # Sidebar for selecting the assistant
    assistant_option = st.sidebar.selectbox(
        "Welcome to HHC Assistant.\nPlease choose your mode based on your role.",
        ("Staff", "Manager")
    )

    if assistant_option == "Manager":
        # Initialize session state variables
        if "file_id_list" not in st.session_state:
            st.session_state.file_id_list = []
        if "start_chat" not in st.session_state:
            st.session_state.start_chat = False
        if "thread_id" not in st.session_state:
            st.session_state.thread_id = None

        # Sidebar for file upload
        st.sidebar.title("Upload Data")
        file_uploaded = st.sidebar.file_uploader("Upload a file to be transformed into embeddings", key="file_upload")

        # Initialize the OpenAI client using the environment variable API key
        st.session_state.client = initialize_openai_client(openai.api_key)

        # Button to upload file and store the file ID
        if st.sidebar.button("Upload File"):
            if file_uploaded:
                with open(f"{file_uploaded.name}", "wb") as f:
                    f.write(file_uploaded.getbuffer())
                another_file_id = upload_to_openai(f"{file_uploaded.name}")
                st.session_state.file_id_list.append(another_file_id)
                st.sidebar.write(f"File ID: {another_file_id}")

        # Display uploaded file IDs
        if st.session_state.file_id_list:
            st.sidebar.write("Uploaded File IDs:")
            for file_id in st.session_state.file_id_list:
                st.sidebar.write(file_id)
                # Associate each file ID with the current assistant
                assistant_file = st.session_state.client.beta.assistants.files.create(
                    assistant_id="asst_Rb4aCslKXCN1USPs3hfHtQVW", file_id=file_id
                )

        # Button to initiate the chat session
        if st.sidebar.button("Start Chatting..."):
            if st.session_state.file_id_list:
                st.session_state.start_chat = True
                # Create a new thread for this chat session
                chat_thread = st.session_state.client.beta.threads.create()
                st.session_state.thread_id = chat_thread.id
                st.write("Thread ID:", chat_thread.id)
            else:
                st.sidebar.warning("No files found. Please upload at least one file to get started.")

        # Main interface for the Manager Assistant
        st.title("HHC Manager Assistant")
        st.write("This chatbot is crafted to assist managers in testing new policies seamlessly alongside the chatbots already in use by staff. To initiate this chatbot, managers simply need access to an OpenAI account containing the assistant_id for this bot. To begin the conversation, kindly upload a PDF document outlining the policy and provide your OpenAI API key.")

        # Check session state and show existing messages if any
        if st.session_state.start_chat:
            if "openai_model" not in st.session_state:
                st.session_state.openai_model = "gpt-4-1106-preview"
            if "messages" not in st.session_state:
                st.session_state.messages = []

            # Show existing messages
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Chat input for the user
            if prompt := st.chat_input("Hello. I am HHC Assistant. How can I help you?"):
                # Add user message to the state and display on the screen
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                # Add the user's message to the existing thread
                st.session_state.client.beta.threads.messages.create(
                    thread_id=st.session_state.thread_id, role="user", content=prompt
                )

                # Create a run with additional instructions
                run = st.session_state.client.beta.threads.runs.create(
                    thread_id=st.session_state.thread_id,
                    assistant_id="asst_Rb4aCslKXCN1USPs3hfHtQVW",
                    instructions="If the user is using another language to ask, please answer in that language as well."
                )

                # Show a spinner while the assistant is thinking
                with st.spinner("Wait... Generating response..."):
                    while run.status != "completed":
                        time.sleep(1)
                        run = st.session_state.client.beta.threads.runs.retrieve(
                            thread_id=st.session_state.thread_id, run_id=run.id
                        )

                    # Retrieve messages added by the assistant
                    messages = st.session_state.client.beta.threads.messages.list(
                        thread_id=st.session_state.thread_id
                    )

                    # Process and display assistant messages
                    assistant_messages_for_run = [
                        message for message in messages if message.run_id == run.id and message.role == "assistant"
                    ]

                    for message in assistant_messages_for_run:
                        full_response = process_message_with_citations(message=message)
                        st.session_state.messages.append({"role": "assistant", "content": full_response})
                        with st.chat_message("assistant"):
                            st.markdown(full_response, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
