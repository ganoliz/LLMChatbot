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

line_bot_api = LineBotApi(os.environ['channel_access_token'])
handler = WebhookHandler(os.environ['channel_secret'])
dynamodb = boto3.resource('dynamodb')
PostgresURL = f"postgresql://postgres:{os.environ['PostgresURL']}@database-2.cfyo6i0yafoq.ap-southeast-1.rds.amazonaws.com:5432/llm_chat"
TOGETHER_API_KEY = os.environ['TOGETHER_API_KEY']
COHERE_API_KEY = os.environ['COHERE_API_KEY']
QDRANT_API_KEY = os.environ['QDRANT_API_KEY']

class State(MessagesState):
    summary: str

def is_emoji(s):
    # Emoji pattern using Unicode ranges for emojis
    emoji_pattern = re.compile(
        r"[\U0001F600-\U0001F64F]"  # Emoticons
        r"|[\U0001F300-\U0001F5FF]"  # Miscellaneous Symbols and Pictographs
        r"|[\U0001F680-\U0001F6FF]"  # Transport and Map Symbols
        r"|[\U0001F900-\U0001F9FF]"  # Supplemental Symbols and Pictographs
        r"|[\U0001FA70-\U0001FAFF]"  # Symbols and Pictographs Extended-A
        r"|[\u2600-\u26FF]"  # Miscellaneous Symbols
        r"|[\u2700-\u27BF]"  # Dingbats
        r"|[\u2639-\u263A]"  # Add ☹️ and ☺️ specifically
        , flags=re.UNICODE)

    return bool(emoji_pattern.match(s))
def sticker_list(idx=0):
    sticker_emoji = ["🥱", "🎵", "😠", "😐", "🙏", "😭", "👍", "👻", "🤗", "💤",
                     "😴", "🤓"]
    sticker_url = ["https://sticker-assets.dcard.tw/images/06c62d24-28c1-4e38-bee4-29f74536fef0/orig.png",
                     "https://sticker-assets.dcard.tw/images/ee2a82a4-7c75-42d9-b183-84c226c059a5/orig.png",
                     "https://sticker-assets.dcard.tw/images/410d28f8-b1ee-4ced-8e64-d08f14723926/orig.png",
                     "https://sticker-assets.dcard.tw/images/4efa8755-977a-44a1-a3f7-452f5511d4a4/orig.png",
                     "https://sticker-assets.dcard.tw/images/73c6b900-8ac7-4e66-a69d-597041e6841c/orig.png",
                     "https://sticker-assets.dcard.tw/images/a0186c29-eae4-4799-ab4d-d60f5b7c957f/orig.png",
                     "https://sticker-assets.dcard.tw/images/b9be384c-595d-40e8-9d9c-3230845f18ba/orig.png",
                     "https://sticker-assets.dcard.tw/images/3530ffcc-0753-48e1-b890-3791471fd055/orig.png",
                     "https://sticker-assets.dcard.tw/images/b20d6fa9-1f28-4144-a78b-4189355e078a/orig.png",
                     "https://sticker-assets.dcard.tw/images/1418c01c-b916-4a0f-8e11-f58240feaddb/orig.png",
                     "https://sticker-assets.dcard.tw/images/c5254199-d085-4e2c-be2c-b64dff9a9c08/orig.png",
                     "https://sticker-assets.dcard.tw/images/51ca7ba3-ad0d-45c4-aebe-2ce8a51c722a/orig.png",]
    return sticker_emoji, sticker_url
# @app.route("/", methods=['POST'])

