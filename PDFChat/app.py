from dotenv import load_dotenv
import os
import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain import HuggingFaceHub

def display_chat_history():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.session_state.chat_history:
        for chat in st.session_state.chat_history:
            st.write("**Question:** ", chat["question"])
            st.write("**Answer:** ", chat["answer"])
            st.write("---")

def main():
    load_dotenv()
    st.set_page_config(page_title="Ask your PDF")
    st.header("Ask Your PDF")

    pdf = st.file_uploader("Upload your pdf", type="pdf")

    if pdf is not None:
        pdf_reader = PdfReader(pdf)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()

        # Split into chunks
        text_splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=10000,
            chunk_overlap=1000,
            length_function=len
        )
        chunks = text_splitter.split_text(text)

        # Create embeddings
        embeddings = HuggingFaceEmbeddings()

        knowledge_base = FAISS.from_texts(chunks, embeddings)
        display_chat_history()
        user_question = st.text_input("Ask Question about your PDF:")
        if user_question:
            docs = knowledge_base.similarity_search(user_question)
            huggingfacehub_api_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
            llm = HuggingFaceHub(repo_id="google/flan-t5-large", model_kwargs={"temperature": 3, "max_length": 500}, huggingfacehub_api_token=huggingfacehub_api_token)
            chain = load_qa_chain(llm, chain_type="stuff")
            response = chain.run(input_documents=docs, question=user_question)

            st.write(response)
            
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []

            st.session_state.chat_history.append({"question": user_question, "answer": response})

if __name__ == '__main__':
    main()
