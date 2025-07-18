import streamlit as st
import asyncio
import os
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from data_preprocessor import clean_and_structure, json_to_documents
from code360 import main as fetch_interview_data
from prompt import get_prompt
from pdfgen import pdfgenerator  # Must return BytesIO or bytes PDF

# 🔐 Setup API key
os.environ["GOOGLE_API_KEY"] = "AIzaSyAfNUg3nn1UaW1uzjXypquW2RJfXreKkrU"

# 🧠 Ensure event loop exists
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# 🧠 Cached LLM
@st.cache_resource
def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.3,
        max_tokens=None,
        timeout=None,
        max_retries=2
    )

# 🧠 Cached embedding model
@st.cache_resource
def get_embeddings():
    return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-exp-03-07")

# 📦 Vectorstore + raw data loader
@st.cache_resource(show_spinner="Fetching and embedding interview data...")
def load_vectorstore(company: str, role: str, pages: int):
    df = fetch_interview_data(company, role, pages)
    raw_text = df['description'].str.cat(sep=' ')
    structured = clean_and_structure(raw_text)
    chunks = json_to_documents(structured)
    docs = [Document(page_content=chunk) for chunk in chunks]
    embeddings = get_embeddings()
    vectorstore = FAISS.from_documents(docs, embeddings)
    return vectorstore, df, structured

# 🎯 Page UI
st.title("🔍 RAG Q&A Chatbot for Interview Insights")

company = st.text_input("Enter Company Name", "Microsoft")
role = st.text_input("Enter Role", "SDE-2")
pages = st.number_input("Number of Pages to Scrape", min_value=1, max_value=10, value=1)

# 🧠 Session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "qa_chain" not in st.session_state:
    st.session_state.qa_chain = None

# 🚀 Load VectorStore + Build QA Chain
if st.button("Load & Build Chatbot"):
    with st.spinner("Working...",show_time=True):
        vs, df, structured = load_vectorstore(company, role, pages)
        st.session_state.structured = structured

        custom_prompt = get_prompt()
        st.session_state.qa_chain = ConversationalRetrievalChain.from_llm(
            llm=get_llm(),
            retriever=vs.as_retriever(search_kwargs={"k": 5}),
            return_source_documents=True,
            combine_docs_chain_kwargs={"prompt": custom_prompt}
        )
        st.success(f"Chatbot ready with {len(df)} interview experiences ✅")

# 💬 Chat Interface
if st.session_state.qa_chain:
    if prompt := st.chat_input("Ask a question"):
        if prompt.lower().strip() in ["exit", "quit", "bye"]:
            st.success("🧹 Ending session. Cache and chat history cleared.")
            st.cache_resource.clear()
            st.session_state.clear()
            st.stop()

        with st.spinner("Thinking..."):
            result = st.session_state.qa_chain({
                "question": prompt,
                "chat_history": st.session_state.chat_history
            })
            answer = result["answer"]
            st.session_state.chat_history.append((prompt, answer))

            for user_q, bot_a in st.session_state.chat_history:
                st.chat_message("user").write(user_q)
                st.chat_message("assistant").write(bot_a)

    # 📄 PDF generation button
    # st.markdown("---")
    # if st.button("📄 Generate PDF from Interviews"):
    #     if "structured" in st.session_state:
    #         with st.spinner("Generating PDF..."):
    #             pdf_bytes = pdfgenerator(st.session_state.structured)
    #             st.success("PDF generated successfully! 📄")
    #             st.download_button("⬇️ Download PDF", data=pdf_bytes, file_name="interview_data.pdf", mime="application/pdf")
    #     else:
    #         st.warning("Please load and build the chatbot first.")