def getSAUGY():
    
    result_url =[
    'https://sticker-assets.dcard.tw/images/5ca072d3-55d0-434a-9059-f58c4028c8e2/orig.png',
    'https://sticker-assets.dcard.tw/images/9381abae-b8b9-46b5-8423-aeb5b48f2e0a/orig.png',
    'https://sticker-assets.dcard.tw/images/334b02b8-f61c-4f3a-8910-ffd4b15643b6/orig.png',
    'https://sticker-assets.dcard.tw/images/da827e18-8e79-4802-bcfb-bb1102fb780a/orig.png',
    'https://sticker-assets.dcard.tw/images/a4e021e1-7c4b-48f5-b090-63d8fddf7a5c/orig.png',
    'https://sticker-assets.dcard.tw/images/7ef25ca9-d1f8-4bc0-92f3-74c7a8fc0594/orig.png',
    'https://sticker-assets.dcard.tw/images/a435e212-3046-48cf-9bdd-e3b58a35ade8/orig.png',
    'https://sticker-assets.dcard.tw/images/a26dc921-7c45-4c97-ac87-2614ea7c5139/orig.png',
    'https://sticker-assets.dcard.tw/images/47dfe03e-898c-4950-952c-5e464ddeb39a/orig.png',

    'https://sticker-assets.dcard.tw/images/c76494fe-f620-42bc-ab01-af33ae7ccd49/orig.png',
    'https://sticker-assets.dcard.tw/images/36345eb9-fdb6-4ab1-ae34-1c2b5a3b8180/orig.png',
    'https://sticker-assets.dcard.tw/images/d1c71786-d438-4748-97c6-8ed09c0a8fc4/orig.png',
    'https://sticker-assets.dcard.tw/images/22b03819-59f2-43be-a842-728b95bb23e5/orig.png',
    'https://sticker-assets.dcard.tw/images/566b29af-803f-433f-939c-6cb539e1f7c8/orig.png',
    'https://sticker-assets.dcard.tw/images/776943bd-664e-4c9f-ad29-bd08eefb6cec/orig.png',
    'https://sticker-assets.dcard.tw/images/5f8874cf-6611-4ca6-8d29-38f9ac636ea5/orig.png',
    'https://sticker-assets.dcard.tw/images/21e2baaa-4fd5-44c3-8169-3c57ad84108a/orig.png',
    'https://sticker-assets.dcard.tw/images/ce64cef2-fab8-4f6a-864d-8b5e5bc9b238/orig.png',

    'https://sticker-assets.dcard.tw/images/8a29e9b2-8304-4975-a2fc-7cd6f9329158/orig.png',
    'https://sticker-assets.dcard.tw/images/01de551c-fc60-4770-8cbb-a6ce38ce950b/orig.png',
    'https://sticker-assets.dcard.tw/images/685611b0-a3ea-43bd-a480-0f5f7839c774/orig.png',
    'https://sticker-assets.dcard.tw/images/c7b374f5-3c69-4b60-9461-30c698fd7ef8/orig.png',
    'https://sticker-assets.dcard.tw/images/d45d5eb1-7349-49b2-a58b-54feaf49b783/orig.png',
    'https://sticker-assets.dcard.tw/images/c868af36-83bf-4aa9-a54c-1bcb13234484/orig.png',
    'https://sticker-assets.dcard.tw/images/19f7d6e7-a36b-4ef6-af14-543dcc21ac1c/orig.png',
    'https://sticker-assets.dcard.tw/images/329c10dd-de08-4433-85ca-236ba47eac19/orig.png',
    'https://sticker-assets.dcard.tw/images/3284c75d-3955-4acc-82da-c18d47106b83/orig.png',

    'https://sticker-assets.dcard.tw/images/9d11f80a-02f1-4a72-a170-caed88d7cea2/orig.png',
    'https://sticker-assets.dcard.tw/images/6a1b2745-54bf-4488-ba84-fe1541217f50/full.png',
    'https://sticker-assets.dcard.tw/images/c3ba37b1-36a6-49ac-93de-83875db22882/full.png',
    'https://sticker-assets.dcard.tw/images/8f1fd1c7-081e-4eed-94be-ac82d6baaae4/full.png',
    'https://sticker-assets.dcard.tw/images/98a38551-2e92-4fd0-b8e9-14552e030ce1/full.png',
    'https://sticker-assets.dcard.tw/images/9b426319-abfd-43cb-859a-b1a86d569798/full.png',
    'https://sticker-assets.dcard.tw/images/7a10f910-769a-41cd-a508-6b5bbd61fb96/full.png',
    'https://sticker-assets.dcard.tw/images/9417f85c-a9a6-4dcd-b785-25f183708750/full.png',
    'https://sticker-assets.dcard.tw/images/446039c1-1674-46b2-8e31-d7edb769a702/full.png',

    'https://sticker-assets.dcard.tw/images/67becd97-ed7a-433d-bfd0-ce6c66f9a762/full.png',
    'https://sticker-assets.dcard.tw/images/645da7ad-53ab-4d9a-a669-5f63c1d1a95b/full.png',
    'https://sticker-assets.dcard.tw/images/4b5832fa-9e5f-467c-ae6e-cc7bfaf3c557/full.png',
    'https://sticker-assets.dcard.tw/images/54f9be74-97b4-4ef4-abdf-bfaed9e30238/full.png',
    'https://sticker-assets.dcard.tw/images/c9509ad9-5704-4ea0-b046-832e16cb7432/full.png',
    'https://sticker-assets.dcard.tw/images/f5514e2e-44be-4c0e-afc9-f7710d4032cc/full.png',
    'https://sticker-assets.dcard.tw/images/c3cda97f-2975-434c-8c53-9219ad9e0c1c/full.png',
    'https://sticker-assets.dcard.tw/images/4384af3a-4db4-4bdd-a9b8-9f7666035dca/full.png',
    'https://sticker-assets.dcard.tw/images/dc7acbef-7e90-4cb8-8413-ddc0c006e78b/full.png',

    'https://sticker-assets.dcard.tw/images/596ddcc3-777f-4678-83fc-f6f52e4ce102/full.png',
    'https://sticker-assets.dcard.tw/images/b5c7eddc-8dd9-40e9-ba4b-358323a45713/full.png',
    'https://sticker-assets.dcard.tw/images/84eddd38-497c-41d6-8845-ec8b57498c6a/full.png',
    'https://sticker-assets.dcard.tw/images/4d5acaf6-fb1c-4110-8538-6d2d651b410a/full.png',
    'https://sticker-assets.dcard.tw/images/102eb5ae-3f1e-4b28-8866-905a64f87c9b/full.png',
    'https://sticker-assets.dcard.tw/images/b9b289c4-172e-4d7d-8ed1-7ab87aa7744a/full.png',
    'https://sticker-assets.dcard.tw/images/b1e8bc33-e846-4bab-8a6a-490ace5d315f/full.png',
    'https://sticker-assets.dcard.tw/images/a71e45fc-defb-4ae4-992d-adffca997d0c/full.png',
    'https://sticker-assets.dcard.tw/images/5f830473-5bc7-4d5d-8da8-d2e8aca8a17c/full.png',

    'https://sticker-assets.dcard.tw/images/c69489be-dfe7-46d5-ae21-7945b39aabe5/orig.png',
    'https://sticker-assets.dcard.tw/images/9483eb12-b9d4-42b6-9ee7-9790cccbc283/orig.png',
    'https://sticker-assets.dcard.tw/images/1a496bbf-b1bc-402e-b1d2-bba20d62c132/orig.png',
    'https://sticker-assets.dcard.tw/images/fe48c8da-3d8b-4649-83d7-63c275b7f1c9/orig.png',
    'https://sticker-assets.dcard.tw/images/73ed83d9-795f-40fa-8a9d-294a73cc8bbf/orig.png',
    'https://megapx-assets.dcard.tw/images/1e750758-bdab-4d2b-a4d7-5f8c9a69b5f5/full.png',
    'https://megapx-assets.dcard.tw/images/6daf6bc3-4fba-49c3-86b2-6ebfffc09e54/full.png',
    'https://megapx-assets.dcard.tw/images/f6257a01-251d-436a-943a-615fcae7d1a6/full.png',
    'https://megapx-assets.dcard.tw/images/3f1570cb-2916-4964-b820-471685178f13/full.png',
    ]
    return result_url

