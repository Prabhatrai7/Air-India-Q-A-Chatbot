import os
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_core.prompts import PromptTemplate

st.set_page_config(
    page_title="PDF Q&A with Grok",
    page_icon="📄",
    layout="wide"
)
API_KEY = ""
os.environ["API_KEY"] = API_KEY

API_KEY = os.getenv("API_KEY") or st.secrets.get("API_KEY", "")

if not API_KEY:
    st.error("API_KEY not found. Please set it in environment variables or .streamlit/secrets.toml")
    st.stop()

PDF_FOLDER = "pdfs"
GLOB_PATTERN = "**/*.pdf"

prompt_template = """You are a helpful assistant answering questions based **only** on the provided context.
If the information is not in the context, say "I don't have enough information in the documents".

Context:
{context}

Question: {question}

Answer concisely, clearly and naturally:"""

PROMPT = PromptTemplate.from_template(prompt_template)

@st.cache_resource(show_spinner="Loading and processing PDFs...")
def load_documents():
    try:
        loader = DirectoryLoader(
            path=PDF_FOLDER,
            glob=GLOB_PATTERN,
            loader_cls=PyPDFLoader,
            show_progress=True,
            silent_errors=False
        )
        docs = loader.load()
        
        if not docs:
            st.warning(f"No PDF files were found in folder: '{PDF_FOLDER}'")
            return []
            
        total_pages = len(docs)
        st.success(f"Loaded **{total_pages}** pages from PDFs")
        return docs
        
    except Exception as e:
        st.error(f"Error loading documents:\n{str(e)}")
        return []

@st.cache_resource
def get_llm():
    return ChatOpenAI(
        model="tngtech/deepseek-r1t2-chimera:free", 
        api_key = API_KEY, 
        base_url="https://openrouter.ai/api/v1",
        temperature=0.15,
        max_tokens=2048,
        streaming=True
    )

def main():
    st.title("📄 Air India Chatbot")
    st.caption("Ask questions about Air India")

    documents = load_documents()

    if not documents:
        st.stop()

    context_text = "\n\n".join(doc.page_content for doc in documents)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if question := st.chat_input("Ask a question about the documents..."):
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        formatted_prompt = PROMPT.format(
            context=context_text,
            question=question
        )

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            try:
                llm = get_llm()

                for chunk in llm.stream(formatted_prompt):
                    if hasattr(chunk, "content"):
                        delta = chunk.content
                    else:
                        delta = str(chunk)
                        
                    full_response += delta
                    message_placeholder.markdown(full_response + "▌")

                message_placeholder.markdown(full_response)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response
                })

            except Exception as e:
                st.error(f"Error during generation:\n{str(e)}")

    if st.sidebar.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

if __name__ == "__main__":

    main()
