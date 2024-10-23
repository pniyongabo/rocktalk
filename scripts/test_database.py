from datetime import datetime, timedelta
from rocktalk.storage.sqlite_storage import SQLiteChatStorage
import random
from typing import List, Tuple, Dict

class TestDataGenerator:
    def __init__(self, reference_date: datetime = datetime(2024, 10, 22)):
        """
        Initialize the generator with a reference date (default: Oct 22, 2024)
        """
        self.reference_date = reference_date
        self.sample_conversations = {
            "tech_support": [
                ("user", "How do I fix my printer?"),
                ("assistant", "Let's try some basic troubleshooting. Is it connected and powered on?"),
                ("user", "Yes, but it's not printing"),
                ("assistant", "Try turning it off and on, then check if there are any error messages.")
            ],
            "python_help": [
                ("user", "Can you help me with Python lists?"),
                ("assistant", "Sure! Lists are ordered collections in Python. What would you like to know?"),
                ("user", "How do I add items?"),
                ("assistant", "You can use .append() to add single items or .extend() for multiple items.")
            ],
            "casual_chat": [
                ("user", "How's your day going?"),
                ("assistant", "I'm functioning well! How can I help you today?"),
                ("user", "Just wanted to chat"),
                ("assistant", "That's nice! I'm always happy to engage in conversation.")
            ],
            "book_recommendation": [
                ("user", "Can you recommend a good sci-fi book?"),
                ("assistant", "Have you read 'Project Hail Mary' by Andy Weir?"),
                ("user", "No, what's it about?"),
                ("assistant", "It's about a lone astronaut who wakes up in space with amnesia. It's full of science and problem-solving.")
            ]
        }

    def generate_date_points(self) -> List[Dict]:
        """
        Generate a list of dates with their descriptions
        """
        ref_date = self.reference_date
        return [
            {
                "date": ref_date - timedelta(days=3),
                "desc": "Recent - Few days ago"
            },
            {
                "date": ref_date - timedelta(weeks=2),
                "desc": "Recent - Couple weeks ago"
            },
            {
                "date": ref_date - timedelta(days=45),
                "desc": "Month and a half ago"
            },
            {
                "date": ref_date - timedelta(days=90),
                "desc": "Three months ago"
            },
            {
                "date": ref_date - timedelta(days=180),
                "desc": "Six months ago"
            },
            {
                "date": ref_date - timedelta(days=270),
                "desc": "Nine months ago"
            },
            {
                "date": ref_date - timedelta(days=365),
                "desc": "One year ago"
            },
            {
                "date": ref_date - timedelta(days=456),
                "desc": "15 months ago"
            }
        ]

    def create_test_database(self, db_path: str = "test_chat_database.db"):
        """
        Create a test database with sample conversations
        """
        storage = SQLiteChatStorage(db_path)
        dates = self.generate_date_points()
        
        for date_info in dates:
            date = date_info["date"]
            desc = date_info["desc"]
            
            # Create 1-2 sessions per date point
            for session_num in range(random.randint(1, 2)):
                conv_type = random.choice(list(self.sample_conversations.keys()))
                conversation = self.sample_conversations[conv_type]
                
                # Create session with historical timestamp
                session_id = storage.create_session(
                    title=f"Chat {date.strftime('%Y-%m-%d')} - {conv_type}",
                    subject=f"Sample {desc}",
                    metadata={
                        "test_data": True,
                        "conversation_type": conv_type,
                        "generated_on": date.isoformat()  # Use historical date instead of now()
                    },
                    created_at=date,  # Add created_at parameter
                    last_active=date  # Add last_active parameter
                )

                # Add messages with timestamps spaced a few minutes apart
                message_time = date
                for role, content in conversation:
                    storage.save_message(
                        session_id=session_id,
                        role=role,
                        content=content,
                        metadata={
                            "timestamp": message_time.isoformat(),
                            "conversation_type": conv_type
                        },
                        created_at=message_time  # Add created_at parameter for messages
                    )
                    message_time += timedelta(minutes=random.randint(1, 5))

        return storage


def create_sample_database(reference_date: datetime = None, db_path: str = "test_chat_database.db"):
    """
    Convenience function to create a sample database
    """
    if reference_date is None:
        reference_date = datetime(2024, 10, 22)  # Default reference date
    
    generator = TestDataGenerator(reference_date)
    return generator.create_test_database(db_path)

if __name__ == "__main__":
    # Example usage:
    # Create with default reference date (Oct 22, 2024)
    storage = create_sample_database(db_path="chat_database.db")
    
    # # Create with custom reference date
    # custom_date = datetime(2024, 12, 25)  # Christmas 2024
    # storage = create_sample_database(custom_date, "christmas_test.db")
    
    print("Test databases created successfully!")