def getDINU():
    result_url = [
    'https://sticker-assets.dcard.tw/images/764ff643-b618-4691-8e8b-7646a4d86e2d/orig.png',
    'https://sticker-assets.dcard.tw/images/2ef2e126-ed86-4652-a920-d40843df5df5/orig.png',
    'https://sticker-assets.dcard.tw/images/d0764c8b-f751-44ed-a719-51fce3089b3f/orig.png',
    'https://sticker-assets.dcard.tw/images/373c13cc-b66c-41e5-b460-a2c8c61c26c5/orig.png',
    'https://sticker-assets.dcard.tw/images/1fce248b-db7e-4d96-aa93-7370f2eb9c1e/orig.png',
    'https://sticker-assets.dcard.tw/images/e065241a-e07b-4703-a8fe-7d8776ff624b/orig.png',
    'https://sticker-assets.dcard.tw/images/b4d24722-22f7-448b-9ce5-716a419e625c/orig.png',
    'https://sticker-assets.dcard.tw/images/1c16d6af-01aa-4be3-8dc2-5bdd101adbc5/orig.png',
    'https://sticker-assets.dcard.tw/images/7c5d469f-46d8-419b-bdac-effd76d287a9/orig.png',

    'https://sticker-assets.dcard.tw/images/138738df-95d3-46cd-bfb5-0fc2918ccaf7/orig.png',
    'https://sticker-assets.dcard.tw/images/8c418a9c-a742-4522-ada2-ec5004378dff/orig.png',
    'https://sticker-assets.dcard.tw/images/b1ba18cd-a8f0-4e69-8391-999466e2a35b/orig.png',
    'https://sticker-assets.dcard.tw/images/eb0d0f72-9f06-4263-ac10-4b2bba8378c3/orig.png',
    'https://sticker-assets.dcard.tw/images/fe0ae228-e2fd-4e57-9bb2-6bf2d42ed51b/orig.png',
    'https://sticker-assets.dcard.tw/images/2fc67964-07cb-442f-ab65-3bd5f316a388/orig.png',
    'https://sticker-assets.dcard.tw/images/895343ef-e5d2-422d-96f1-4b1622b449e1/orig.png',
    'https://sticker-assets.dcard.tw/images/53a9d171-bbaa-451d-ae48-6d9bb5caeafe/orig.png',
    'https://sticker-assets.dcard.tw/images/d93e9c82-4969-4e74-828d-39c5f28c56c6/orig.png',

    'https://sticker-assets.dcard.tw/images/d417f1d1-22b9-4e19-a4e3-13ead086d78f/orig.png',
    'https://sticker-assets.dcard.tw/images/181e0559-4dd7-4b10-a94f-b5319ba53718/orig.png',
    'https://sticker-assets.dcard.tw/images/39f27780-d143-41a1-80cd-8ca43a7aac8c/orig.png',
    'https://sticker-assets.dcard.tw/images/0213dbb3-5b5a-4fbd-9852-38b510c78f86/orig.png',
    'https://sticker-assets.dcard.tw/images/b826cf74-c055-45e3-90fb-ef3bcf07dbda/orig.png',
    'https://sticker-assets.dcard.tw/images/05c2c9f2-5310-43e1-979c-08f57ad0d7dc/orig.png',
    'https://sticker-assets.dcard.tw/images/5f8874cf-6611-4ca6-8d29-38f9ac636ea5/orig.png',
    'https://sticker-assets.dcard.tw/images/8cc5345c-afde-4475-9529-026094ed573c/orig.png',
    'https://sticker-assets.dcard.tw/images/e2141ae6-e65d-407c-9537-124f65618bdc/orig.png',

    'https://sticker-assets.dcard.tw/images/ddc34bbe-85b2-492c-9d9c-76d4b5357af7/orig.png',
    'https://sticker-assets.dcard.tw/images/97890f92-7182-4648-aaaa-158f1afa2106/orig.png',
    'https://sticker-assets.dcard.tw/images/467c767d-90d8-444d-b2e2-b5f1aceb57a9/orig.png',
    'https://sticker-assets.dcard.tw/images/1ead96d0-0b9a-4375-82b3-f9af60f5a6af/orig.png',
    'https://sticker-assets.dcard.tw/images/6281a899-3b99-4534-b7f8-500fed7aab9a/orig.png',
    'https://sticker-assets.dcard.tw/images/73219d4e-66bb-4268-9062-3711ab7f1ac1/orig.png',
    'https://sticker-assets.dcard.tw/images/299d2b4c-a1c3-4bb2-8adc-853dcc67f3b1/orig.png',
    'https://sticker-assets.dcard.tw/images/30c0fc6b-4746-459d-bc05-6947373bea3a/orig.png',
    'https://sticker-assets.dcard.tw/images/ecc7e913-1662-4928-a4cc-056fe856e862/orig.png',

    'https://sticker-assets.dcard.tw/images/b2c5fd09-b815-4d07-b8e8-51dd703ac934/orig.png',
    'https://sticker-assets.dcard.tw/images/853469f6-bfe6-46fa-9ff4-2fdb0136f58e/orig.png',
    'https://sticker-assets.dcard.tw/images/92adfc70-2890-44a4-a365-368185d07814/orig.png',
    'https://sticker-assets.dcard.tw/images/e09aa338-95bf-447d-84aa-c9eae1721958/orig.png',
    'https://sticker-assets.dcard.tw/images/fb766f92-2924-4a3c-824a-bbc41a3bb88f/orig.png',
    'https://sticker-assets.dcard.tw/images/ec51cec4-6c99-4a49-af85-fc80b82a6467/orig.png',
    'https://sticker-assets.dcard.tw/images/7f53cca4-4aaf-429a-8723-437e45e5946c/orig.png',
    'https://sticker-assets.dcard.tw/images/ed0a93b7-356d-4ffe-99ce-b1b47bec7e57/full.png',
    'https://sticker-assets.dcard.tw/images/c63e532b-4177-462b-95fb-bf6424e43739/full.png',

    'https://sticker-assets.dcard.tw/images/08d1141c-516e-41e5-a54a-bc9efb8fb469/full.png',
    'https://sticker-assets.dcard.tw/images/76f1b959-b9bb-46b6-a925-8b93eb1cd713/full.png',
    'https://sticker-assets.dcard.tw/images/b914ee31-e409-4670-8cf6-52189a7bada7/full.png',
    'https://sticker-assets.dcard.tw/images/ae75c0dd-9c78-4f0e-9d14-21c24a57fffd/full.png',
    'https://sticker-assets.dcard.tw/images/e5f44dc3-4b68-4c6b-af9c-77c8ee28a0bd/full.png',
    'https://sticker-assets.dcard.tw/images/fc61130b-981e-435c-8cb5-ff7f0e0bbf4a/full.png',
    'https://sticker-assets.dcard.tw/images/446039c1-1674-46b2-8e31-d7edb769a702/full.png',
    'https://sticker-assets.dcard.tw/images/06029532-3f57-4cba-bbc7-97cf602de1c3/full.png',
    'https://sticker-assets.dcard.tw/images/b44af092-1580-41c5-b76c-1c0f788095c3/full.png',

    'https://sticker-assets.dcard.tw/images/25d38225-eca7-489f-aa32-47316eeebdce/full.png',
    'https://sticker-assets.dcard.tw/images/dbff62dc-5a20-4fb3-ad7a-736645a42d18/full.png',
    'https://sticker-assets.dcard.tw/images/c9509ad9-5704-4ea0-b046-832e16cb7432/full.png',
    'https://sticker-assets.dcard.tw/images/3f7768f6-a4ca-4d52-97dd-d03252a13673/full.png',
    'https://sticker-assets.dcard.tw/images/caee4fa3-90e7-407e-9cc3-aa7e78acdafb/full.png',
    'https://sticker-assets.dcard.tw/images/596ddcc3-777f-4678-83fc-f6f52e4ce102/full.png',
    'https://sticker-assets.dcard.tw/images/3466451a-6547-4b54-b6a6-089047a2b3b8/orig.png',
    'https://sticker-assets.dcard.tw/images/7ae6c525-885c-4075-b71e-ac94f0c16b52/orig.png',
    'https://sticker-assets.dcard.tw/images/73ed83d9-795f-40fa-8a9d-294a73cc8bbf/orig.png',

    'https://megapx-assets.dcard.tw/images/9b6873f2-2c17-4daf-b792-b9eb880f9542/full.png',
    'https://megapx-assets.dcard.tw/images/12b35278-f93b-4ab8-bd8c-7454d4e312b3/full.png',
    'https://megapx-assets.dcard.tw/images/eb4a1b38-6d25-49d1-885a-c6105c5077b5/full.png',
    'https://megapx-assets.dcard.tw/images/ba5882a1-c55f-4717-8b29-76e40bbc13a9/full.png',
    ]
    
    return result_url
