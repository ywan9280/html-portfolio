'''
app.py contains all of the server application
this is where you'll find all of the get/post request handlers
the socket event handlers are inside of socket_routes.py
'''

from flask import Flask, render_template, request, abort, url_for,make_response,jsonify
from flask_socketio import SocketIO, emit
import db
import secrets

import hashlib
import ssl
import os
import signal
import sys
import re
import sqlite3
import datetime


# import logging

# this turns off Flask Logging, uncomment this to turn off Logging
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

current_folder = os.path.dirname(os.path.abspath(__file__))
database_folder = os.path.join(current_folder, "database")
database_file = os.path.join(database_folder, "main.db")
global_str_variable = database_file

app = Flask(__name__)

# secret key used to sign the session cookie
app.config['SECRET_KEY'] = secrets.token_hex()
socketio = SocketIO(app)
db.update_user_types()
# don't remove this!!
import socket_routes

def shutdown_server(signal, frame): #add
    db.delete_all_sessions()
    db.delete_all_public_messages()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_server) #add

def generate_salt(): #add
    return secrets.token_hex(16)

def hash_password(password, salt): #add
    salted_password = password + salt
    hashed_password = hashlib.sha256(salted_password.encode()).hexdigest()
    return hashed_password


# index page
@app.route("/")
def index():
    return render_template("index.jinja")

# login page
@app.route("/login")
def login():    
    return render_template("login.jinja")

# handles a post request when the user clicks the log in button
@app.route("/login/user", methods=["POST"])
def login_user():
    
    if not request.is_json:
        abort(404)
    

    username = (request.json.get("username")) #add prevent xss
    password = (request.json.get("password")) #add prevent xss

    
    user =  db.get_user(username)

    if not username or not password: #add
        return "Error: Username or password is empty!"

    if user is None:
        return "Error: User does not exist!"

    salt = user.salt #add
    hashed_password = hash_password(password, salt) #add

    if user.password != hashed_password: #add change
        return "Error: Password does not match!"
    db.disconnet_remove_sessionID(username) #add
    session_id = db.insert_sessionID(username, datetime.datetime.now()) #add
    if session_id is None: #add
        return "Error: Failed to generate session ID!"
    type = user.type
    response = make_response(url_for('home', username=username)) #add
    response.set_cookie('session_id', session_id) #add
    response.set_cookie('username', username)

    return response #add change

# handles a get request to the signup page
@app.route("/signup")
def signup():
    return render_template("signup.jinja")

# handles a post request when the user clicks the signup button
@app.route("/signup/user", methods=["POST"])
def signup_user():
    if not request.is_json:
        abort(404)
    username = (request.json.get("username"))  #add change
    password = (request.json.get("password"))  #add change


    if not username or not password: #add
        return "Error: Username or password is empty!"

    if db.get_user(username) is None: #add change
        salt = generate_salt()
        hashed_password = hash_password(password, salt)
        db.insert_user(username, hashed_password, salt)
        db.update_user_types()#add
        session_id = db.insert_sessionID(username, datetime.datetime.now())
        if session_id is None:
            return "Error: Failed to generate session ID!"
        
        response = make_response(url_for('home', username=username))
        response.set_cookie('session_id', session_id)
        response.set_cookie('username', username)
        #response.set_cookie('type', username)

        return response

    return "Error: User already exists!"

# handler when a "404" error happens
@app.errorhandler(404)
def page_not_found(_):
    return render_template('404.jinja'), 404

# home page, where the messaging app is
@app.route("/home")
def home():
    if request.args.get("username") is None:
        abort(404)
    if db.get_user(request.args.get("username")) is None:      ####################add when user not exist
        abort(404)
    user = db.get_user(request.args.get("username"))
    type = user.type
    mute = db.check_mute(user.username)#add
    return render_template("home.jinja", username=request.args.get("username"), type = type,mute=mute)

#########################
######  Below are the new functions for friend part  ###################

