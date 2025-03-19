# LLM Linebot on AWS Lambda

![image](https://github.com/ganoliz/LLMChatbot/blob/main/images/architecture.jpg)

LLM-powered Chatbot Assistant Using LangChain and Langgraph framework.

* Developed an AI-powered chatbot assistant for Line using AWS Lambda for serverless backend processing.
* Implemented Retrieval-Augmented Generation (RAG) using LangChain, supporting PDF, URLs, and text files as knowledge sources.
* Integrated Qdrant as the vector database for embedding storage, utilizing Cohere’s embedding and reranking models for enhanced retrieval.
* Leveraged **DeepSeek R1 Distilled Llama 70B** and **Meta’s Llama-3 70B** as the primary LLM for intelligent responses.
* Designed a chat memory mechanism using AWS DynamoDB to maintain conversation context per user.

Here is my workflow:

![image](https://github.com/ganoliz/LLMChatbot/blob/main/images/rag_flow.png)