def getHOYA():
    result_url = [
    'https://sticker-assets.dcard.tw/images/a7a04bba-f545-4298-8544-1a185bf671af/orig.png',
    'https://sticker-assets.dcard.tw/images/a06f32ac-87cb-4e45-b825-31c63bf5528a/orig.png',
    'https://sticker-assets.dcard.tw/images/2b3ceec9-c4ae-463c-923b-6e9e46b18679/orig.png',
    'https://sticker-assets.dcard.tw/images/1588fef2-494a-486d-98e1-1f9b3ef8281d/orig.png',
    'https://sticker-assets.dcard.tw/images/8a3d2c5b-60a0-40ca-8334-240c0952e400/orig.png',
    'https://sticker-assets.dcard.tw/images/c4c9a34e-a3fa-49c6-bf25-44a518f5543c/orig.png',
    'https://sticker-assets.dcard.tw/images/c4bdc7da-3a6b-4e62-9e7c-4562b461a9b2/orig.png',
    'https://sticker-assets.dcard.tw/images/e425ebbe-6228-47a3-a89e-09365f96daac/orig.png',
    'https://sticker-assets.dcard.tw/images/71f8a1fa-5374-4802-8577-12b201437999/orig.png',

    'https://sticker-assets.dcard.tw/images/cc779f98-7e56-4142-a449-c8b24bfaea37/orig.png',
    'https://sticker-assets.dcard.tw/images/28811556-ef52-4b78-8ef1-ec36a527ddd9/orig.png',
    'https://sticker-assets.dcard.tw/images/0231f20a-97c5-48e4-a95a-6fb2fbf733a0/orig.png',
    'https://sticker-assets.dcard.tw/images/d61ee61a-5173-4003-b6ce-27a558f999e2/orig.png',
    'https://sticker-assets.dcard.tw/images/89fffebc-deed-4bfa-bf61-ec6708af248e/orig.png',
    'https://sticker-assets.dcard.tw/images/e44123a2-ee18-43d8-9345-a71f2a3bde44/orig.png',
    'https://sticker-assets.dcard.tw/images/5eca09dc-704c-472f-9f73-2b44a41dc315/orig.png',
    'https://sticker-assets.dcard.tw/images/52838443-6214-485a-9d7b-1700cbb7cc15/orig.png',
    'https://sticker-assets.dcard.tw/images/90c5f57c-6d82-4725-8151-8e39fcd6ee7f/orig.png',

    'https://sticker-assets.dcard.tw/images/344b7982-44db-4986-8220-5f0978be8450/orig.png',
    'https://sticker-assets.dcard.tw/images/bd8190a5-c29b-4b1c-b6c5-734ab8827d20/orig.png',
    'https://sticker-assets.dcard.tw/images/4e0685b1-2ced-4363-a8fd-accee79613e2/orig.png',
    'https://sticker-assets.dcard.tw/images/1e4e2ca0-1228-4c30-96b6-7a1380efec47/orig.png',
    'https://sticker-assets.dcard.tw/images/8f4ff7ed-65b1-442e-8f88-1e946cfa498f/orig.png',
    'https://sticker-assets.dcard.tw/images/3fc73726-ad2f-4362-8da3-c5b9e1157f49/orig.png',
    'https://sticker-assets.dcard.tw/images/b2c5fd09-b815-4d07-b8e8-51dd703ac934/orig.png',
    'https://sticker-assets.dcard.tw/images/60c5ad28-5db4-4018-804e-2f66489bfb12/orig.png',
    'https://sticker-assets.dcard.tw/images/e2a49464-6e53-4e2f-ac2f-4cf335bbce8c/orig.png',
    
    'https://megapx-assets.dcard.tw/images/8eaf7655-e9a7-4ff6-a13f-bad515a2ca0b/orig.png',
    'https://megapx-assets.dcard.tw/images/fb766f92-2924-4a3c-824a-bbc41a3bb88f/orig.png',
    'https://megapx-assets.dcard.tw/images/8fcb0474-67aa-4b18-a7d0-2600c76985c7/orig.png',
    'https://megapx-assets.dcard.tw/images/21e833f6-772b-4cb8-862e-c337d3dfe920/orig.png',
    'https://megapx-assets.dcard.tw/images/1b8830e7-8f24-4dc6-8543-017de9977bda/orig.png',
    'https://megapx-assets.dcard.tw/images/f64dacfb-d2bf-4769-8033-8034aa74c279/orig.png',
    'https://megapx-assets.dcard.tw/images/50c6fd7b-9e27-43d4-8cdd-bfd2fb1f5d72/full.png',
    'https://megapx-assets.dcard.tw/images/76f1b959-b9bb-46b6-a925-8b93eb1cd713/full.png',
    'https://megapx-assets.dcard.tw/images/ae75c0dd-9c78-4f0e-9d14-21c24a57fffd/full.png',
    
    'https://megapx-assets.dcard.tw/images/e8899975-c259-416e-a2ae-ef7454028a4a/full.png',
    'https://megapx-assets.dcard.tw/images/c0a334c5-6465-4b54-adc7-e0c360e0642a/full.png',
    'https://megapx-assets.dcard.tw/images/3066c87b-50ba-48d4-ba3c-586e85e67461/full.png',
    'https://megapx-assets.dcard.tw/images/7a10f910-769a-41cd-a508-6b5bbd61fb96/full.png',
    'https://megapx-assets.dcard.tw/images/b765dd87-43d1-4c83-8a89-2ed6e28c1869/full.png',
    'https://megapx-assets.dcard.tw/images/06029532-3f57-4cba-bbc7-97cf602de1c3/full.png',
    'https://megapx-assets.dcard.tw/images/3a0ad12a-39bc-4b3f-b30b-c0f2077d09c7/full.png',
    'https://megapx-assets.dcard.tw/images/310d6712-d5df-4e47-b579-25162f365148/full.png',
    'https://megapx-assets.dcard.tw/images/38081dce-a620-450f-bcfe-29f2c66da248/full.png',
    
    'https://megapx-assets.dcard.tw/images/c9509ad9-5704-4ea0-b046-832e16cb7432/full.png',
    'https://megapx-assets.dcard.tw/images/46a22dc5-25ec-42d1-9880-bb1f423ba0f8/full.png',
    'https://megapx-assets.dcard.tw/images/a234580a-d083-479f-9339-d3d6d4b81243/full.png',
    'https://megapx-assets.dcard.tw/images/5626f32d-fa0c-45c6-a496-2b3e0d3670f6/full.png',
    'https://megapx-assets.dcard.tw/images/9653929b-80da-46cb-a0d3-91bf09ce508c/full.png',
    'https://megapx-assets.dcard.tw/images/77acbb43-1449-4f49-9391-edfed566b216/full.png',
    'https://megapx-assets.dcard.tw/images/07013694-41cc-4d8e-9c0f-af4183deeb11/full.png',
    'https://megapx-assets.dcard.tw/images/818e4e3b-6397-4fc6-8be3-3dc0973e2357/full.png',
    
    ]
    
    return result_url