#get friend list
@app.route('/get_friend_list', methods=['POST'])
def get_friend_list():
    username = request.form['username']
    friend_list = fetch_friend_list(username)
    
    cookie_username = request.cookies.get("username") #add
    cookie_sessionID = request.cookies.get("session_id") #add
    sessionID = db.get_sessionID(username) #add

    if username is None or cookie_username is None or cookie_sessionID is None: #add
        return "Unauthorized access"
    
    if username != cookie_username or cookie_sessionID != sessionID: #add
        return "Unauthorized access"
    
    return friend_list

def fetch_friend_list(username):
    
    cookie_username = request.cookies.get("username") #add
    cookie_sessionID = request.cookies.get("session_id") #add
    sessionID = db.get_sessionID(username) #add

    if username is None or cookie_username is None or cookie_sessionID is None: #add
        return "Unauthorized access get_friend_list"
    
    if username != cookie_username or cookie_sessionID != sessionID: #add
        return "Unauthorized access get_friend_list"
    

    conn = sqlite3.connect(global_str_variable)
    cursor = conn.cursor()
    cursor.execute("SELECT friend_list FROM user WHERE username=?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None



#add a new friend
@app.route('/add_friend', methods=['POST'])
def add_Friend():
    username = request.form['username']
    friend_username = request.form['friend']
    
    cookie_username = request.cookies.get("username") #add
    cookie_sessionID = request.cookies.get("session_id") #add
    sessionID = db.get_sessionID(username) #add

    if username is None or cookie_username is None or cookie_sessionID is None: #add
        return "Unauthorized access add_Friend"
    
    if username != cookie_username or cookie_sessionID != sessionID: #add
        return "Unauthorized access add_Friend"
    
    #part 1: update my request_list
    has_user = False
    is_friend = False
    conn = sqlite3.connect(global_str_variable)
    cursor = conn.cursor()

    cursor.execute("SELECT username FROM user")
    usernames = cursor.fetchall()

    for usernamess in usernames:
        if friend_username == usernamess[0]:
            has_user = True

    conn.close()

    conn = sqlite3.connect(global_str_variable)
    cursor = conn.cursor()
    cursor.execute("SELECT friend_list FROM user WHERE username=?", (username,))#########  add, if you are already friends, cannot send requests
    result = cursor.fetchone()
    friend_list = result[0]
    friend_list = friend_list.split(',')
    
    if friend_username in friend_list:
        is_friend = True

    if has_user==True and is_friend == False:

        conn = sqlite3.connect(global_str_variable)
        cursor = conn.cursor()
        cursor.execute("SELECT request_list FROM user WHERE username=?", (str(username),))
        
        result= cursor.fetchone()
        
        if result:
            request_list = result[0]
            if request_list is not None:
                request_list_split = request_list.split(',')
            new_request = friend_username
        
        if request_list:
            if new_request not in request_list_split:
                if friend_username!=username:
                    request_list += ',' + new_request
                    #part2: update receivers' waiting list
                    conn2 = sqlite3.connect(global_str_variable)
                    cursor2 = conn2.cursor()
                    cursor2.execute("SELECT waiting_list FROM user WHERE username=?", (str(friend_username),))
                    result2= cursor.fetchone()
                    
                    if result2 is not None:
                        if result2[0] is not None:
                            waiting = result2[0]
                            waiting+=','+username
                        else:
                            waiting = username
                    else:
                        waiting = username
                    cursor2.execute("UPDATE user SET waiting_list=? WHERE username=?", (waiting, friend_username))
                    conn2.commit()
                else:
                    return "cannot add yourself"
            else:
                return "request already exists!"
        else:
            if friend_username!=username:
                request_list = new_request
                #part2: update receivers' waiting list
                conn2 = sqlite3.connect(global_str_variable)
                cursor2 = conn2.cursor()
                cursor2.execute("SELECT waiting_list FROM user WHERE username=?", (str(friend_username),))
                result2= cursor2.fetchone()
                if result2[0] is not None:

                    waiting=result2[0]
                    waiting+=','+username
                else:
                    waiting=username
                cursor2.execute("UPDATE user SET waiting_list=? WHERE username=?", (waiting, friend_username))
                conn2.commit()
            else:
                return "cannot add yourself"
        
        
        cursor.execute("UPDATE user SET request_list=? WHERE username=?", (request_list, username))
        conn.commit()

        return request_list
    else:
        return "failed"


#get waiting list(the list of people waiting for your agree/reject)
@app.route('/get_wait_list',methods=['POST'])
def get_wait_list():
    username = request.form['username']
    
    cookie_username = request.cookies.get("username") #add
    cookie_sessionID = request.cookies.get("session_id") #add
    sessionID = db.get_sessionID(username) #add

    if username is None or cookie_username is None or cookie_sessionID is None: #add
        return "Unauthorized access get_wait_list"
    
    if username != cookie_username or cookie_sessionID != sessionID: #add
        return "Unauthorized access get_wait_list"

    conn = sqlite3.connect(global_str_variable)
    cursor = conn.cursor()
    cursor.execute("SELECT waiting_list FROM user WHERE username=?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] else "empty"


#get request list
@app.route('/get_request_list',methods=['POST'])
def get_request_list():
    username = request.form['username']
    
    cookie_username = request.cookies.get("username") #add
    cookie_sessionID = request.cookies.get("session_id") #add
    sessionID = db.get_sessionID(username) #add

    if username is None or cookie_username is None or cookie_sessionID is None: #add
        return "Unauthorized access get_request_list"
    
    if username != cookie_username or cookie_sessionID != sessionID: #add
        return "Unauthorized access get_request_list"
    
    conn = sqlite3.connect(global_str_variable)
    cursor = conn.cursor()
    cursor.execute("SELECT request_list FROM user WHERE username=?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] else "empty"


#after an agree/reject operation, update the request/waiting list accordingly
@app.route('/remove_item',methods=['POST'])
def remove_item():
    item = request.form['item']
    username = request.form['username']
    conn = sqlite3.connect(global_str_variable)
    cursor = conn.cursor()
    
    cookie_username = request.cookies.get("username") #add
    cookie_sessionID = request.cookies.get("session_id") #add
    sessionID = db.get_sessionID(username) #add

    if username is None or cookie_username is None or cookie_sessionID is None: #add
        return "Unauthorized access remove_item"
    
    if username != cookie_username or cookie_sessionID != sessionID: #add
        return "Unauthorized access remove_item"
    
    cursor.execute("SELECT waiting_list FROM user WHERE username=?", (username,))
    result = cursor.fetchone()
    new = result[0].split(',')
    
    if item in new:
        new.remove(item)
    new_in = ','.join(new)
    cursor.execute("UPDATE user SET waiting_list=? WHERE username=?", (new_in, username))
    ##############

    cursor.execute("SELECT request_list FROM user WHERE username=?", (username,))
    result = cursor.fetchone()
    new = result[0].split(',')
    
    if item in new:
        new.remove(item)
    new_in = ','.join(new)
    cursor.execute("UPDATE user SET request_list=? WHERE username=?", (new_in, username))
    ###################

    cursor.execute("SELECT request_list FROM user WHERE username=?", (item,))
    result = cursor.fetchone()
    new = result[0].split(',')
    
    if username in new:
        new.remove(username)
    new_in = ','.join(new)
    cursor.execute("UPDATE user SET request_list=? WHERE username=?", (new_in, item))
    ####################

    cursor.execute("SELECT waiting_list FROM user WHERE username=?", (item,))
    result = cursor.fetchone()
    new = result[0].split(',')
    
    if username in new:
        new.remove(username)
    new_in = ','.join(new)
    cursor.execute("UPDATE user SET waiting_list=? WHERE username=?", (new_in, item))
    
    conn.commit()
    conn.close()

    return "hi"



#add something to friend_list after agree/reject operation
@app.route('/add_to_list',methods=['POST'])
def add_to_list():
    item = request.form['item']
    username = request.form['username']
    conn = sqlite3.connect(global_str_variable)
    cursor = conn.cursor()
    
    cookie_username = request.cookies.get("username") #add
    cookie_sessionID = request.cookies.get("session_id") #add
    sessionID = db.get_sessionID(username) #add

    if username is None or cookie_username is None or cookie_sessionID is None: #add
        return "Unauthorized access add_to_list"
    
    if username != cookie_username or cookie_sessionID != sessionID: #add
        return "Unauthorized access add_to_list"
    
    cursor.execute("SELECT friend_list FROM user WHERE username=?", (username,))
    result = cursor.fetchone()
    if result is not None:
        if result[0] is not None:
            new = result[0].split(',')
            new.append(item)
            update = ','.join(new)
            cursor.execute("UPDATE user SET friend_list=? WHERE username=?", (update, username))
            conn.commit()
            
        else:
            cursor.execute("UPDATE user SET friend_list=? WHERE username=?", (item, username))
            conn.commit()
            
    else:
        cursor.execute("UPDATE user SET friend_list=? WHERE username=?", (item, username))
        conn.commit()
        
    

    cursor.execute("SELECT friend_list FROM user WHERE username=?", (item,))
    result = cursor.fetchone()
    if result is not None:
        if result[0] is not None:
            new = result[0].split(',')
            new.append(username)
            update = ','.join(new)
            cursor.execute("UPDATE user SET friend_list=? WHERE username=?", (update, item))
            conn.commit()
            return "add successfully"
        else:
            cursor.execute("UPDATE user SET friend_list=? WHERE username=?", (username, item))
            conn.commit()
            return "add successfully"
    else:
        cursor.execute("UPDATE user SET friend_list=? WHERE username=?", (username, item))
        conn.commit()
        return "add successfully"


#######################  BELOW are functions for message encryption and MAC CODE
@app.route('/send_public_key', methods=['POST'])
#when some user generate a public key, update the database
def receive_public_key():
    public_key = request.form.get('public_key')
    username = request.form.get('username')
    conn = sqlite3.connect(global_str_variable)
    cursor = conn.cursor()
    
    cookie_username = request.cookies.get("username") #add
    cookie_sessionID = request.cookies.get("session_id") #add
    sessionID = db.get_sessionID(username) #add

    if username is None or cookie_username is None or cookie_sessionID is None: #add
        return "Unauthorized access"
    
    if username != cookie_username or cookie_sessionID != sessionID: #add
        return "Unauthorized access"
    
    cursor.execute("SELECT * FROM user WHERE username = ?", (username,))
    user = cursor.fetchone()

    if user:

        cursor.execute("UPDATE user SET public_key = ? WHERE username = ?", (public_key, username))
        
        conn.commit()
        conn.close()
        return "Public key updated successfully for user: " + username
    else:
        conn.close()
        return "User not found: " + username
    #when send message to someone, get his public key from database for encrypt message
@app.route('/get_public_key', methods=['POST'])
def get_public_key():
    receiver = request.form.get('username')
    
    conn = sqlite3.connect(global_str_variable)
    cursor = conn.cursor()
    
    cursor.execute("SELECT public_key FROM user WHERE username = ?", (receiver, ))
    
    public_key = cursor.fetchone()
    conn.commit()
    
    return public_key[0]



@app.route('/get_knowledge', methods=['POST'])#add
def get_knowledge():
    conn = sqlite3.connect('database/main.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM article')
    articles = cursor.fetchall()
    articles_dict = []
    for row in articles:
        id = row[0]
        username = row[1]
        content = row[2]
        type = row[3]
        content = content.replace('\n', '<br>')
        
        articles_dict.append(f"<div>id: {id}<br>username: {username}<br>type: {type}<br>content: <br>{content}</div>")


    conn.close()

    return articles_dict




import re
@app.route('/delete_article', methods=['POST'])#add
def delete_article():
    item = request.form['item']
    pattern = r"id: (\d+)"
    match = re.search(pattern,item)
    if match:
        id = match.group(1)
        print("Extracted id:", id)
        conn = sqlite3.connect('database/main.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM article WHERE id = ?", (id,))
        conn.commit()
        conn.close()

    else:
        print("No id found in the string.")
    return "s"



@app.route('/post_article', methods=['POST'])#add
def post_article():
    username = request.form['username']
    type = db.get_user_type(username)
    content = request.form['content']
    db.insert_article(username,content,type)
    return "success"


@app.route('/modify_article', methods=['POST'])#add
def modify_article():
    item = request.form['item']
    article = request.form['content']
    match = re.search(r'id: (\d+)', item)
    print(article)
    if match:
        id_number = match.group(1)
        conn = sqlite3.connect('./database/main.db')
        cursor = conn.cursor()

        cursor.execute("UPDATE article SET content = ? WHERE id = ?", (article, id_number))

        conn.commit()
        conn.close()
        return "suceess"
    else:
        return "failed"
    


@app.route('/save_comment',methods=['POST'])#add
def save_comment():
    comment = request.form['comment']
    username = request.form['username']
    item = request.form['item']
    match = re.search(r'id:\s*(\d+)', item)
    if match:
        id_number = match.group(1)
        id_number = int(id_number)
        db.insert_comment(id_number,username,comment)
        
    
    return "s"


@app.route('/view_comment',methods=['POST'])#add
def view_comment():
    item = request.form['item']
    match = re.search(r'id:\s*(\d+)', item)
    if match:
        id_number = match.group(1)
        id_number = int(id_number)
        conn = sqlite3.connect('./database/main.db')
        c = conn.cursor()

        
        c.execute("SELECT content,username,type FROM comment WHERE article_id = ?", (id_number,))
        comments = c.fetchall()

        
        conn.close()

        conn = sqlite3.connect('./database/main.db')
        c = conn.cursor()

       
        for comment in comments:
            print(comment)
        return [(comment[0],comment[1],comment[2]) for comment in comments]
    

@app.route('/delete_comment',methods=['POST'])
def delete_comment():
    
    item = request.form['item']
    comment = request.form['content']
    
    conn = sqlite3.connect('./database/main.db')
    c = conn.cursor()
    
    
    c.execute("DELETE FROM comment WHERE content = ?", (comment,))
    
    
    conn.commit()
    conn.close()
    
    return "s"


@app.route('/mute_user',methods=['POST'])
def mute_user():
    user = request.form['muteuser']
    import sqlite3
    conn = sqlite3.connect('./database/main.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mute WHERE username = ?", (user,))
    result = cursor.fetchone()
    if result:
        return "already muted"  
    else:
        cursor.execute("SELECT * FROM user WHERE username = ?", (user,))
        result2 = cursor.fetchone()
        if result2:
            db.insert_muteuser(user)
            return "mute successfully"
        else:
            return "user doesn't exist"
        
@app.route('/unmute_user',methods=['POST'])
def unmute_user():
    user = request.form['muteuser']
    import sqlite3
    conn = sqlite3.connect('./database/main.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user WHERE username = ?", (user,))
    result = cursor.fetchall()
    if result:

        cursor.execute("DELETE FROM mute WHERE username = ?", (user,))
        conn.commit()
        conn.close()
        return "delete successfully"
    else:
        return "user does not exists"

@app.route('/remove_friend',methods=['POST'])
def remove_friend():
    friendname = request.form['item']
    username = request.form['username']
    conn = sqlite3.connect('./database/main.db')
    cursor = conn.cursor()
    cursor.execute("SELECT friend_list FROM user WHERE username = ?", (username,))
    result = cursor.fetchone()
    if friendname in result[0].split(','):
        new_friend_list = ','.join([name for name in result[0].split(',') if name != friendname])
    print(new_friend_list)
    cursor.execute("UPDATE user SET friend_list=? WHERE username=?", (new_friend_list, username))
    conn.commit()
    conn.close()

    conn = sqlite3.connect('./database/main.db')
    cursor = conn.cursor()
    cursor.execute("SELECT friend_list FROM user WHERE username = ?", (friendname,))
    result = cursor.fetchone()
    if username in result[0].split(','):
        new_friend_list = ','.join([name for name in result[0].split(',') if name != username])
    print(new_friend_list)
    cursor.execute("UPDATE user SET friend_list=? WHERE username=?", (new_friend_list, friendname))
    conn.commit()
    conn.close()
    return friendname
if __name__ == '__main__': #add change HTTPS

    current_dir = os.path.dirname(os.path.abspath(__file__))

    certfile = os.path.join(current_dir, 'HTTPS', '2222Project.crt')
    keyfile = os.path.join(current_dir, 'HTTPS', '2222Project.key')

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile, keyfile)
    '''
    socketio.run(app, ssl_context=context)
    '''
    db.update_user_types()
    socketio.run(app)