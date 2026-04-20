"""Gemini 2.5 Flash provider.

Translates our provider-agnostic types into Gemini's SDK types, calls
the model, and translates back.
    messages → contents
    tools → function declarations
    response → text + tool_calls
"""

from __future__ import annotations

import os
import uuid

from google import genai
from google.genai import types

from agent.state import Message, ToolCall, Role
from llm.provider import LLMProvider, LLMResponse
from tools.schema import Tool

class GeminiProvider:
    def __init__(
        self,
        model:str="gemini-2.5-flash",
        api_key:str|None=None,    
    )->None:
        self.client=genai.Client(api_key=api_key or os.environ["GEMINI_API_KEY"])
        self.model=model
    
    def complete(
        self,
        system_prompt,
        messages: list[Message],
        tools: list[Tool],
    )->LLMResponse:
        """Send the conversation + tool definitions, get the next turn."""
        contents=_message_to_contents(messages)
        tool_config=[types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name=t.name,
                description=t.description,
                parameters=t.parameters_schema
            ) for t in tools
        ])] if tools else None
        
        response=self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=tool_config
            )
        )
        
        return _response_to_llm_response(response)
    
def _message_to_contents(messages:list[Message])->list[types.Content]:
    """Our Message list -> Gemini's Content list.

    Gemini uses roles 'user' and 'model'. Tool results go in as 'user'
    role with a function_response part. Assistant tool_call turns become
    'model' role with function_call parts.
    """
    contents:list[types.Content]=[]
    for m in messages:
        if m.role==Role.USER and m.content is not None:
            contents.append(types.Content(role="user", parts=[types.Part(text=m.content)]))
        elif m.role==Role.ASSISTANT:
            parts:list[types.Part]=[]
            if m.content:
                parts.append(types.Part(text=m.content))
            for tc in m.tool_call:
                parts.append(types.Part(function_call=types.FunctionCall(
                    name=tc.name,
                    args=tc.arguments
                )))
            contents.append(types.Content(role="model", parts=parts))
        elif m.role==Role.TOOL and m.tool_result is not None:
            contents.append(types.Content(
                role="user", 
                parts=[types.Part(function_response=types.FunctionResponse(
                    name=m.tool_result.tool_call_id.split(":", 1)[0],
                    response={
                        "result": m.tool_result.content, 
                        "is_error": m.tool_result.is_error
                    },
                ))]
            ))
    return contents

def _response_to_llm_response(response:types.GenerateContentResponse)->LLMResponse:
    """Convert a Gemini GenerateContentResponse to a normalized LLMResponse.

    Iterates over the first candidate's content parts, collecting text into a
    single joined string and mapping function_call parts to ToolCall objects.
    Returns early with stop_reason="No candidates" when the response contains
    no candidates.
    """
    text_parts:list[str]=[]
    tool_calls:list[ToolCall]=[]
    
    if not response.candidates:
        return LLMResponse(
            text=None,
            tool_calls=tool_calls,
            stop_reason="No candidates"
        )
        
    candidate=response.candidates[0]
    for part in candidate.content.parts:
        if part.function_call:
            tool_calls.append(
                ToolCall(
                    id=f"{part.function_call.name}:{uuid.uuid4().hex[:8]}",
                    name=part.function_call.name,
                    arguments=dict(part.function_call.args),
                )
            )
        elif part.text:
            text_parts.append(part.text)

    return LLMResponse(
        text="\n".join(text_parts) if text_parts else None,
        tool_calls=tool_calls,
        stop_reason=str(candidate.finish_reason),
    )