def getLYNN():
    result_url = [
    'https://sticker-assets.dcard.tw/images/42cc5bd6-a0a8-4b73-8d1e-3284e7b6658a/orig.png',
    'https://sticker-assets.dcard.tw/images/4dfea9d8-0aa7-421e-8a66-d9dad76f3f75/orig.png',
    'https://sticker-assets.dcard.tw/images/f079b2b6-5d5f-4a63-9518-c242c10cd16e/orig.png',
    'https://sticker-assets.dcard.tw/images/5a816438-918a-41af-bfc4-4acc0e564c28/orig.png',
    'https://sticker-assets.dcard.tw/images/18eabe31-19b6-4b6c-9e1d-30d065fc0ee7/orig.png',
    'https://sticker-assets.dcard.tw/images/4d41ede2-a14e-491c-9b88-000c08c5e6a0/orig.png',
    'https://sticker-assets.dcard.tw/images/68336e91-3a93-4505-91f6-9ec51b61b303/orig.png',
    'https://sticker-assets.dcard.tw/images/6af40cc5-9b57-4fa2-923f-40af82949f62/orig.png',
    'https://sticker-assets.dcard.tw/images/1f07e831-8be3-4f9f-9fd4-6e44cb47fb24/orig.png',

    'https://sticker-assets.dcard.tw/images/41c176e2-ad0c-4ca0-8c71-9e6b21a79f92/orig.png',
    'https://sticker-assets.dcard.tw/images/c1f7cb26-8ed5-4234-8ca6-ea937277668b/orig.png',
    'https://sticker-assets.dcard.tw/images/eb0d0f72-9f06-4263-ac10-4b2bba8378c3/orig.png',
    'https://sticker-assets.dcard.tw/images/97779c9d-9645-4bff-a1e2-313117470be3/orig.png',
    'https://sticker-assets.dcard.tw/images/45afaaf2-07fd-4298-9bb0-cff17ebbe2ab/orig.png',
    'https://sticker-assets.dcard.tw/images/7f80bc24-1800-4df2-8563-990acf8634de/orig.png',
    'https://sticker-assets.dcard.tw/images/35a64e27-dd3d-4ce6-a820-0a3f5c729b46/orig.png',
    'https://sticker-assets.dcard.tw/images/1bbd27e4-2680-475a-9028-890d11ac506c/orig.png',
    'https://sticker-assets.dcard.tw/images/f0616a40-02c1-483a-a5a7-4acfd849b7b5/orig.png',

    'https://sticker-assets.dcard.tw/images/d3b12f4f-c51d-4e10-b128-a2f51b4c0a2c/orig.png',
    'https://sticker-assets.dcard.tw/images/ffc9f014-35dc-4921-97ad-bce26e12ef15/orig.png',
    'https://sticker-assets.dcard.tw/images/ffb9bce3-2b47-4571-97d3-398810f1ca2d/orig.png',
    'https://sticker-assets.dcard.tw/images/aea192ca-59d4-479f-b2c6-016f4edf83e9/orig.png',
    'https://sticker-assets.dcard.tw/images/6796c4e2-8be2-4ef1-96c5-be2d04fe8134/orig.png',
    'https://sticker-assets.dcard.tw/images/7051b987-3b0e-4a1d-bc30-f16b9af8e8ce/full.png',
    'https://sticker-assets.dcard.tw/images/90b1525f-4e6b-4099-814b-cf7486ed52ff/orig.png',
    'https://sticker-assets.dcard.tw/images/6924c6e3-e3d2-46b2-a4d2-978a427e8aee/orig.png',
    'https://megapx-assets.dcard.tw/images/19f54141-2bd3-473e-a2a3-fcee028a408d/orig.png',

    ]
    
    return result_url
