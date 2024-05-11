'''
socket_routes
file containing all the routes related to socket.io
'''


from flask_socketio import join_room, emit, leave_room
from flask import request

from datetime import datetime
import sqlite3

try:
    from __main__ import socketio
except ImportError:
    from app import socketio

from models import Room

import db

room = Room()

# when the client connects to a socket
# this event is emitted when the io() function is called in JS
@socketio.on('connect')
def connect():
    username = request.cookies.get("username")
    room_id = request.cookies.get("room_id")
    if room_id is None or username is None:
        db.set_user_state(username,'online')
        return
    # socket automatically leaves a room on client disconnect
    # so on client connect, the room needs to be rejoined
    db.set_user_state(username,'online')
    join_room(int(room_id))
    emit("incoming", (f"{username} has connected", "green"), to=int(room_id))

# event when client disconnects
# quite unreliable use sparingly
@socketio.on('disconnect')
def disconnect():
    username = request.cookies.get("username")
    room_id = request.cookies.get("room_id")
    if room_id is None or username is None:
        remove = db.disconnet_remove_sessionID(username)
        db.set_user_state(username,'offline')
        return
    remove = db.disconnet_remove_sessionID(username) #add
    if remove is None: #add
        return
    db.set_user_state(username,'offline')
    emit("incoming", (f"{username} has disconnected", "red"), to=int(room_id))

# send message event handler
@socketio.on("send")
def send(username, message, room_id):
    cookie_username = request.cookies.get("username") #add
    cookie_sessionID = request.cookies.get("session_id") #add
    sessionID = db.get_sessionID(username) #add

    if username is None or cookie_username is None or cookie_sessionID is None: #add


        emit("error_message", "Unauthorized access 1")
        return
    
    if username != cookie_username or cookie_sessionID != sessionID: #add
        emit("error_message", "Unauthorized access 2")
        return
    """
    emit("incoming", (f"ID:{room_id} {username}: {message}"), to=room_id, include_self=False) #add change later
    """
    if(int(room_id) < 1000):
        emit("incoming", (f"{username}:{message}"), to=room_id, include_self=False) #add change later
    else:
        print(message)
        print(room_id)
        print(room.dict)
        #emit("incoming_public", (f"{username}:{message}"))
        join_room(room_id)
        db.insert_public_message(room_id,f"{username}:{message}")
        emit("incoming_public", (f"{username}:{message}"), to=room_id)
    

    
# join room event handler
# sent when the user joins a room
@socketio.on("join")
def join(sender_name, receiver_name):

    cookie_username = request.cookies.get("username") #add
    cookie_sessionID = request.cookies.get("session_id") #add
    sessionID = db.get_sessionID(sender_name) #add

    if sender_name is None or cookie_username is None or cookie_sessionID is None: #add
        emit("error_message", "Unauthorized access")
        return
    
    if sender_name != cookie_username or cookie_sessionID != sessionID: #add
        emit("error_message", "Unauthorized access")
        return
    
    conn = sqlite3.connect('./database/main.db')
    c = conn.cursor()
    c.execute("SELECT friend_list FROM user WHERE username=?", (sender_name,))
    friend_list = c.fetchone()[0]
    friend_list = friend_list.split(',')
    receiver = db.get_user(receiver_name)

    if receiver is None:
        return "Unknown receiver!"
    
    if receiver_name not in friend_list:
        return "Not a friend!"

    sender = db.get_user(sender_name)
    if sender is None:
        return "Unknown sender!"


    
    room_id = room.get_room_id(receiver_name)

    # if the user is already inside of a room 
    if room_id is not None:
        room.join_room(sender_name, room_id)
        join_room(room_id)
        # emit to everyone in the room except the sender
        emit("incoming", (f"{sender_name} has joined the room.", "green"), to=room_id, include_self=False)
        # emit only to the sender
        emit("incoming", (f"{sender_name} has joined the room. Now talking to {receiver_name}.", "green"))
        messages = db.get_messages(sender_name, receiver_name) #add
        for message in messages: #add
                emit("history", (f"{message}", "black"), to=request.sid)
        return room_id

    # if the user isn't inside of any room, 
    # perhaps this user has recently left a room
    # or is simply a new user looking to chat with someone
    room_id = room.create_room(sender_name, receiver_name)
    join_room(room_id)
    emit("incoming", (f"{sender_name} has joined the room. Now talking to {receiver_name}.", "green"), to=room_id)

    messages = db.get_messages(sender_name, receiver_name) #add
    for message in messages: #add
        emit("history", (f"{message}", "black"), to=request.sid)
    
    return room_id



