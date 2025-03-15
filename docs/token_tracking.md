# Token Tracking Implementation Plan

## Overview

The current context window size is determined by the input_tokens field in AI response metadata. This represents how many tokens were used for the entire context, including:
- System message (if any)
- All previous messages in the conversation
- Current user message

## Model Changes

### ChatSession Updates
```python
class ChatSession:
    # Existing fields...
    cumulative_input_tokens: int    # Total input tokens used (keeps increasing)
    cumulative_output_tokens: int   # Total output tokens generated (keeps increasing)
    current_context_tokens: int     # From last AI response input_tokens
```

## Token Tracking Logic

### Update Session Tokens
```python
def _update_session_tokens(self, input_tokens: int, output_tokens: int, session_id: Optional[str] = None):
    """Update token counts from AI response metadata
    
    Args:
        input_tokens: Number of input tokens used for this response's context
        output_tokens: Number of output tokens generated
        session_id: Optional session ID. If None, uses current session.
    """
    # Update cumulative counts (these only increase)
    session.cumulative_input_tokens += input_tokens
    session.cumulative_output_tokens += output_tokens
    
    # Update current context size from this response
    session.current_context_tokens = input_tokens
```

### After Message Deletion
```python
def update_context_after_deletion(session: ChatSession):
    """Update context size after message deletion by making a small request
    
    We need to make a request to get an accurate context size after deletion.
    This could be a minimal prompt like "Continue" that will return the 
    new context size in its response metadata.
    """
    # Convert remaining messages to LLM format
    messages = self.convert_messages_to_llm_format(session)
    
    # Make a minimal request to get new context size
    response = self._llm.invoke(
        input=[*messages, HumanMessage(content="Continue")]
    )
    
    # Extract new context size from metadata
    if (
        hasattr(response, "additional_kwargs")
        and "usage_metadata" in response.additional_kwargs
    ):
        usage_data = response.additional_kwargs["usage_metadata"]
        token_usage = self._extract_token_usage(usage_data)
        
        # Update session with new context size
        session.current_context_tokens = token_usage["input_tokens"]
```

## Implementation Steps

1. Update ChatSession in interfaces.py:
   - Rename token fields for clarity
   - Add current_context_tokens field
   - Add validation and default values

2. Modify token tracking in llm.py:
   - Update _update_session_tokens() to track both cumulative and current tokens
   - Add method to update context size after deletions
   - Update token usage statistics reporting

3. Handle message deletions:
   - Keep cumulative token counts unchanged
   - Make minimal request to get new context size
   - Update context window usage percentage

4. Update UI:
   - Show cumulative input/output totals
   - Display current context size
   - Add warnings when approaching context limits

## Benefits

- Accurate context size tracking using response metadata
- Proper handling of message deletions
- Clear separation between cumulative and current usage
- Efficient updates only when needed

## Implementation Notes

- Current context size comes from AI response metadata
- Cumulative totals never decrease
- After deletion, need a small request to get new context size
- UI should clearly show:
  * Total tokens used (cumulative input + output)
  * Current context size
  * Remaining context window space