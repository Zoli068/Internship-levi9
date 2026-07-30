import os
import json
import boto3
from typing import Any

bedrock_client = boto3.client('bedrock-agent-runtime')

agent_id = os.environ.get("BEDROCK_AGENT_ID")
agent_alias_id = os.environ.get("BEDROCK_AGENT_ALIAS_ID")


def handler(event, _context) -> dict[str, Any]:
    connection_id = event['requestContext']['connectionId']
    callback_url = os.environ['CALLBACK_URL']
    
    apigw_management = boto3.client('apigatewaymanagementapi', endpoint_url=callback_url)

    try:
        body = json.loads(event.get('body', '{}'))
        question_text = body.get('questionText')
        session_id = body.get('sessionID')

        if not question_text or not session_id:
            apigw_management.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({"error": "Missing questionText or sessionID"})
            )
            return {"statusCode": 400}  


        ai_response_text = ""

        response = bedrock_client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=question_text
        )
        
        #bedrock response is stream response, so we need to wait it
        event_stream = response.get("completion")
        
        if event_stream:
            for chunk_event in event_stream:
                if "chunk" in chunk_event:
                    chunk_bytes = chunk_event["chunk"]["bytes"]
                    ai_response_text += chunk_bytes.decode("utf-8")
        else:
            ai_response_text = "Agent doesn't generated any response"

        response_body = {
            "sessionID": session_id,
            "answerText": ai_response_text
        }

        apigw_management.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(response_body)
        )

    except Exception as e:
        try:
            apigw_management.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({"error": f"Internal error: {str(e)}"})
            )
        except Exception:
            # User closed connection
            pass 

    return {"statusCode": 200}