@socketio.on("join_public")
def join_public(sender_name, room_id):

    cookie_username = request.cookies.get("username") # 获取 cookie 中的用户名
    cookie_sessionID = request.cookies.get("session_id") # 获取 cookie 中的会话 ID
    sessionID = db.get_sessionID(sender_name) # 从数据库获取会话 ID

    if sender_name is None or cookie_username is None or cookie_sessionID is None:
        emit("error_message", "Unauthorized access")
        return
    
    if sender_name != cookie_username or cookie_sessionID != sessionID:
        emit("error_message", "Unauthorized access")
        return
    
    # 直接使用提供的 room_id 加入房间
    leave_room(1001)
    leave_room(1002)
    leave_room(1003)
    room.leave_room(sender_name)
    room.join_room(sender_name, room_id)
    join_room(room_id)
    emit("incoming", (f"{sender_name} has joined the room {room_id}.", "green"), to=room_id)
    messages = db.get_public_messages(room_id) # 根据房间 ID 获取消息历史
    for message in messages:
        emit("incoming_public", (f"{message}", "black"), to=request.sid)
    
    return room_id





# leave room event handler
@socketio.on("leave")
def leave(username, room_id):
    cookie_username = request.cookies.get("username") #add
    cookie_sessionID = request.cookies.get("session_id") #add
    sessionID = db.get_sessionID(username) #add
    print(f"leave id is{room_id}")
    if username is None or cookie_username is None or cookie_sessionID is None: #add
        emit("error_message", "Unauthorized access")
        return
    
    if username != cookie_username or cookie_sessionID != sessionID: #add
        emit("error_message", "Unauthorized access")
        return
    join_room(room_id)
    emit("incoming", (f"{username} has left the room.", "red"), to=room_id)
    print(room_id)
    leave_room(room_id)
    leave_room(1001)
    leave_room(1002)
    leave_room(1003)
    room.leave_room(username)

@socketio.on("getHistory") #add
def get_history(username, message, receiver): #add
    cookie_username = request.cookies.get("username")
    cookie_sessionID = request.cookies.get("session_id")
    sessionID = db.get_sessionID(username)

    if username is None or cookie_username is None or cookie_sessionID is None:
        emit("error_message", "Unauthorized access")
        return
    
    if username != cookie_username or cookie_sessionID != sessionID:
        emit("error_message", "Unauthorized access")
        return
    
    db.insert_message(username, message, receiver)

@socketio.on('getFriendstatus')
def handle_get_friend_status(username):
    user = db.get_user(username)
    list = user.friend_list
    friends_info = []
    friend_list = [name for name in list.split(',') if name]
    for name in friend_list:
        User = db.get_user(name)
        friends_info.append(User.state)
        friends_info.append(User.type)

    emit('friendStatusResponse', friends_info)

@socketio.on('setPrivate')
def set_private(username):
    user = db.get_user(username)
    if user.state == 'online' or user.state == 'busy':
        db.set_user_state(username, 'offline')
        note = username + ' is now private'
        emit("error_message", note)
    else:
        db.set_user_state(username, 'online')
        note = username + ' is now online'
        emit("error_message", note)

@socketio.on('setBusy')
def set_busy(username):
    user = db.get_user(username)
    if user.state != 'busy':
        db.set_user_state(username, 'busy')
        note = username + ' is now busy'
        emit("error_message", note)
    else:
        db.set_user_state(username, 'online')
        note = username + ' is now online'
        emit("error_message", note)
