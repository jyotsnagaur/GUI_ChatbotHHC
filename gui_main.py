import openai
import os
from dotenv import find_dotenv, load_dotenv
import time
import logging
from datetime import datetime
import streamlit as st


load_dotenv()
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Define the function to create new client
def initialize_openai_client(api_key):
    return openai.OpenAI(api_key=api_key)

def wait_for_run_completion(client,thread_id,run_id,interval=5):
    while True:
        try:
            run = st.session_state.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            if run.completed_at:
                elapsed_time = run.completed_at - run.created_at
                formatted_elapsed_time = time.strftime(
                    "%H:%M:%S", time.gmtime(elapsed_time)
                )
                st.write(f"Run completed in {formatted_elapsed_time}")
                logging.info(f"Run completed in {formatted_elapsed_time}")

                break
        except Exception as e:
            logging.error(f"An error occurred while retrieving the run: {e}")
            break
        logging.info("Waiting for run to complete...")
        time.sleep(interval)

# Define function for pretty print
def pretty_print(messages):
    responses = []
    for m in messages:
        if m.role == "assistant":
            responses.append(m.content[0].text.value)
    return "\n".join(responses)

# Define the function to process messages with citations
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

# Streamlit UI for sidebar configuration
st.sidebar.title("Sign in")

# Sidebar for selecting the assistant
assistant_option = st.sidebar.selectbox(
    "Welcome to HHC Assistant.\nPlease choose your mode based on your role.",
    ("Staff", "Manager")
)

# assistant_id_1 = asst_6THbXlSoxRLfwMc6ixCJyD8a
# assistant_id_2 = asst_v9WZaCUsP4sOmoY1ej59czTT
def main():
# ========================== Staff ==============================================================
    if assistant_option == "Staff":
        st.title("HHC Staff Assistant")

        # Description
        st.markdown("""
            This assistant is your go-to resource for policies insights and advice.
            Simply enter your query below and let the assistant guide you with actionable insights.
        """)
        st.session_state.client = openai.OpenAI()
        if 'client' not in st.session_state:

            # Initialize the client
            st.session_state.client = openai.OpenAI()

            # Upload file
            st.session_state.uploaded_file = st.session_state.client.files.create(
                file=open("./all_pdfs_text.txt", 'rb'),
                purpose='assistants',
            )

            # Create assistant
            st.session_state.assistant = st.session_state.client.beta.assistants.create(
                name="HHC Assistant Bot",
                instructions="""You are a AI Assistant that answers any queries related to aged care policies and incidents as per the data provided.Look inside the data first. If the answer is not available then search the answer from the preset conditions. Start your answers with a warm greeting""",
                # instructions="""You are a helpful chat bot that will answer any question related to home care  policies to the staff who work on Hope Holistic Care (HHC) based in Australia. You  have to start the conversation before the staff by greeting them and ask how can you help them.  After the staff telling you their question, you summarise the question, and answer them by using information on the policies. Keep the answer as short as possible but still provide enough necessary information. If there is no information regarded to their question, you tell them sorry you do not have that information, tell them please see your manager for further assistant. After answer the question, ask them do they have other questions. If the staff say no, you say good bye to them.""",
                model="gpt-3.5-turbo-0125",
                tools=[{"type": "retrieval"}],
                file_ids=[st.session_state.uploaded_file.id]
            )

        #Create a thread
        st.session_state.thread = st.session_state.client.beta.threads.create()
    
        if "start_chat" not in st.session_state:
            st.session_state.start_chat = False
        if "thread_id" not in st.session_state:
            st.session_state.thread_id = None

        # Button to initiate the chat session
        if st.sidebar.button("Start Chatting..."):
            st.session_state.start_chat = True
        
        # Check sessions
        if st.session_state.start_chat:
            if "messages" not in st.session_state:
                st.session_state.messages = []

            # Show existing messages if any...
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # chat input for the user
            if prompt := st.chat_input("Hello. I am HHC Assistant. How can I help you?"):
                
                # Add user message to the state and display on the screen
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                # add the user's message to the existing thread
                st.session_state.client.beta.threads.messages.create(
                    thread_id=st.session_state.thread.id, role="user", content=prompt
                )

                # Create a run
                run = st.session_state.client.beta.threads.runs.create(
                    thread_id=st.session_state.thread.id,
                    assistant_id="asst_v9WZaCUsP4sOmoY1ej59czTT",
                    instructions="""If the user using other languages to ask, please answer by that language as well."""
                )

                # Show a spinner while the assistant is thinking...
                with st.spinner("Wait... Generating response..."):
                    while run.status != "completed":
                        time.sleep(1)
                        run = st.session_state.client.beta.threads.runs.retrieve(
                            thread_id=st.session_state.thread.id, run_id=run.id
                        )
                    # Retrieve messages added by the assistant
                    messages = st.session_state.client.beta.threads.messages.list(
                        thread_id=st.session_state.thread.id
                    )
                    # Process and display assis messages
                    assistant_messages_for_run = [
                        message
                        for message in messages
                        if message.run_id == run.id and message.role == "assistant"
                    ]

                    for message in assistant_messages_for_run:
                        full_response = process_message_with_citations(message=message)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": full_response}
                        )
                        with st.chat_message("assistant"):
                            st.markdown(full_response, unsafe_allow_html=True)
                    
                # # # === Run ===
                wait_for_run_completion(client = st.session_state.client, thread_id=st.session_state.thread.id, run_id = run.id)

            
            # # # === Steps --- Logs ===
            # run_steps = st.session_state.client.beta.threads.runs.steps.list(
            #     thread_id=st.session_state.thread.id,
            #     run_id=run.id,
            # )
            # st.write(f"Steps---> {run_steps.data[0]}")
