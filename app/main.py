from typing import Union
from bson import ObjectId
from fastapi import FastAPI, HTTPException
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase as sqlchain
from pydantic import BaseModel
from pymongo import MongoClient
import openai
from fastapi.middleware.cors import CORSMiddleware
#from langchain_community.utilities import SQLDatabase



llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

#db = SQLDatabase.from_uri("sqlite:///Chinook.db")
db = sqlchain.from_uri("mssql+pyodbc://sa:ABC1238f47!@104.254.247.128:1436/Universidad?driver=ODBC+Driver+17+for+SQL+Server")
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()


app = FastAPI()

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_DETAILS = "mongodb://root:*%25h5MY2Wg_@104.254.247.128:27017/chat?authSource=admin"
# Cadena de conexión a tu instancia de MongoDB
MONGO_URL = "mongodb://root:*%25h5MY2Wg_@104.254.247.128:27017/chat?authSource=admin"

client = MongoClient(MONGO_URL)

# Selecciona tu base de datos
dbMongo = client['chat']

class Message(BaseModel):
    role:str
    content:str

class ConversationResponse(BaseModel):
    id: str
    name: str

class Conversation(BaseModel):
    name: str
    description: str
    messages: list[Message]
    mail: str  # Agrega esto

def getMessages(conversation_id: str):
    collection = dbMongo['conversations'] 
    # Convertir la cadena del ID a ObjectId
    oid = ObjectId(conversation_id)

    # Realizar la consulta
    conversation = collection.find_one({"_id": oid})

    if conversation:

        return conversation
    else:
        print("Conversación no encontrada.")

def updateConversation(document_id:str, message: Message):
    # Nuevo mensaje para agregar
    new_message = message
    # Actualización del documento usando $push para agregar el nuevo mensaje
    collection = dbMongo['conversations'] 
    # Creando un nuevo objeto Message
    new_message = Message(role=message.role, content=message.content)

    # Convirtiendo el objeto Message a un diccionario manualmente
    message_dict = {
        "role": new_message.role,
        "content": new_message.content
    }

    resultado = collection.update_one(
        {"_id": ObjectId(document_id)},
        {"$push": {"messages": message_dict}}
    )

    print(resultado)


@app.get("/conversations/", response_model=list[ConversationResponse])
def get_conversations():
    collection  = dbMongo['conversations'] 
    # Encontrar todos los documentos en la colección y devolverlos
    conversations = []
    for conversation in collection.find():
        item = {
            "id": str(conversation["_id"]),
            "name": conversation.get("name", ""),
        }
        conversations.append(item)

    return conversations

@app.post("/conversations/")
async def create_item(item: Conversation):
    item.mail = "sebastian.villarreal@tibs.com.mx"
    collection  = dbMongo['conversations'] 

    item_dict = item.dict()  # Convertir el objeto a diccionario
    
    result =  collection.insert_one(item_dict)  # Asegurarse de usar await para la operación asíncrona
    return {"name": item.name, "description": item.description, "id": str(result.inserted_id)}

@app.get("/conversations/{conversation_id}", response_model=Conversation)
def get_conversation(conversation_id: str):
    # Intenta convertir el ID de la conversación a ObjectId
    try:
        oid = ObjectId(conversation_id)
    except:
        raise HTTPException(status_code=400, detail="ID de conversación inválido")

    collection  = dbMongo['conversations'] 
    # Busca el documento en la base de datos
    conversation =  collection.find_one({"_id": oid})

    # Si no se encuentra el documento, retorna un error 404
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    

    # Prepara la respuesta
    response = {
        "id": str(conversation["_id"]),
        "name": conversation.get("name", ""),
        "description": conversation.get("description", ""),
        "messages": conversation.get("messages", []),
        "mail": conversation.get("mail")
    }
    return response
    

@app.get("/pregunta/{conversation}")
def read_item( conversation: str,  pregunta: Union[str, None] = None):
    updateConversation(conversation, message=Message(role="user", content=pregunta))
    SQL_PREFIX = """You are an agent designed to interact with a SQL database.
        Given an input question, create a syntactically correct SQL Server query to run, then look at the results of the query and return the answer.
        Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 5 results.
        You can order the results by a relevant column to return the most interesting examples in the database.
        Never query for all the columns from a specific table, only ask for the relevant columns given the question.
        You have access to tools for interacting with the database.
        Only use the below tools. Only use the information returned by the below tools to construct your final answer.
        You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.

        DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

        To start you should ALWAYS look at the tables in the database to see what you can query.
        Do NOT skip this step.
        Then you should query the schema of the most relevant tables."""

    system_message = SystemMessage(content=SQL_PREFIX)
    agent_executor = create_react_agent(llm, tools, messages_modifier=system_message)

    for s in agent_executor.stream(
        {"messages": [HumanMessage(content=pregunta)]}
    ):
        print(s)
        tools_messages = s.get('tools', {}).get('messages', [])
        respuesta = ""
        agent_messages = s.get('agent', {}).get('messages', [])
        for message in agent_messages:
            if message.content != "":
                respuesta = message.content
                updateConversation(conversation, Message(role="system", content=respuesta))

    return {"conversation": conversation, "pregunta": pregunta, "respuesta": respuesta}










