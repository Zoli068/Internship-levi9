from .avg_aqi_report_system_prompt import AVG_AQI_REPORT_SYSTEM_PROMPT

LLM_STATE = {
    "Type": "Task",
    "Resource": "arn:aws:states:::bedrock:invokeModel",
    "Parameters": {
        "ModelId": "arn:aws:bedrock:eu-central-1::inference-profile/eu.amazon.nova-lite-v1:0",
        "Body": {
            "schemaVersion": "messages-v1",
            "system": [{"text": AVG_AQI_REPORT_SYSTEM_PROMPT}],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text.$": "States.Format('You are an AI assistant. Analyze the following air quality data and return text message only as one big string, no other wrapper or anything around this text. DATA:{}', $.lambda_output.data_for_llm)"
                        }
                    ],
                }
            ],
            "inferenceConfig": {
                "maxTokens": 2000,
                "temperature": 0.2,
                "topP": 0.9,
            },
        },
    },
    "ResultSelector": {"text.$": "$.Body.output.message.content[0].text"},
    "ResultPath": "$.summary_text",
}
