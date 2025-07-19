# PrepGenie

**PrepGenie** is a Retrieval-Augmented Generation (RAG) based Q&A chatbot that assists users with job interview preparation by answering queries based on uploaded documents and real-world interview experiences scraped from the web.

---

## Features

- **Custom Interview Q&A Chatbot**  
  Answer queries related to specific companies and job roles using context-aware responses.

- **Automated Data Collection**  
  Uses Selenium to scrape fresh interview experiences from online platforms and integrates the raw data into the chatbot system.

- **RAG Pipeline**  
  Combines FAISS for chunk retrieval with LangChain and Gemini Pro to generate high-quality, grounded answers.

- **Persistent Conversation Flow**  
  Maintains memory across messages to support multi-turn conversations.

- **PDF Export**  
  Automatically generates a downloadable PDF summary of your chatbot session.

---

## Tech Stack

- **Frontend:** Streamlit 
- **Backend:** Python, LangChain
- **LLM:** gemini-2.0-flash
- **Vector Store:** FAISS
- **Web Scraping:** Selenium
- **PDF Export:** WeasyPrint

---

