import json

from linebot import LineBotApi, WebhookHandler
# from linebot.v3.webhook import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.models import ImageSendMessage
from together import Together
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

import re
import os

from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_community.document_loaders import WebBaseLoader
from typing import Literal
from langchain_core.tools import tool

from langchain_cohere import CohereEmbeddings, CohereRerank
from langchain_together import ChatTogether
from langchain_qdrant import Qdrant

from langchain_core.documents import Document
# Jina AI Reader model
import requests

from langchain_core.messages import SystemMessage, RemoveMessage
from langchain_core.tools import tool

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import Connection
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever

from langchain_core.messages import HumanMessage
from utils import getSAUGY, getDINU, getHOYA, getLYNN, getZOLLY, getREMI, getBOB
from utils import is_emoji, isKeywordautorReply, sticker_list

line_bot_api = LineBotApi(os.environ['channel_access_token'])
handler = WebhookHandler(os.environ['channel_secret'])
dynamodb = boto3.resource('dynamodb')
PostgresURL = f"postgresql://postgres:{os.environ['PostgresURL']}@database-2.cfyo6i0yafoq.ap-southeast-1.rds.amazonaws.com:5432/llm_chat"
TOGETHER_API_KEY = os.environ['TOGETHER_API_KEY']
COHERE_API_KEY = os.environ['COHERE_API_KEY']
QDRANT_API_KEY = os.environ['QDRANT_API_KEY']
USE_SQS = True

class State(MessagesState):
    summary: str

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('YourTableName')  # Replace with your table name

def create_item_if_not_exists(user_channel):
    table = dynamodb.Table('chat_history2')
    response = table.put_item(
        Item={
            'user_channel': user_channel,  # Partition key
            'user_info': 'None',        # Sort key
        },
        ConditionExpression="attribute_not_exists(user_channel)"  # Ensure user_channel doesn't exist
    )
    print("Item created successfully!")
    return response

def read_from_dynamodb(user_id):
    table = dynamodb.Table('chat_history2')
    response = table.get_item(
        Key={
            'user_channel': user_id, "user_info": 'None'
        }
    )
    if 'Item' in response:
        message_user_set = response['Item'].get('message_user', set())
        message_bot_set = response['Item'].get('message_user', set())
        return message_user_set, message_bot_set
        # return response['Item']
    else:
        return "User with ID not found.", user_id

def add_to_string_set(user_id, attre, new_message):
    table = dynamodb.Table('chat_history2')
    response = table.update_item(
        Key={'user_channel': user_id, "user_info": 'None'},
        UpdateExpression=f"ADD attre :new_message",
        ExpressionAttributeValues={
            ':new_message': {new_message}  # Use a Python set to represent the string set
        },
        ReturnValues="UPDATED_NEW"
    )
    return response

def add_to_existing_string_set(user_id, new_message):
    
    table = dynamodb.Table('chat_history2')
    response = table.update_item(
        Key={'user_channel': user_id, "user_info": 'None'},
        UpdateExpression="ADD message_user :new_message",
        ExpressionAttributeValues={
            ':new_message': {new_message}
        },
        ConditionExpression="attribute_exists(message_user)",  # Ensure the attribute exists
        ReturnValues="UPDATED_NEW"
    )
    return response

