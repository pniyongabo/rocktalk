# Message-Based Token Tracking Implementation

## Overview

Currently, token tracking is done at the session level, with cumulative input and output tokens stored in the ChatSession model. This enhancement adds token tracking at the individual message level, making it easier to:
- Calculate context window usage up to any point
- Handle message editing and deletion
- Maintain accurate token counts

## Database Changes

### Messages Table Update
```sql
ALTER TABLE messages
ADD COLUMN input_tokens INTEGER NOT NULL DEFAULT 0,
ADD COLUMN output_tokens INTEGER NOT NULL DEFAULT 0;
```

### Migration Strategy
1. Add columns with default value 0
2. Existing messages will have 0 token counts
3. New messages will track tokens accurately

## Model Changes

### ChatMessage Class
```python
class ChatMessage(BaseModel):
    # Existing fields...
    input_tokens: int = Field(default=0, description="Number of input tokens for this message")
    output_tokens: int = Field(default=0, description="Number of output tokens for this message")

    @property
    def total_tokens(self) -> int:
        """Total tokens used by this message."""
        return self.input_tokens + self.output_tokens

    def calculate_cumulative_tokens(self, messages: List["ChatMessage"]) -> tuple[int, int]:
        """Calculate cumulative tokens up to and including this message.
        
        Args:
            messages: List of all messages in chronological order
            
        Returns:
            Tuple of (cumulative_input_tokens, cumulative_output_tokens)
        """
        cumulative_input = 0
        cumulative_output = 0
        
        for msg in messages:
            if msg.index <= self.index:
                cumulative_input += msg.input_tokens
                cumulative_output += msg.output_tokens
                
        return cumulative_input, cumulative_output
```

### Token Usage Updates

#### Message Creation
```python
@staticmethod
def create(
    role: str,
    content: List[ChatContentItem],
    index: int,
    session_id: Optional[str] = None,
    message_id: Optional[int] = None,
    created_at: Optional[datetime] = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> "ChatMessage":
    """Create a new ChatMessage with token tracking."""
    return ChatMessage(
        message_id=message_id or len(st.session_state.messages),
        session_id=session_id or "",
        role=role,
        content=content,
        index=index,
        created_at=created_at or datetime.now(timezone.utc),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
```

## Implementation Steps

1. Database Migration
- Create migration script to add token columns
- Update SQLite storage implementation

2. Model Updates
- Add token fields to ChatMessage
- Update creation and serialization methods
- Add token calculation methods

3. LLM Integration
- Update BedrockLLM to set token counts on messages
- Modify stream() and invoke() methods
- Update session token calculations

4. Message Operations
- Update message editing to recalculate tokens
- Handle token updates during message deletion
- Add methods to recalculate session totals

## Usage Examples

### Calculate Context Window
```python
def get_context_window_usage(messages: List[ChatMessage], up_to_index: int) -> int:
    """Calculate total tokens used up to a specific message index."""
    total_input = 0
    total_output = 0
    
    for msg in messages:
        if msg.index <= up_to_index:
            total_input += msg.input_tokens
            total_output += msg.output_tokens
            
    return total_input + total_output
```

### Update Session Tokens
```python
def recalculate_session_tokens(session_id: str, storage: StorageInterface) -> None:
    """Recalculate session token totals from message-level counts."""
    messages = storage.get_messages(session_id)
    session = storage.get_session(session_id)
    
    total_input = sum(msg.input_tokens for msg in messages)
    total_output = sum(msg.output_tokens for msg in messages)
    
    session.input_tokens_used = total_input
    session.output_tokens_used = total_output
    storage.update_session(session)
```

## Benefits

1. Accurate Context Tracking
- Know exactly how many tokens are used up to any point
- Better predict when to start new sessions

2. Improved Message Management
- Accurate token counts after edits/deletions
- No need to estimate token usage

3. Enhanced Rate Limiting
- More precise token usage tracking
- Better session management

## Implementation Notes

1. Token Counting
- Human messages: Count input tokens only
- AI messages: Count output tokens only
- System messages: Count as input tokens

2. Session Updates
- Update session totals after message operations
- Maintain cumulative and current context counts

3. Performance Considerations
- Cache token calculations where appropriate
- Use efficient database queries for token sums

4. Migration
- Handle existing messages gracefully
- Provide utilities for backfilling token counts if needed