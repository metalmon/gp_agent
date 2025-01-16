# OpenRouter Tool Calls Guide

## Key Points
1. Using paid model (google/gemini-flash-1.5) for more reliable tool calls
2. Model works better with markdown/yaml context than XML
3. Response parsing is simpler with this model
4. Tool calls follow OpenAI function calling format

## Context Formatting
Use markdown for context:
```markdown
# Current Context
- User request: {request}
- Available tools: {tool list}
- Previous actions: {actions}

## Tool Details
Each tool has:
- Name
- Description
- Required parameters
```

Or YAML for structured data:
```yaml
context:
  user_request: "What is the weather?"
  available_tools:
    - name: get_weather
      description: "Get weather info"
      parameters:
        - location: "City name"
  previous_actions:
    - tool_call: get_weather
      arguments: 
        location: "Boston"
```

## Request Format

Basic request structure:
```json
{
  "model": "google/gemini-flash-1.5",
  "messages": [],
  "tools": [],
  "tool_choice": "auto"
}
```

Tool definition:
```json
{
  "type": "function",
  "function": {
    "name": "function_name",
    "description": "Function description",
    "parameters": {
      "type": "object",
      "properties": {
        "param1": {
          "type": "string",
          "description": "Parameter description"
        }
      },
      "required": ["param1"]
    }
  }
}
```

## Response Parsing

1. Check choices[0].finish_reason:
   - "tool_calls" - model wants to call a function
   - "STOP" - final response

2. For "tool_calls" response:
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [{
        "id": "tool_id",
        "type": "function",
        "function": {
          "name": "function_name",
          "arguments": "json_string"
        }
      }]
    }
  }]
}
```

3. For "STOP" response:
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Final response",
      "refusal": ""
    }
  }]
}
```

## Important Notes

1. Always include tool_choice: "auto"
2. Function arguments as JSON strings
3. Tool call IDs must be unique
4. Tool responses as JSON strings
5. Model supports markdown in responses
6. Error codes:
   - 404: tools not supported
   - 429: rate limits exceeded
7. Null content means tool call
8. Each call needs tool response
9. Keep message history

## Best Practices

1. Context Formatting:
   - Use markdown for human-readable context
   - Use YAML for structured data
   - Avoid XML formatting
   - Keep context clear and concise

2. Tool Definitions:
   - Clear, specific descriptions
   - Well-defined parameter types
   - Explicit required fields
   - Consistent naming conventions

3. Response Handling:
   - Parse finish_reason first
   - Extract tool calls immediately if present
   - Handle errors gracefully
   - Maintain conversation context

4. Performance:
   - Paid model is more reliable
   - Responses are more predictable
   - Tool calls are more accurate
   - Faster response times

5. Error Handling:
   - Check rate limits
   - Verify tool support
   - Validate JSON responses
   - Monitor refusal field