'''
db
database file, containing all the logic to interface with the sql database
'''
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session
from models import *

from pathlib import Path

import random
import string
from cryptography.fernet import Fernet
import hashlib
from base64 import urlsafe_b64encode

# creates the database directory
Path("database") \
    .mkdir(exist_ok=True)

# "database/main.db" specifies the database file
# change it if you wish
# turn echo = True to display the sql output
engine = create_engine("sqlite:///database/main.db", echo=False)

# initializes the database
Base.metadata.create_all(engine)
#############-------------add-------------############
def insert_article(username: str, content: str, type: str):    #add
    with Session(engine) as session:
        art = Article(username = username, content = content, type = type)
        session.add(art)
        session.commit()

def get_user_type(username: str):
    with Session(engine) as session:
        user = session.query(User).filter_by(username=username).first()
        if user:
            return user.type
        else:
            return None
        

def insert_comment(id: int,username: str, comment:str):
    with Session(engine) as session:
        type = get_user_type(username)
        comment = Comment(username = username, content = comment, article_id = id, type = type)
        session.add(comment)
        session.commit()


def insert_muteuser(muteuser: str):
    with Session(engine) as session:
        muteobject = Mute(username = muteuser)
        session.add(muteobject)
        session.commit()

def check_mute(username: str):
    with Session(engine) as session:
        user = session.query(Mute).filter_by(username=username).first()
        if user:
            return True
        else:
            return False

# inserts a user to the database
def insert_user(username: str, hashed_password: str, salt: str, friend_list=''): #add change
    with Session(engine) as session:
        user = User(username=username, password=hashed_password, salt=salt,friend_list=friend_list,request_list = '',waiting_list ='', public_key='',state='',type='admin') #add change
        session.add(user)
        session.commit()

# gets a user from the database
def get_user(username: str):
    with Session(engine) as session:
        return session.get(User, username)

def set_user_state(username: str, status):
    with Session(engine) as session:
        # 使用 session.get() 获取 User 实例
        user = session.get(User, username)
        if user:
            # 修改用户状态
            user.state = status
            # 提交更改
            session.commit()
            print(f"User {username} has been set to offline.")
        else:
            print(f"User {username} not found.")

def get_user_password(username: str): #add
    with Session(engine) as session:
        user = session.query(User).filter_by(username=username).first()
        if user:
            return user.password
        else:
            return None
        

def insert_message(sender_username: str,  content: str, receiver): #add
    with Session(engine) as session:
        if content is None:
            return "Error: Message content cannot be None!"
        delete_messages(sender_username, receiver)
        sender_password = get_user_password(sender_username)
        if not sender_password:
            return "Error: Sender does not exist!"
        
        fernet_key = urlsafe_b64encode(bytes.fromhex(get_user_password(sender_username))).ljust(32, b'=')
        
        cipher = Fernet(fernet_key)

        encrypted_content = cipher.encrypt(content.encode()).decode()
        
        message = Message(sender_username=sender_username, content=encrypted_content, receiver = receiver)
        session.add(message)
        session.commit()

def delete_messages(sender_username: str, receiver: int): #add
    with Session(engine) as session:
        try:
            stmt = delete(Message).where(
                (Message.receiver == receiver) &
                (Message.sender_username == sender_username)
            )

            session.execute(stmt)
            session.commit()
        except:
            return

def get_messages( username: str, receiver): #add
    with Session(engine) as session:

        messages = session.query(Message).filter(
            Message.receiver == receiver,
            Message.sender_username == username
        ).all()
        
        decrypted_messages = []
        for message in messages:
            sender_username = message.sender_username

            fernet_key = urlsafe_b64encode(bytes.fromhex(get_user_password(sender_username))).ljust(32, b'=')
        
            if not sender_username:
                return "Error: Sender does not exist!"

            cipher = Fernet(fernet_key)

            decrypted_content = cipher.decrypt(message.content.encode()).decode()

            decrypted_messages.append(decrypted_content)
        
        return decrypted_messages

def insert_sessionID(username: str, join_time) -> str: #add
    with Session(engine) as session:

        user = session.query(User).filter(User.username == username).first()
        if user is None:
            return None
        
        session_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        session_info = SessionID(session_id=session_id, username=username, join_time=join_time)
        session.add(session_info)
        session.commit()
        return session_id

def get_sessionID(username: str) -> str: #add
    with Session(engine) as session:

        session_info = session.query(SessionID).filter(SessionID.username == username).first()
        if session_info:
            return session_info.session_id
        else:
            return None
        
def get_join_time(username: str) -> str: #add
    with Session(engine) as session:

        session_info = session.query(SessionID).filter(SessionID.username == username).first()
        if session_info:
            return session_info.join_time
        else:
            return None
        
def disconnet_remove_sessionID(username): #add
    with Session(engine) as session:
        session_id = session.query(SessionID).filter(SessionID.username == username).first()
        if session_id:
            session.delete(session_id)
            session.commit()
        else:
            return None

def delete_all_sessions(): #add
    with Session(engine) as session:
        stmt = delete(SessionID)
        session.execute(stmt)
        session.commit()


def update_user_types():
    # Create a new session
    with Session(engine) as session:
        # Query all users
        users = session.query(User).all()

        for user in users:
            if "academics" in user.username:
                user.type = 'academics'
            elif "admin" in user.username:
                user.type = 'admin'
                
            elif "administrative" in user.username:
                user.type = 'administrative'
            else:
                user.type = 'student'
        # Commit the changes to the database
        session.commit()


def insert_public_message(room_id: int, content: str): #add
    with Session(engine) as session:
        if content is None:
            return "Error: Message content cannot be None!"
        print(f"add {content}")
        message = Message_public(room_id=room_id, content=content)
        session.add(message)
        session.commit()

def delete_all_public_messages(): #add
    with Session(engine) as session:
        stmt = delete(Message_public)
        session.execute(stmt)
        session.commit()
    
def get_public_messages(room_id: int): #add
    with Session(engine) as session:

        messages = session.query(Message_public).filter(
            Message_public.room_id == room_id,
        ).all()
        contents = []
        for message in messages:
            contents.append(message.content)
        print(contents)
        return contents
    






import sqlite3

conn = sqlite3.connect('database/main.db')

cursor = conn.cursor()

cursor.execute("SELECT * FROM user")

rows = cursor.fetchall()

for row in rows:
    print(row)

cursor.close()
conn.close()