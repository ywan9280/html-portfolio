'''
models
defines sql alchemy data models
also contains the definition for the room class used to keep track of socket.io rooms

Just a sidenote, using SQLAlchemy is a pain. If you want to go above and beyond, 
do this whole project in Node.js + Express and use Prisma instead, 
Prisma docs also looks so much better in comparison

or use SQLite, if you're not into fancy ORMs (but be mindful of Injection attacks :) )
'''

from sqlalchemy import String, Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column,relationship
from typing import Dict

# data models
class Base(DeclarativeBase):
    pass

# model to store user information
class User(Base):
    __tablename__ = "user"
    
    # looks complicated but basically means
    # I want a username column of type string,
    # and I want this column to be my primary key
    # then accessing john.username -> will give me some data of type string
    # in other words we've mapped the username Python object property to an SQL column of type String 
    username: Mapped[str] = mapped_column(String, primary_key=True)
    password: Mapped[str] = mapped_column(String)
    salt: Mapped[str] = mapped_column(String) #add
    friend_list: Mapped[str] = mapped_column(String)
    request_list: Mapped[str] = mapped_column(String)
    waiting_list: Mapped[str] = mapped_column(String)######################## cerate some new columns for the database
    public_key: Mapped[str] = mapped_column(String)#############update here too
    type: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String)


# stateful counter used to generate the room id
class Counter():
    def __init__(self):
        self.counter = 0
    
    def get(self):
        self.counter += 1
        return self.counter

# Room class, used to keep track of which username is in which room
class Room():
    def __init__(self):
        self.counter = Counter()
        # dictionary that maps the username to the room id
        # for example self.dict["John"] -> gives you the room id of 
        # the room where John is in
        self.dict: Dict[str, int] = {}

    def create_room(self, sender: str, receiver: str) -> int:
        room_id = self.counter.get()
        self.dict[sender] = room_id
        self.dict[receiver] = room_id
        return room_id
    
    def join_room(self,  sender: str, room_id: int) -> int:
        self.dict[sender] = room_id

    def leave_room(self, user):
        if user not in self.dict.keys():
            return
        del self.dict[user]

    # gets the room id from a user
    def get_room_id(self, user: str):
        if user not in self.dict.keys():
            return None
        return self.dict[user]
    

    
class Message(Base): #add
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    sender_username = Column(String, ForeignKey('user.username'))
    receiver = Column(String)
    content = Column(String)

    sender = relationship("User", foreign_keys=[sender_username])


class SessionID(Base): #add
    __tablename__ = 'sessionID'

    session_id = Column(String,  primary_key=True)
    username = Column(String, ForeignKey('user.username'))
    join_time = Column(DateTime)


class Message_public(Base): #add
    __tablename__ = 'messages_public'
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer)
    content = Column(String)


##############---------add---------#############
class Article(Base): #add
    __tablename__ = 'article'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String)
    content = Column(String)
    type = Column(String)



class Comment(Base):
    __tablename__ = 'comment'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String)
    
    content = Column(String)
    article_id = Column(Integer)
    type = Column(String)

class Mute(Base):
    __tablename__ = 'mute'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String)