def getBOB():
    result_url = [
    'https://sticker-assets.dcard.tw/images/a1153652-10b0-4dbc-bcb1-10e9b38303b4/orig.png',
    'https://sticker-assets.dcard.tw/images/87fe7e81-c5a6-48d4-81f5-179f235255d0/orig.png',
    'https://sticker-assets.dcard.tw/images/3e937229-0145-4a9b-9341-8ef1b68dce1f/orig.png',
    'https://sticker-assets.dcard.tw/images/8de2f7bc-70af-4798-be89-4c7dc7b8f000/orig.png',
    'https://sticker-assets.dcard.tw/images/e13e11a8-5917-4ea8-8005-a288c93fb21b/orig.png',
    'https://sticker-assets.dcard.tw/images/46cfffad-6555-40cd-8659-faa8f52d0a25/orig.png',
    'https://sticker-assets.dcard.tw/images/25847cce-018d-47fe-b649-4e83bf5db6c8/orig.png',
    'https://sticker-assets.dcard.tw/images/25847cce-018d-47fe-b649-4e83bf5db6c8/orig.png',
    'https://sticker-assets.dcard.tw/images/f3046f18-f324-494b-888e-c141401be1b5/orig.png',

    'https://sticker-assets.dcard.tw/images/0e8eb20e-0a5f-4520-b4a3-d61b9c3f9102/orig.png',
    'https://sticker-assets.dcard.tw/images/db90253f-7916-4cc7-886a-4b68136e6aa5/orig.png',
    'https://sticker-assets.dcard.tw/images/d61ee61a-5173-4003-b6ce-27a558f999e2/orig.png',
    'https://sticker-assets.dcard.tw/images/96c9e5ab-1630-4299-9018-9a419c09aa63/orig.png',
    'https://sticker-assets.dcard.tw/images/9ceadb2e-b37c-4b38-868e-1cbc10801fb7/orig.png',
    'https://sticker-assets.dcard.tw/images/aa26b44a-9441-4f89-bd40-6a8974558141/orig.png',
    'https://sticker-assets.dcard.tw/images/095431be-93a3-4cc7-b3b2-95b175794672/orig.png',
    'https://sticker-assets.dcard.tw/images/995a5651-b669-4e09-966b-46055fbaf1b0/orig.png',
    'https://sticker-assets.dcard.tw/images/00030bbc-eaf3-4055-96e9-fc6ca3211d91/orig.png',
    
    'https://megapx-assets.dcard.tw/images/8bde4d2b-a06c-4c9e-8e9c-36bfa4c59420/orig.png',
    'https://megapx-assets.dcard.tw/images/cbc485b4-96e1-416e-ac12-63eed72713f4/orig.png',
    'https://megapx-assets.dcard.tw/images/eabed516-4174-432e-b862-9c8858067fb2/orig.png',
    'https://megapx-assets.dcard.tw/images/4b143572-5532-47e6-a719-7f1f5217a878/full.png',
    'https://megapx-assets.dcard.tw/images/c5a01ed4-8003-49f7-a3d1-5737b1058f29/full.png',
    
    ]
    return result_url