def linebot(event):
    

        # line_bot_api = LineBotApi(access_token)
        # handler = WebhookHandler(secret)
        # signature = event['headers']['x-line-signature']
    
    body = json.loads(event['body']) # no header  json.loads(event['body'])
    print('body=', body)
    # handler.handle(body, signature)    # I can't match body and signature now. Probably have error with headers

    replyToken = body['events'][0]['replyToken']
    type = body['events'][0]['message']['type']

    # print(body['events'][0]['message']['text'])
    sticker_emoji, sticker_url = sticker_list()
    if type == 'text':
        
        msg = body['events'][0]['message']['text']
        msg1 = msg.replace(' ', '')
        dtto_format = re.match('^[BbDdHhLlSsRrZz]\d+$', msg1)

        # Dtto stickers search
        if dtto_format is not None:
            code = dtto_format.group()
            character = code[0].lower()
            index = int(code[1:])
            res_url = []
            if character == 'b':
                res_url = getBOB()
            elif character == 'd':
                res_url = getDINU()
            elif character == 'h':
                res_url = getHOYA()
            elif character == 'l':
                res_url = getLYNN()
            elif character == 's':
                res_url = getSAUGY()
            elif character == 'r':
                res_url = getREMI()
            elif character == 'z':
                res_url = getZOLLY()
            
            if len(res_url) != 0:
                index = (index-1) % len(res_url) if index > 0 else 0
                message =  ImageSendMessage(original_content_url=res_url[index],
                            preview_image_url=res_url[index])   
                line_bot_api.reply_message(replyToken, message)
                return 'Success Dtto'

        # Our magic commands
        elif isKeywordautorReply(msg) == True:
            return 'AutoReply'
        # LLM Chatbot
        else:

            llm = ChatTogether(
                model='meta-llama/Llama-3.3-70B-Instruct-Turbo-Free',
                together_api_key=TOGETHER_API_KEY)

            embeddings = CohereEmbeddings(
                model='embed-multilingual-v3.0',
                cohere_api_key=COHERE_API_KEY
            )
            vectorstore = Qdrant.from_existing_collection(
                embedding=embeddings,
                collection_name="PDF_Langchain",
                url="https://3c6a22ab-7343-4017-ab1d-4e3ca8b1872c.europe-west3-0.gcp.cloud.qdrant.io:6333",
                api_key=QDRANT_API_KEY,
            )


            USER_ID = body['events'][0]['source']['userId']
            config = {"configurable": {"thread_id": f"{USER_ID}"}}
            DB_URI = PostgresURL
            connection_kwargs = {"autocommit": True, "prepare_threshold": 0}


            # Retrieve docs and return content and raw document
            @tool(response_format="content_and_artifact")
            def retrieve(query: str):
                """Retrieve information related to a query."""
                retriever = vectorstore.as_retriever(
                    search_kwargs={'k': 50, 'filter': {"user_id": USER_ID}})
                compressor = CohereRerank(model='rerank-english-v3.0',
                                          cohere_api_key=COHERE_API_KEY, top_n=10)
                compression_retriever = ContextualCompressionRetriever(base_compressor=compressor,
                                                                       base_retriever=retriever)
                retrieved_docs = compression_retriever.invoke(query)
                serialized = "\n\n".join(
                    (f"Source: {doc.metadata['source']}\n" f"Content: {doc.page_content}") for doc in retrieved_docs)
                return serialized, retrieved_docs
            # Query documents or direct respond
            def query_or_respond(state: State):
                """Generate tool call for retrieval or respond."""
                summary = state.get("summary", "")

                if summary:
                    system_message = f"Summary of conversation earlier: {summary}"
                    messages = [SystemMessage(content=system_message)] + state["messages"]
                else:
                    messages = state["messages"]

                llm_with_tools = llm.bind_tools([retrieve])
                response = llm_with_tools.invoke(messages, tool_choice="retrieve")
                retry_times = 5
                retry = 0
                message_retry = []
                while ((response.content.startswith("<function=retrieve>") or response.content.startswith(
                        '{"name": "retrieve"')) and (retry < retry_times)):
                    print(f"============ Error response:{response.content}. Retry {retry} times. ==============\n")
                    message_retry = messages.copy()
                    message_retry.append(response)
                    err_msg = HumanMessage(
                        content="The last tool call raised an exception. Try calling the tool again with corrected arguments. Do not repeat mistakes.")
                    message_retry.append(err_msg)
                    response = llm_with_tools.invoke(message_retry, tool_choice="retrieve")
                    retry = retry + 1

                return {"messages": [response]}

            tools = ToolNode([retrieve])
            # Generate responds from retrieve documents
            def generate(state: State):
                """Generate answer."""

                summary = state.get("summary", "")
                summary_message = ""
                if summary:
                    summary_message = f"Summary of conversation earlier: {summary}"

                recent_tool_messages = []
                for message in reversed(state["messages"]):
                    if message.type == "tool":
                        recent_tool_messages.append(message)
                    else:
                        break
                tool_messages = recent_tool_messages[::-1]  # only use the last tool recent_tool_messages[::-1]
                # Format into prompt
                docs_content = "\n\n".join(doc.content for doc in tool_messages)
                system_message_content = (
                    f"""You are an assistant forquestion-answering tasks. Use
                        the following pieces of retrieved context to answer the question. If you don't
                        know the answer, say that you don't know. Use ten sentences maximum and keep the answer concise.
                        \n\n {docs_content}. {summary_message}"""
                )

                conversation_messages = [message for message in state["messages"] if message.type in ("human", "system")
                                         or (message.type == "ai" and not message.tool_calls)]

                prompt = [SystemMessage(system_message_content)] + conversation_messages
                response = llm.invoke(prompt)
                print(f"We generation content {response}")

                delete_messages = []
                for m in state["messages"]:
                    if m.type == 'tool' or len(m.content) == 0:
                        delete_messages.append(RemoveMessage(id=m.id))
                delete_messages.append(response)

                return {"messages": delete_messages}

            def summarize_conversation(state: State):

                summary = state.get("summary", "")
                if summary:
                    summary_message = (f"This is summary of the conversation to date: {summary}\n\n"
                                       "Modify the summary by taking into account the new messages above:")  # Extend or Modify
                else:
                    summary_message = "Create a summary of the conversation above:"

                messages = state["messages"] + [HumanMessage(content=summary_message)]
                response = llm.invoke(messages)

                delete_num = 0
                delete_messages = []
                for m in state["messages"]:
                    if m.type == 'tool' or len(m.content) == 0:
                        delete_messages.append(RemoveMessage(id=m.id))
                        delete_num = delete_num + 1

                history_length = 15
                history_preserve = 4
                if (len(state["messages"]) > history_length):

                    for m in state["messages"]:
                        if (len(state["messages"]) - delete_num) <= history_preserve:
                            break
                        if (m.type == 'tool' or len(m.content) == 0):  # Already put in remove messages
                            continue

                        delete_messages.append(RemoveMessage(id=m.id))
                        delete_num = delete_num + 1
                    # delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-6]]

                return {"summary": response.content, "messages": delete_messages}



            graph_builder = StateGraph(State)  # StateGraph(MessagesState)
            graph_builder.add_node(query_or_respond)
            graph_builder.add_node(tools)
            graph_builder.add_node(generate)
            graph_builder.add_node(summarize_conversation)

            graph_builder.add_edge(START, "query_or_respond")
            graph_builder.add_conditional_edges("query_or_respond", tools_condition,
                                                {END: END, "tools": "tools"})
            graph_builder.add_edge("tools", "generate")
            graph_builder.add_edge("generate", "summarize_conversation")
            graph_builder.add_edge("summarize_conversation", END)


            if "!清除記憶" in msg or "！清除記憶" in msg:
                # table.delete_item(Key={'user_channel': user_channel, 'user_info': 'None'})
                # Delete qdrant user documents vector store
                from qdrant_client import models  # Filter(must=[FieldCondition(key=’rand_number’, range=Range(gte=0.7))])
                filter = models.Filter(must=[models.FieldCondition(key="metadata.user_id",
                                                                   match=models.MatchValue(
                                                                       value=f"{USER_ID}"))])  # "metadata": user_id .{"must": [{"key": "user_id", "match":{"value": "test1"}}]}
                vectorstore.client.delete(collection_name="PDF_Langchain", points_selector=filter)

                # Delete postgres chat history
                with Connection.connect(DB_URI, **connection_kwargs) as conn:

                    config = {"configurable": {"thread_id": f"{USER_ID}"}}
                    thread_id = config["configurable"]["thread_id"]
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,))
                    cursor.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (thread_id,))
                    cursor.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (thread_id,))

                line_bot_api.reply_message(replyToken, TextSendMessage("已清除 Bot 先前聊天記憶!"))

                return "Delete LineBot Memory."
            elif '!聊天紀錄' in msg or "！聊天紀錄" in msg or '!聊天記錄' in msg or "！聊天記錄" in msg:
                with Connection.connect(DB_URI, **connection_kwargs) as conn:
                    checkpointer = PostgresSaver(conn)
                    config = {"configurable": {"thread_id": f"{USER_ID}"}}
                    checkpointer.setup()
                    app = graph_builder.compile(checkpointer=checkpointer)
                    state = app.get_state(config).values
                    if 'messages' in state:
                        messages= state["messages"]
                        messages = "\n".join((m.type + ": "+m.content) for m in messages)
                        messages = messages[:-4900:-1]
                        messages = messages[::-1]
                    else:
                        messages = "沒有聊天記錄"

                line_bot_api.reply_message(replyToken, TextSendMessage(messages))

                return "Retrieve LineBot chat history."

            elif "!聊天總結" in msg or "！聊天總結" in msg:

                with Connection.connect(DB_URI, **connection_kwargs) as conn:
                    checkpointer = PostgresSaver(conn)
                    config = {"configurable": {"thread_id": f"{USER_ID}"}}
                    checkpointer.setup()
                    app = graph_builder.compile(checkpointer=checkpointer)
                    state = app.get_state(config).values
                    if 'summary' in state:
                        summary = state["summary"]
                        summary = "  \n".join(m.content for m in summary) if isinstance(summary, list) else summary
                        summary = summary[:-4900:-1]
                        summary = summary[::-1]
                    else:
                        summary = "沒有聊天總結記錄"


                line_bot_api.reply_message(replyToken, TextSendMessage(summary))

                return "Retrieve LineBot chat history."

            elif msg.startswith('http'):
                URL = f"{msg}"  # "https://lilianweng.github.io/posts/2023-06-23-agent/"
                WEB_URL = f'https://r.jina.ai/{URL}'
                headers = {
                    'X-With-Generated-Alt': 'true',
                    'X-With-Images-Summary': 'true',
                    'X-With-Links-Summary': 'true'
                }
                response = requests.get(WEB_URL, headers=headers)
                parse_text = response.text

                document = Document(page_content=parse_text, metadata={"source": WEB_URL})

                text_splitter = RecursiveCharacterTextSplitter(
                    # Set a really small chunk size, just to show.
                    chunk_size=500,
                    chunk_overlap=200,
                    length_function=len,
                    is_separator_regex=False,
                )

                doc_splits = text_splitter.create_documents([parse_text],
                                                            metadatas=[{"source": WEB_URL, "user_id": USER_ID}])


                vectorstore = Qdrant.from_documents(documents=doc_splits, embedding=embeddings,
                                                    url="https://3c6a22ab-7343-4017-ab1d-4e3ca8b1872c.europe-west3-0.gcp.cloud.qdrant.io:6333",
                                                    api_key=QDRANT_API_KEY,
                                                    collection_name="PDF_Langchain", prefer_grpc=True,
                                                    force_recreate=False)
                line_bot_api.reply_message(replyToken, TextSendMessage("已讀取網址文件!"))

                return "Store embedding vector to qdrant"

            ai_message=''
            with Connection.connect(DB_URI, **connection_kwargs) as conn:
                checkpointer = PostgresSaver(conn)
                checkpointer.setup()
                app = graph_builder.compile(checkpointer=checkpointer)
                config = {"configurable": {"thread_id": f"{USER_ID}"}}
                input_message = HumanMessage(content=f"{msg}")
                all_messages = app.invoke({"messages":[input_message]}, config)
                ai_message = all_messages["messages"][-1].content
                state = app.get_state(config).values  # state is a dict of several messages
                temp = checkpointer.get_tuple(config)

            if len(ai_message) >=5000:
                ai_message = ai_message[:4986]
                line_bot_api.reply_message(replyToken, TextSendMessage(ai_message+' <超過Line字數上限!>'))
            else:
                line_bot_api.reply_message(replyToken, TextSendMessage(ai_message))

    return 'Default Return'

def handler(event, context):

    print("the event is :", event, '\n')

    if USE_SQS == True:
        event = event['Records'][0]   # We use  standard SQS and have a default Records key at outer scope

    message_result = linebot(event)
    print('Message result:', message_result)


    # Need to delete message that have processed
    if USE_SQS == True:
        try:
            sqs = boto3.client('sqs')
            queue_url = 'https://sqs.ap-southeast-1.amazonaws.com/438465157691/langchain_lambda'
            receipt_handle = event['receiptHandle']
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
        except Exception as e:
            print(f"Error deleting message from queue. {str(e)}")

    # signature = event['headers']['x-line-signature']
    # # get request body as text
    # body = event['body']
    # try:
    #     handler.handle(body, signature)
    # except InvalidSignatureError:
    #     return {
    #         'statusCode': 502,
    #         'body': json.dumps("Invalid signature. Please check your channel access token/channel secret.")
    #         }
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }



# if __name__ == '__main__':
#     app.run()