# ==== Manager ====  
                
    elif assistant_option == "Manager":
        # Initialize all the session
        if "file_id_list" not in st.session_state:
            st.session_state.file_id_list = []

        if "start_chat" not in st.session_state:
            st.session_state.start_chat = False

        if "thread_id" not in st.session_state:
            st.session_state.thread_id = None

        # ==== Function definitions etc =====
        def upload_to_openai(filepath):
            with open(filepath, "rb") as file:
                response = client.files.create(file=file.read(), purpose="assistants")
            return response.id

        # === Sidebar - where users can upload files
        file_uploaded = st.sidebar.file_uploader(
            "Upload a file to be transformed into embeddings", key="file_upload"
        )

        entered_api_key = st.sidebar.text_input("Enter your OpenAI API key", type="password")

        # Check if an API key is entered, then initialize the OpenAI client
        client = None
        if entered_api_key:
            with st.spinner('Initializing OpenAI Client...'):
                client = initialize_openai_client(entered_api_key)

        # Upload file button - store the file ID
        if st.sidebar.button("Upload File"):
            if file_uploaded:
                with open(f"{file_uploaded.name}", "wb") as f:
                    f.write(file_uploaded.getbuffer())
                another_file_id = upload_to_openai(f"{file_uploaded.name}")
                st.session_state.file_id_list.append(another_file_id)
                st.sidebar.write(f"File ID:: {another_file_id}")

        # Display those file ids
        if st.session_state.file_id_list:
            st.sidebar.write("Uploaded File IDs:")
            for file_id in st.session_state.file_id_list:
                st.sidebar.write(file_id)
                # Associate each file id with the current assistant
                assistant_file = client.beta.assistants.files.create(
                    assistant_id="asst_Rb4aCslKXCN1USPs3hfHtQVW", file_id=file_id
                    )

        # Button to initiate the chat session
        if st.sidebar.button("Start Chatting..."):
            if st.session_state.file_id_list:
                st.session_state.start_chat = True

                # Create a new thread for this chat session
                chat_thread = client.beta.threads.create()
                st.session_state.thread_id = chat_thread.id
                st.write("Thread ID:", chat_thread.id)
            else:
                st.sidebar.warning(
                    "No files found. Please upload at least one file to get started."
                )

        # the main interface ...
        st.title("HHC Manager Assitant")
        st.write("This chatbot is crafted to assist managers in testing new policies seamlessly alongside the chatbots already in use by staff. To initiate this chatbot, managers simply need access to an OpenAI account containing the assistant_id for this bot. To begin the conversation, kindly upload a PDF document outlining the policy and provide your OpenAI API key.")

        # Check sessions
        if st.session_state.start_chat:
            if "openai_model" not in st.session_state:
                st.session_state.openai_model = "gpt-4-1106-preview"
            if "messages" not in st.session_state:
                st.session_state.messages = []

            # Show existing messages if any...
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # chat input for the user
            if prompt := st.chat_input("Hello. I am HHC Assistant. How can I help you?"):
                # Add user message to the state and display on the screen
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                # add the user's message to the existing thread
                client.beta.threads.messages.create(
                    thread_id=st.session_state.thread.id, role="user", content=prompt
                )

                # Create a run with additional instructions
                run = client.beta.threads.runs.create(
                    thread_id=st.session_state.thread.id,
                    assistant_id="asst_Rb4aCslKXCN1USPs3hfHtQVW",
                    instructions="""If the user using other languages to ask, please answer by that language as well."""
                )

                # Show a spinner while the assistant is thinking...
                with st.spinner("Wait... Generating response..."):
                    while run.status != "completed":
                        time.sleep(1)
                        run = client.beta.threads.runs.retrieve(
                            thread_id=st.session_state.thread.id, run_id=run.id
                        )
                    # Retrieve messages added by the assistant
                    messages = client.beta.threads.messages.list(
                        thread_id=st.session_state.thread.id
                    )
                    # Process and display assis messages
                    assistant_messages_for_run = [
                        message
                        for message in messages
                        if message.run_id == run.id and message.role == "assistant"
                    ]

                    for message in assistant_messages_for_run:
                        full_response = process_message_with_citations(message=message)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": full_response}
                        )
                        with st.chat_message("assistant"):
                            st.markdown(full_response, unsafe_allow_html=True)

            else:
                # Promopt users to start chat
                st.write(
                    "Please upload at least a file to get started by clicking on the 'Start Chat' button"
                )
if __name__ == "__main__":
        main()