def getZOLLY():
    result_url = [
    'https://sticker-assets.dcard.tw/images/6e90e74b-b23a-4ba5-a386-0dc417aadd2c/orig.png',
    'https://sticker-assets.dcard.tw/images/ff0f0efb-ff2c-493d-af1a-d39e3f98b1be/orig.png',
    'https://sticker-assets.dcard.tw/images/3f8135cb-c935-4885-ac6d-dd6756cf7f82/orig.png',
    'https://sticker-assets.dcard.tw/images/7de4cda8-a83e-4667-a2d5-79b08c07784d/orig.png',
    'https://sticker-assets.dcard.tw/images/c7f6a07c-c711-4685-b80d-fcc772655334/orig.png',
    'https://sticker-assets.dcard.tw/images/3d755769-8aa4-41fd-a701-dc73e56e6e97/orig.png',
    'https://sticker-assets.dcard.tw/images/6afd7b2c-1484-4a5c-899e-334c39396b8c/orig.png',
    'https://sticker-assets.dcard.tw/images/922ab47f-41f2-4584-914d-607589efc959/orig.png',
    'https://sticker-assets.dcard.tw/images/9b030d66-678c-4afc-9919-f644e1ae681f/orig.png',

    'https://sticker-assets.dcard.tw/images/a598eaf1-4a79-4eac-9602-88945fbb577b/orig.png',
    'https://sticker-assets.dcard.tw/images/3cf7be0a-bf68-4c4d-89e8-d0ea93f0a530/orig.png',
    'https://sticker-assets.dcard.tw/images/e93afb68-3148-4ae6-bfaf-2fe6bf071d35/orig.png',
    'https://sticker-assets.dcard.tw/images/b20d6fa9-1f28-4144-a78b-4189355e078a/orig.png',
    'https://sticker-assets.dcard.tw/images/073be55f-b468-4282-ab16-9da0697f7f91/orig.png',
    'https://sticker-assets.dcard.tw/images/017fa3a7-5495-440f-b4fc-752405e602e1/orig.png',
    'https://sticker-assets.dcard.tw/images/baae80da-64ab-466d-8e9b-3e06b501d56d/orig.png',
    'https://sticker-assets.dcard.tw/images/b171fdb5-1942-473b-9854-44f63486bf2f/orig.png',
    'https://sticker-assets.dcard.tw/images/793b04ec-eb2a-43f6-adcf-4a26ed28f8eb/orig.png',
    ]
    return result_url
