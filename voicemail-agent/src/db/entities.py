from sqlmodel import Field, SQLModel
from typing import Optional

class Conversation(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = Field(unique=True)
    
class UserInfo(SQLModel, table=True):
    id: str = Field(primary_key=True)
    personality_json: str