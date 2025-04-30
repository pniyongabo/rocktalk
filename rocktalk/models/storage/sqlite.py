import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from models.interfaces import ChatMessage, ChatSession, ChatTemplate, LLMConfig
from utils.datetime_utils import format_datetime, parse_datetime
from utils.log import logger

from .storage_interface import SearchOperator, StorageInterface


class SQLiteChatStorage(StorageInterface):
    def __init__(self, db_path: str = "chat_database.db") -> None:
        # Ensure database directory exists
        Path(db_path).parent.mkdir(exist_ok=True, parents=True)
        self.db_path = db_path
        self.init_db()

    def _migrate_db(self) -> None:
        """Handle database migrations"""
        with self.get_connection() as conn:
            # Check for schema version table
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='schema_version'
                """
            )
            schema_table_exists = cursor.fetchone() is not None

            if not schema_table_exists:
                # Create schema version table if it doesn't exist
                conn.execute(
                    """
                    CREATE TABLE schema_version (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMP NOT NULL
                    )
                    """
                )
                # Insert initial version
                conn.execute(
                    """
                    INSERT INTO schema_version (version, applied_at)
                    VALUES (0, ?)
                    """,
                    (format_datetime(datetime.now(timezone.utc)),),
                )

            # Get current schema version
            cursor = conn.execute("SELECT MAX(version) as version FROM schema_version")
            row = cursor.fetchone()
            current_version = 0 if row["version"] is None else row["version"]
            target_version = self.CURRENT_SCHEMA_VERSION

            # update to mention whether migration eeded or not
            if current_version == target_version:
                logger.debug(
                    f"SQLite database schema version: == target version ({target_version}). No migration needed."
                )
            else:
                logger.info(
                    f"SQLite database migration needed. Current schema version is: {current_version}; target version: {target_version}"
                )

            # Run migrations sequentially from current to target version
            if current_version < 1 and target_version >= 1:
                self._migrate_to_v1(conn)

            if current_version < 2 and target_version >= 2:
                self._migrate_to_v2(conn)

            # Add token tracking migration
            if current_version < 3 and target_version >= 3:
                self._migrate_to_v3(conn)

    def _migrate_to_v1(self, conn) -> None:
        """Migration for version 1: Adding session columns"""
        logger.info("Migrating database to schema version 1")

        # Check if is_private column exists
        cursor = conn.execute(
            """
            SELECT name FROM pragma_table_info('sessions')
            WHERE name='is_private'
            """
        )
        if not cursor.fetchone():
            logger.info("Adding is_private column to sessions table")
            conn.execute(
                """
                ALTER TABLE sessions
                ADD COLUMN is_private BOOLEAN NOT NULL DEFAULT 0
                """
            )

        # Update schema version
        conn.execute(
            """
            INSERT INTO schema_version (version, applied_at)
            VALUES (1, ?)
            """,
            (format_datetime(datetime.now(timezone.utc)),),
        )

    def _migrate_to_v2(self, conn) -> None:
        """Migration for version 2: Message content format"""
        logger.info("Migrating database to schema version 2")

        # Get all messages
        cursor = conn.execute("SELECT message_id, content FROM messages")
        messages = cursor.fetchall()

        for message in messages:
            message_id = message["message_id"]
            old_content = message["content"]

            try:
                # Try to parse the old content
                content_data = json.loads(old_content)

                # Convert to new format based on content type
                new_content = []

                # Handle different possible legacy formats
                if isinstance(content_data, str):
                    # Simple string content
                    new_content = [{"text": content_data}]
                elif isinstance(content_data, list):
                    # Already a list, check each item's structure
                    for item in content_data:
                        if isinstance(item, str):
                            new_content.append({"text": item})
                        elif isinstance(item, dict):
                            if "text" in item:
                                new_content.append({"text": item["text"]})
                            elif "thinking" in item:
                                new_content.append({"thinking": item["thinking"]})
                            elif "source" in item and item.get("type") == "image":
                                # Handle image data
                                new_content.append(
                                    {
                                        "image_data": item["source"].get("data", ""),
                                        "metadata": {
                                            "format": item["source"].get(
                                                "type", "base64"
                                            ),
                                            "media_type": item["source"].get(
                                                "media_type", "image/jpeg"
                                            ),
                                        },
                                    }
                                )
                else:
                    # Assume it's a dict with a single content element
                    if "text" in content_data:
                        new_content = [{"text": content_data["text"]}]
                    else:
                        # Unknown format, store as text with a warning
                        new_content = [
                            {
                                "text": f"[Content migrated from old format: {old_content[:100]}...]"
                            }
                        ]
                        logger.warning(
                            f"Unknown content format for message {message_id}: {old_content[:100]}..."
                        )

                # Update the message with new format
                conn.execute(
                    "UPDATE messages SET content = ? WHERE message_id = ?",
                    (json.dumps(new_content), message_id),
                )

            except Exception as e:
                # If parsing fails, preserve content as string
                logger.error(f"Error migrating message {message_id}: {str(e)}")
                fallback_content = [
                    {"text": f"[Content migration error: {old_content[:100]}...]"}
                ]
                conn.execute(
                    "UPDATE messages SET content = ? WHERE message_id = ?",
                    (json.dumps(fallback_content), message_id),
                )

        # Update schema version
        conn.execute(
            """
            INSERT INTO schema_version (version, applied_at)
            VALUES (2, ?)
            """,
            (format_datetime(datetime.now(timezone.utc)),),
        )

    def _migrate_to_v3(self, conn) -> None:
        """Migration for version 3: Separate token tracking"""
        logger.info("Migrating database to schema version 3")

        try:
            # First check if the sessions table has the target columns already
            cursor = conn.execute(
                """
                SELECT 
                    COUNT(*) as col_count 
                FROM pragma_table_info('sessions') 
                WHERE name IN ('input_tokens_used', 'output_tokens_used')
                """
            )
            existing_columns = cursor.fetchone()["col_count"]
            
            # Check if total_tokens_used exists
            cursor = conn.execute(
                """
                SELECT name FROM pragma_table_info('sessions')
                WHERE name='total_tokens_used'
                """
            )
            has_total_tokens = cursor.fetchone() is not None
            
            if existing_columns == 2 and not has_total_tokens:
                # Migration already completed
                logger.info("Token columns already exist in proper format, skipping v3 migration")
            else:
                # We need to rebuild the table
                logger.info("Rebuilding sessions table with new token columns")
                
                # Create new table with correct schema
                conn.execute(
                    """
                    CREATE TABLE sessions_new (
                        session_id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        last_active TIMESTAMP NOT NULL,
                        config TEXT NOT NULL,
                        is_private BOOLEAN NOT NULL DEFAULT 0,
                        input_tokens_used INTEGER NOT NULL DEFAULT 0,
                        output_tokens_used INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
                
                # If total_tokens_used exists, use it for input_tokens_used
                if has_total_tokens:
                    conn.execute(
                        """
                        INSERT INTO sessions_new
                        SELECT
                            session_id,
                            title,
                            created_at,
                            last_active,
                            config,
                            COALESCE(is_private, 0),
                            COALESCE(total_tokens_used, 0),
                            0
                        FROM sessions
                        """
                    )
                else:
                    # No total_tokens_used column, do a clean migration
                    conn.execute(
                        """
                        INSERT INTO sessions_new
                        SELECT
                            session_id,
                            title,
                            created_at,
                            last_active,
                            config,
                            COALESCE(is_private, 0),
                            0,
                            0
                        FROM sessions
                        """
                    )
                
                # Replace old table with new one
                conn.execute("DROP TABLE sessions")
                conn.execute("ALTER TABLE sessions_new RENAME TO sessions")
            
            # Update schema version
            conn.execute(
                """
                INSERT INTO schema_version (version, applied_at)
                VALUES (3, ?)
                """,
                (format_datetime(datetime.now(timezone.utc)),),
            )
            
        except Exception as e:
            logger.error(f"Migration to v3 failed: {str(e)}")
            raise e
    @contextmanager
    def get_connection(self):
        """Create a new connection with row factory for dict results"""
        conn = None
        try:
            # Attempt to create a connection
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                yield cursor  # Provide the cursor to the calling context
                conn.commit()  # Commit the transaction if no exceptions occur
            except Exception as e:
                conn.rollback()  # Roll back the transaction on exception
                raise RuntimeError(
                    f"Failed to execute query on database at {self.db_path}: {str(e)}"
                ) from e
        except Exception as e:
            # Handle exceptions during connection setup
            raise RuntimeError(
                f"Failed to connect to database at {self.db_path}: {str(e)}"
            ) from e
        finally:
            # Ensure the connection is closed if it was successfully opened
            if conn:
                conn.close()

    def init_db(self) -> None:
        """Initialize database schema"""
        # Set restrictive permissions on the database file if it doesn't exist
        db_file = Path(self.db_path)
        if not db_file.exists():
            # Create empty file with restrictive permissions
            db_file.touch(
                mode=0o600
            )  # Read/write for owner only (equivalent to chmod 600)
        else:
            # Update permissions on existing file
            db_file.chmod(0o600)

        with self.get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    last_active TIMESTAMP NOT NULL,
                    config TEXT NOT NULL,
                    is_private BOOLEAN NOT NULL DEFAULT 0,
                    input_tokens_used INTEGER NOT NULL DEFAULT 0,
                    output_tokens_used INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    message_index INTEGER NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                    UNIQUE(session_id, message_index)  -- Ensure unique indexes per session
                );

                CREATE TABLE IF NOT EXISTS templates (
                        template_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        description TEXT NOT NULL,
                        config TEXT NOT NULL,
                        is_default BOOLEAN NOT NULL DEFAULT 0
                    );

                -- Indexes for better search performance

                CREATE INDEX IF NOT EXISTS idx_sessions_last_active
                ON sessions(last_active);

                CREATE INDEX IF NOT EXISTS idx_messages_session_id
                ON messages(session_id, message_index);

                CREATE INDEX IF NOT EXISTS idx_messages_timestamp
                ON messages(timestamp);

                CREATE INDEX IF NOT EXISTS idx_templates_name
                ON templates(name);
            """
            )
            self.initialize_preset_templates()
            self._migrate_db()

    def store_session(self, session: ChatSession) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions
                (session_id, title, created_at, last_active, config, is_private, input_tokens_used, output_tokens_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session.session_id,
                    session.title,
                    format_datetime(session.created_at),
                    format_datetime(session.last_active),
                    session.config.model_dump_json(),
                    session.is_private,
                    session.input_tokens_used,
                    session.output_tokens_used,
                ),
            )

    def update_session(self, session: ChatSession) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET title = ?, last_active = ?, config = ?, is_private = ?, input_tokens_used = ?, output_tokens_used = ?
                WHERE session_id = ?
            """,
                (
                    session.title,
                    format_datetime(session.last_active),
                    json.dumps(session.config.model_dump()),
                    session.is_private,
                    session.input_tokens_used,
                    session.output_tokens_used,
                    session.session_id,
                ),
            )

    def save_message(self, message: ChatMessage) -> None:
        """Save a message to a chat session and update last_active"""
        with self.get_connection() as conn:
            # allow db to autoincrement message_id
            conn.execute(
                """
                INSERT INTO messages
                (session_id, role, content, message_index, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    message.session_id,
                    message.role,
                    message.serialize_message_content(),
                    message.index,
                    format_datetime(message.created_at),
                ),
            )
            # Update session's last_active timestamp
            conn.execute(
                """
                UPDATE sessions
                SET last_active = ?
                WHERE session_id = ?
            """,
                (format_datetime(message.created_at), message.session_id),
            )

    def delete_messages_from_index(self, session_id: str, from_index: int) -> None:
        """Delete all messages with index >= from_index for the given session."""
        with self.get_connection() as conn:
            conn.execute(
                """
                DELETE FROM messages
                WHERE session_id = ? AND message_index >= ?
                """,
                (session_id, from_index),
            )

    def delete_message(self, session_id: str, index: int) -> None:
        """Delete a specific message by its index from a chat session."""
        with self.get_connection() as conn:
            try:
                # Start a transaction
                conn.execute("BEGIN TRANSACTION")

                # Delete the specific message
                result = conn.execute(
                    """
                    DELETE FROM messages
                    WHERE session_id = ? AND message_index = ?
                    """,
                    (session_id, index),
                )

                # Check if a message was actually deleted
                if result.rowcount == 0:
                    raise ValueError(
                        f"No message found with index {index} in session {session_id}"
                    )

                # Update indexes of subsequent messages
                conn.execute(
                    """
                    UPDATE messages
                    SET message_index = message_index - 1
                    WHERE session_id = ? AND message_index > ?
                    """,
                    (session_id, index),
                )

                # Update session's last_active timestamp
                conn.execute(
                    """
                    UPDATE sessions
                    SET last_active = ?
                    WHERE session_id = ?
                    """,
                    (format_datetime(datetime.now(timezone.utc)), session_id),
                )

                # Commit the transaction
                conn.execute("COMMIT")
            except Exception as e:
                # If any error occurs, rollback the transaction
                conn.execute("ROLLBACK")
                raise e

    def _deserialize_message(self, row: sqlite3.Row) -> ChatMessage:
        """Deserialize a message from the database row"""
        return ChatMessage.create(
            message_id=row["message_id"],
            session_id=row["session_id"],
            role=row["role"],
            content=ChatMessage.deserialize_message_content(row["content"]),
            index=row["message_index"],
            created_at=parse_datetime(row["timestamp"]),
        )

    def _deserialize_session(self, row: sqlite3.Row) -> ChatSession:
        """Deserialize a session from the database row"""
        session_data = dict(row)
        return ChatSession(
            session_id=session_data["session_id"],
            title=session_data["title"],
            created_at=parse_datetime(session_data["created_at"]),
            last_active=parse_datetime(session_data["last_active"]),
            config=LLMConfig.model_validate_json(session_data["config"], strict=True),
            is_private=bool(session_data.get("is_private", False)),
            input_tokens_used=session_data.get("input_tokens_used", 0),
            output_tokens_used=session_data.get("output_tokens_used", 0),
        )

    def get_messages(self, session_id: str) -> List[ChatMessage]:
        """Get all messages for a session"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM messages
                WHERE session_id = ?
                ORDER BY timestamp
            """,
                (session_id,),
            )
            return [self._deserialize_message(row) for row in cursor.fetchall()]

    def search_sessions(
        self,
        query: List[str],
        operator: SearchOperator = SearchOperator.AND,
        search_titles: bool = True,
        search_content: bool = True,
        date_range: Optional[Tuple[datetime, datetime]] = None,
    ) -> List[ChatSession]:
        """Search sessions with multi-term support"""
        with self.get_connection() as conn:
            query_conditions = []
            params = []

            # Build query for each search term
            for term in query:
                term_conditions = []
                search_pattern = f"%{term}%"

                if search_titles:
                    term_conditions.append("s.title LIKE ?")
                    params.append(search_pattern)

                if search_content:
                    # For single string content
                    term_conditions.append(
                        "(json_type(m.content) = 'text' AND m.content LIKE ?)"
                    )
                    params.append(search_pattern)

                    # For array content items
                    term_conditions.append(
                        """
                        (json_type(m.content) = 'array' AND
                        EXISTS (
                            SELECT 1
                            FROM json_each(m.content) as items
                            WHERE
                                (json_extract(items.value, '$.text') LIKE ? AND json_extract(items.value, '$.text') IS NOT NULL) OR
                                (json_extract(items.value, '$.thinking') LIKE ? AND json_extract(items.value, '$.thinking') IS NOT NULL)
                        ))
                        """
                    )
                    params.append(search_pattern)
                    params.append(search_pattern)

                # Combine conditions for this term
                term_query = f"({' OR '.join(term_conditions)})"
                query_conditions.append(term_query)

            # Combine all term conditions with AND/OR
            where_clause = f" {operator} ".join(query_conditions)

            # Add date range if specified
            date_conditions = []
            if date_range:
                start_date, end_date = date_range
                if start_date and end_date:
                    date_conditions.append("m.timestamp BETWEEN ? AND ?")
                    params.extend(
                        [
                            format_datetime(start_date),
                            format_datetime(end_date),
                        ]
                    )
                elif start_date:
                    date_conditions.append("m.timestamp >= ?")
                    params.append(format_datetime(start_date))
                elif end_date:
                    date_conditions.append("m.timestamp <= ?")
                    params.append(format_datetime(end_date))

            if date_conditions:
                where_clause = f"({where_clause}) AND ({' AND '.join(date_conditions)})"

            command_str = f"""
                SELECT DISTINCT
                    s.*,
                    MAX(m.timestamp) as last_message,
                    COUNT(m.message_id) as message_count
                FROM sessions s
                LEFT JOIN messages m ON s.session_id = m.session_id
                WHERE {where_clause}
                GROUP BY s.session_id
                ORDER BY MAX(m.timestamp) DESC NULLS LAST
                """

            cursor = conn.execute(command_str, params)
            return [self._deserialize_session(row) for row in cursor.fetchall()]

    def get_active_sessions_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[ChatSession]:
        """Get sessions that have messages within the date range"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT DISTINCT
                    s.*,
                    MIN(m.timestamp) as first_message,
                    MAX(m.timestamp) as last_message,
                    COUNT(m.message_id) as message_count
                FROM sessions s
                INNER JOIN messages m ON s.session_id = m.session_id
                WHERE m.timestamp BETWEEN ? AND ?
                GROUP BY s.session_id
                ORDER BY MAX(m.timestamp) DESC
            """,
                (format_datetime(start_date), format_datetime(end_date)),
            )
            return [self._deserialize_session(row) for row in cursor.fetchall()]

    def get_session(self, session_id: str) -> ChatSession:
        """Get a specific chat session"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM sessions
                WHERE session_id = ?
                """,
                (session_id,),
            )
            row = cursor.fetchone()
            if row:
                return self._deserialize_session(row)
            else:
                raise ValueError(f"No session found with id {session_id}")

    def get_recent_sessions(
        self, limit: int = 10, include_private=False
    ) -> List[ChatSession]:
        """Get most recently active sessions"""
        with self.get_connection() as conn:
            query = """
                SELECT s.*,
                    (SELECT COUNT(*) FROM messages WHERE messages.session_id = s.session_id) as message_count,
                    (SELECT MIN(timestamp) FROM messages WHERE messages.session_id = s.session_id) as first_message,
                    (SELECT MAX(timestamp) FROM messages WHERE messages.session_id = s.session_id) as last_message
                FROM sessions s
                {where_clause}
                ORDER BY last_active DESC
                LIMIT ?
                """

            if not include_private:
                # Only include non-private sessions
                where_clause = "WHERE (s.is_private = 0 OR s.is_private IS NULL)"
                query = query.format(where_clause=where_clause)
            else:
                # Include all sessions
                query = query.format(where_clause="")

            cursor = conn.execute(query, (limit,))
            return [self._deserialize_session(row) for row in cursor.fetchall()]

    def rename_session(self, session_id: str, new_title: str) -> None:
        """Rename a chat session"""
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET title = ?, last_active = ?
                WHERE session_id = ?
            """,
                (
                    new_title,
                    format_datetime(datetime.now(timezone.utc)),
                    session_id,
                ),
            )

    def delete_session(self, session_id: str) -> None:
        """Delete a session and its messages"""
        with self.get_connection() as conn:
            try:
                # Start a transaction
                conn.execute("BEGIN TRANSACTION")

                # Delete all messages associated with the session
                conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))

                # Delete the session itself
                result = conn.execute(
                    "DELETE FROM sessions WHERE session_id = ?", (session_id,)
                )

                # Check if a session was actually deleted
                if result.rowcount == 0:
                    raise ValueError(f"No session found with id {session_id}")

                # Commit the transaction
                conn.execute("COMMIT")
            except Exception as e:
                # If any error occurs, rollback the transaction
                conn.execute("ROLLBACK")
                raise e  # Re-raise the exception after rollback

    def delete_all_sessions(self) -> None:
        """Delete all chat sessions and their messages"""
        with self.get_connection() as conn:
            try:
                # Start a transaction
                conn.execute("BEGIN TRANSACTION")

                # Delete all messages first (due to foreign key constraint)
                conn.execute("DELETE FROM messages")

                # Delete all sessions
                conn.execute("DELETE FROM sessions")

                # Commit the transaction
                conn.execute("COMMIT")
            except Exception as e:
                # If any error occurs, rollback the transaction
                conn.execute("ROLLBACK")
                raise RuntimeError(f"Failed to delete all sessions: {str(e)}")

    def _deserialize_template(self, row: sqlite3.Row) -> ChatTemplate:
        """Deserialize a template from the database row"""
        return ChatTemplate(
            template_id=row["template_id"],
            name=row["name"],
            description=row["description"],
            config=LLMConfig.model_validate_json(row["config"], strict=True),
        )

    def store_chat_template(self, template: ChatTemplate) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO templates
                (template_id, name, description, config, is_default)
                VALUES (?, ?, ?, ?, 0)
                """,
                (
                    template.template_id,
                    template.name,
                    template.description,
                    template.config.model_dump_json(),
                ),
            )

    def initialize_preset_templates(self) -> None:
        """Initialize default preset templates if they don't exist"""
        with self.get_connection() as conn:
            # Check if any templates exist
            cursor = conn.execute("SELECT COUNT(*) as count FROM templates")
            templates_count = cursor.fetchone()["count"]

            # Check if a default template exists
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM templates WHERE is_default = 1"
            )
            default_count = cursor.fetchone()["count"]

            if templates_count == 0:
                # No templates exist, initialize presets
                presets = super().get_preset_templates()
                for template in presets:
                    self.store_chat_template(template)
                # Set first preset as default
                self.set_default_template(presets[0].template_id)
            elif default_count == 0:
                # Templates exist but no default set, set first template as default
                cursor = conn.execute(
                    "SELECT template_id FROM templates ORDER BY name LIMIT 1"
                )
                first_template = cursor.fetchone()
                if first_template:
                    self.set_default_template(first_template["template_id"])

    def get_chat_template_by_id(self, template_id: str) -> ChatTemplate:
        """Get a specific chat template by id"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM templates
                WHERE template_id = ?
                """,
                (template_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"No template found with id {template_id}")
            return self._deserialize_template(row)

    def get_chat_template_by_name(self, template_name: str) -> ChatTemplate:
        """Get a specific chat template by name"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM templates
                WHERE name = ?
                """,
                (template_name,),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"No template found with name {template_name}")
            return self._deserialize_template(row)

    def get_chat_templates(self) -> List[ChatTemplate]:
        """Get all chat templates"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM templates
                ORDER BY name
                """
            )
            return [self._deserialize_template(row) for row in cursor.fetchall()]

    def update_chat_template(self, template: ChatTemplate) -> None:
        """Update an existing chat template"""
        with self.get_connection() as conn:
            result = conn.execute(
                """
                UPDATE templates
                SET name = ?, description = ?, config = ?
                WHERE template_id = ?
                """,
                (
                    template.name,
                    template.description,
                    template.config.model_dump_json(),
                    template.template_id,
                ),
            )
            if result.rowcount == 0:
                raise ValueError(f"No template found with id {template.template_id}")

    def delete_chat_template(self, template_id: str) -> None:
        """Delete a chat template"""
        with self.get_connection() as conn:
            result = conn.execute(
                """
                DELETE FROM templates
                WHERE template_id = ?
                """,
                (template_id,),
            )
            if result.rowcount == 0:
                raise ValueError(f"No template found with id {template_id}")

    def set_default_template(self, template_id: str) -> None:
        """Set a template as the default

        Args:
            template_id: ID of the template to set as default

        Raises:
            ValueError: If template_id doesn't exist
        """
        with self.get_connection() as conn:
            try:
                conn.execute("BEGIN TRANSACTION")

                # Verify template exists
                cursor = conn.execute(
                    "SELECT 1 FROM templates WHERE template_id = ?",
                    (template_id,),
                )
                if not cursor.fetchone():
                    raise ValueError(f"No template found with id {template_id}")

                # Clear existing default
                conn.execute("UPDATE templates SET is_default = 0")

                # Set new default
                result = conn.execute(
                    "UPDATE templates SET is_default = 1 WHERE template_id = ?",
                    (template_id,),
                )

                conn.execute("COMMIT")

            except Exception as e:
                conn.execute("ROLLBACK")
                raise e

    def get_default_template(self) -> ChatTemplate:
        """Get the current default template

        Returns:
            The default template if one is set, raise otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM templates
                WHERE is_default = 1
                """
            )
            try:
                row = cursor.fetchone()
                return self._deserialize_template(row)
            except Exception as e:
                raise e
