# Importing necessary libraries
import boto3
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_aws import BedrockEmbeddings, ChatBedrock
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from opensearchpy import RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from constants import DOCUMENT_URL, OPENSEARCH_HOST, AWS_ACCESS_KEY, AWS_SECRET_ACCESS_KEY, AWS_REGION

# AWS configuration
service = "es"  

def get_aws_auth():
    credentials = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY, 
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    ).get_credentials()
    return AWS4Auth(
        AWS_ACCESS_KEY, 
        AWS_SECRET_ACCESS_KEY, 
        AWS_REGION, 
        service, 
        session_token=credentials.token
    )

awsauth = get_aws_auth()

# Document Processing
def load_and_split_documents():
    # Load the data
    loader = PyPDFLoader(DOCUMENT_URL)
    
    # Split text into chunks
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", " ", ""], 
        chunk_size=700, 
        chunk_overlap=70
    )
    return splitter.split_documents(loader.load())

def create_embeddings():
    return BedrockEmbeddings(
        credentials_profile_name='default',
        model_id='amazon.titan-embed-text-v1'
    )

# define vector database
def create_vector_store(documents, embeddings):
    return OpenSearchVectorSearch.from_documents(
        documents=documents,
        embedding=embeddings,
        opensearch_url=OPENSEARCH_HOST,
        index_name="index_roancagu",
        http_auth=awsauth,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )

# creating index
def document_indexing():
    documents = load_and_split_documents()
    embeddings = create_embeddings()
    return create_vector_store(documents, embeddings)

# LLM Configuration
def configure_llm():
    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name="us-east-1",
    )

    model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    model_kwargs =  { 
        "max_tokens": 2048,
        "temperature": 0.0,
        "top_k": 250,
        "top_p": 1,
        "stop_sequences": ["\n\nHuman"],
    }

    return ChatBedrock(
        client=bedrock_runtime,
        model_id=model_id,
        model_kwargs=model_kwargs,
    )

# QA Chain Configuration
def create_qa_prompt():
    # Defining the main prompt to instruct the model on how to behave in the conversation
    system_prompt = (
        "Eres un asistente que utiliza el contexto proporcionado para responder preguntas sobre el tráfico en la ciudad. "
        "Utiliza las siguientes piezas de contexto recuperado para responder la pregunta. Si no sabes la respuesta, "
        "dice que no lo sabes. Usa un máximo de tres oraciones y mantén la respuesta concisa."
        "\n\n"
        "{context}"
    )
    
    # Creating a chat prompt template that defines the structure of the system and human messages in the conversation
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

def create_qa_chain():
    vector_store = document_indexing()
    llm = configure_llm()
    qa_prompt = create_qa_prompt()
    # Create a chain that combines documents from vector DB with the LLM
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    
    # Gives allows you to get the answer
    return create_retrieval_chain(vector_store.as_retriever(), question_answer_chain)
    
     

# Main Execution
if __name__ == "__main__":
    # Example question
    question = "Cuanto tengo que pagar si me paso un alto?"
    response = create_qa_chain().invoke({"input": question, "chat_history": []})
    print(response["answer"])
