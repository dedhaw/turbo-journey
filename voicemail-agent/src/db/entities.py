from sqlmodel import Field, SQLModel
from typing import Optional

class Conversation(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = Field(unique=True)
    notes: list
    
class UserInfo(SQLModel, table=True):
    id: str = Field(primary_key=True)
    first_name: str
    last_name: str