def getREMI():
    result_url = [
    'https://sticker-assets.dcard.tw/images/06c62d24-28c1-4e38-bee4-29f74536fef0/orig.png',
    'https://sticker-assets.dcard.tw/images/ee2a82a4-7c75-42d9-b183-84c226c059a5/orig.png',
    'https://sticker-assets.dcard.tw/images/410d28f8-b1ee-4ced-8e64-d08f14723926/orig.png',
    'https://sticker-assets.dcard.tw/images/4efa8755-977a-44a1-a3f7-452f5511d4a4/orig.png',
    'https://sticker-assets.dcard.tw/images/73c6b900-8ac7-4e66-a69d-597041e6841c/orig.png',
    'https://sticker-assets.dcard.tw/images/a0186c29-eae4-4799-ab4d-d60f5b7c957f/orig.png',
    'https://sticker-assets.dcard.tw/images/b9be384c-595d-40e8-9d9c-3230845f18ba/orig.png',
    'https://sticker-assets.dcard.tw/images/3530ffcc-0753-48e1-b890-3791471fd055/orig.png',
    'https://sticker-assets.dcard.tw/images/b20d6fa9-1f28-4144-a78b-4189355e078a/orig.png',

    'https://sticker-assets.dcard.tw/images/1418c01c-b916-4a0f-8e11-f58240feaddb/orig.png',
    'https://sticker-assets.dcard.tw/images/c5254199-d085-4e2c-be2c-b64dff9a9c08/orig.png',
    'https://sticker-assets.dcard.tw/images/51ca7ba3-ad0d-45c4-aebe-2ce8a51c722a/orig.png',
    'https://sticker-assets.dcard.tw/images/bdb00fe1-eaa0-4a50-bbcf-5f25caf6091a/orig.png',
    'https://sticker-assets.dcard.tw/images/7e21dae9-b32b-4944-8bd7-26632ea9effb/orig.png',
    'https://sticker-assets.dcard.tw/images/467c767d-90d8-444d-b2e2-b5f1aceb57a9/orig.png',
    'https://sticker-assets.dcard.tw/images/47bf904c-5ad9-4362-903b-1722ac4194b3/orig.png',
    'https://sticker-assets.dcard.tw/images/93f72bec-da61-45ea-b623-1486d84726b7/orig.png',
    'https://sticker-assets.dcard.tw/images/28cb79bc-9076-4d84-9270-c02cdd53c726/orig.png',

    'https://sticker-assets.dcard.tw/images/a3467861-c459-4837-b114-6b90db63b3ce/orig.png',
    'https://sticker-assets.dcard.tw/images/c17b8cd6-d8ca-4b7c-8ab5-2f5bbc5eb341/orig.png',
    'https://sticker-assets.dcard.tw/images/d1b66fa2-dcf0-4837-a2cd-86ce1f7c8abe/orig.png',
    'https://sticker-assets.dcard.tw/images/ed0a93b7-356d-4ffe-99ce-b1b47bec7e57/full.png',
    'https://megapx-assets.dcard.tw/images/044337b1-4c6b-4d30-8bb0-7097b6f3f146/orig.png',
    'https://megapx-assets.dcard.tw/images/9a8c96b8-c7a0-4180-ac0a-f9e1fa71a938/full.png',
    'https://megapx-assets.dcard.tw/images/c2a443ec-7da3-4597-8add-9bf5a5a218d4/full.png',

    ]
    return result_url

def isKeywordautorReply(message):
    keywordlist = ['HOYA-L3', 'HOYA-L2', 'HOYA-L1', 'LYNN','DINU-L3',
                    'DINU-L2', 'DINU-L1', 'SAUGY-L3', 'SAUGY-L2', 'SAUGY-L1',
                    'REMI', 'BOB', 'ZOLLY', 'Dtto', 'Dttofriends', '!今天我生日', 
                    'HOYA-P', 'SAUGY-P', 'DINU-P', '!Dtto', '!指令']
    Keyword = False
    if message in keywordlist:
        Keyword = True
    return Keyword



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
    # TODO implement
    # event = event['Records'][0]     # We know use direct API         # We use asynchronous invocation from SQS so we need to get Line webhook event using key Records
    print("the event is :", event, '\n')

    # client = Together()
    # stream = client.chat.completions.create(
    #         model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    #         messages=[{"role": "user", "content": "Hi, how are you"}],
    #         stream=True
    # )
    # message=''
    # for chunk in stream:
    #     message = message + (chunk.choices[0].delta.content)
    # print(message)
    # table = dynamodb.Table('chat_history2')
    # _ = add_to_string_set('1234', 'Hi, what about you.')
    # item = read_from_dynamodb('1234')
    # print(item)
    message_result = linebot(event)
    print(message_result)

        
        
    
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
