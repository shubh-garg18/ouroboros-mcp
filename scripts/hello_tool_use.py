"""
One shot verification that Gemini tool-calling works.
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client=genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# Define a schema for the tool
calculator_declaration ={
    "name": "calculator",
    "description": "A simple calculator which evaluates a basic arithmetic expression.",
    "parameters": {
        "type":"object",
        "properties": {
            "expression":{
                "type": "string",
                "description": "The arithmetic expression to evaluate."
            }
        },
        "required": ["expression"]
    }
}

# Define one tool with a clear schema
calculator = types.Tool(function_declarations=[calculator_declaration])

# Model the response
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="what is 17 times 23",
    config=types.GenerateContentConfig(tools=[calculator])
)

# Print response
for candidate in response.candidates:
    for part in candidate.content.parts:
        if part.function_call:
            print(f"Tool requested: {part.function_call.name}")
            print(f"Args: {dict(part.function_call.args)}")
            expression = part.function_call.args["expression"]
            result = eval(expression)
            print(f"Executed result: {result}")
        elif part.text:
            print(f"Text: {part.text}")