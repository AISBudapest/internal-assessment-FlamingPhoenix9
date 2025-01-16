from flask import Flask, render_template, request, session, redirect
import requests
import json 
#https://cs50.readthedocs.io/libraries/cs50/python/
from cs50 import SQL
import sqlite3
import smtplib
#https://www.youtube.com/watch?v=z0AfnEPyvAs
from flask_apscheduler import APScheduler
from notifications import notify_users
from formsubmission import BrawlStarsMapTrackerRegistrationForm
#db=SQL("sqlite:///data.db")
app = Flask(__name__)
app.secret_key="__privatekey__"
scheduler = APScheduler()

data = {'active_maps': [], 'upcoming_maps': [],'all_maps':[]}

def update_data():
    res = requests.get('https://api.brawlify.com/v1/events')
    res2 = requests.get('https://api.brawlify.com/v1/maps')
    response = json.loads(res.text)
    response2 = json.loads(res2.text)
    active_maps = response.get("active", [])
    data['active_map_names'] = [map_info["map"]["name"] for map_info in active_maps if "map" in map_info]
    upcoming_maps = response.get("upcoming", [])
    data['upcoming_map_names'] = [map_info["map"]["name"] for map_info in upcoming_maps if "map" in map_info]
    all_maps = response2.get("list",[])
    data['all_map_names'] = [map_info["name"] for map_info in all_maps if "name" in map_info]
    data['all_map_emojis'] = {map_info["name"]: map_info["gameMode"]["imageUrl"] for map_info in all_maps if "name" in map_info and "gameMode" in map_info}


update_data()
#https://stackoverflow.com/questions/31270488/navigating-json-in-python

#source - https://stackoverflow.com/questions/68429566/how-to-return-render-template-in-flask
#videos for login/registration: https://youtu.be/fPAUGZYU4MA?feature=shared
#https://www.youtube.com/watch?v=YpKYBG38FbM&list=PLf9umJdQ546h26s7VKQVUir5GoOZ-1JTP&index=12
@app.route("/")

def defaultHome():
    brawlStarsMapTrackerRegistrationForm=BrawlStarsMapTrackerRegistrationForm()
    return render_template('login.html',form=brawlStarsMapTrackerRegistrationForm)

def create_table():
    con = sqlite3.connect('user1.db')
    c = con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS user1(name text, passWord text, email text, notifications boolean)")
    c.execute("CREATE TABLE IF NOT EXISTS currentMaps(map_name text)")
    c.execute("CREATE TABLE IF NOT EXISTS favoriteMaps(user_name text, map_name text)")
    c.execute("CREATE TABLE IF NOT EXISTS notifications (map_name text,user_name text,notified_date text)")
    con.commit()
    con.close()

create_table()

@app.route('/home', methods=['POST','GET'])
def home():
        if 'username' not in session:
             return redirect('/login')
        username = session['username']
        print(f"User logged in: {username}")
        con = sqlite3.connect('user1.db')
        c = con.cursor()
        c.execute("SELECT map_name FROM favoriteMaps WHERE user_name = ?", (username,))
        user_favorites = [row[0] for row in c.fetchall()]
        c.execute("SELECT email FROM user1 WHERE name = ?", (username,))
        user_email = c.fetchone()
        if user_email:
            user_email = user_email[0]
        message = request.args.get('message', None)
        notifications_enabled = session.get('notifications_enabled', True)
        c.execute("SELECT notifications FROM user1 WHERE name = ?", (username,))
        result = c.fetchone()
        notifications_enabled = result[0] if result else True
        if request.method == 'POST':
            map_name = request.form.get('addMaps')
            email = request.form.get('setEmail')
            print(f"Map entered by user: {map_name}")
            if map_name:
                if map_name in data['all_map_names']:
                    c.execute("SELECT * FROM favoriteMaps WHERE user_name = ? AND map_name = ?", (username, map_name))
                    if c.fetchone():
                        message = f"'{map_name}' is already in your favorites."
                    else:
                        c.execute("INSERT INTO favoriteMaps (user_name, map_name) VALUES (?, ?)", (username, map_name))
                        con.commit()
                        message = f"'{map_name}' has been added to your favorites."
                        c.execute("SELECT map_name FROM favoriteMaps WHERE user_name = ?", (username,))
                        user_favorites = [row[0] for row in c.fetchall()]
                else:
                    message = f"'{map_name}' is not an active or upcoming map."
            else:
                message = "Please enter a valid map name."

            if email:
                c.execute("UPDATE user1 SET email = ? WHERE name = ?", (email, username))
                con.commit()
                message = f"Email {email} has been set for notifications."
                    
        con.close()
        brawlStarsMapTrackerRegistrationForm = BrawlStarsMapTrackerRegistrationForm()
        return render_template(
            'index.html',
            form=brawlStarsMapTrackerRegistrationForm,
            favorites=user_favorites,
            active_maps=data['active_map_names'],
            upcoming_maps=data['upcoming_map_names'],
            all_maps=data['all_map_names'],
            map_images=data['all_map_emojis'],
            message=message,
            username=username,
            notifications_enabled=notifications_enabled,
            email=user_email
        )
@app.route('/remove_favorite', methods=['POST'])
def remove_favorite():
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    map_name = request.form.get('map_name')
    con = sqlite3.connect('user1.db')
    c = con.cursor()
    c.execute("DELETE FROM favoriteMaps WHERE user_name = ? AND map_name = ?", (username, map_name))
    con.commit()
    con.close()
    message = f"{map_name} has been removed from favorites."
    return redirect(f'/home?message={message}')
    
@app.route('/add_favorite', methods=['POST'])
def add_favorite():
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    map_name = request.form.get('map_name')
    message = None
    con = sqlite3.connect('user1.db')
    c = con.cursor()
    c.execute("SELECT * FROM favoriteMaps WHERE user_name = ? AND map_name = ?", (username, map_name))
    if c.fetchone():
        message  = f"{map_name} is already in favorites."
    else: 
        c.execute("INSERT INTO favoriteMaps (user_name, map_name) VALUES (?, ?)", (username, map_name))
        con.commit()
        message = f"{map_name} has been added to favorites."
    con.close()
    return redirect(f'/home?message={message}')

  
@app.route('/login', methods=['POST','GET'])
def login():
     if request.method=='POST':
        userName = request.form['name']
        passWord=request.form['passWord']
        con=sqlite3.connect('user1.db')
        c=con.cursor()
        statement=f"SELECT * from user1 WHERE name='{userName}' AND passWord='{passWord}';"
        c.execute(statement)
        user = c.fetchone()
        if user:
            session['username'] = userName
            return redirect('/home')
        else:
            return render_template('login.html', error="Invalid username or password")
     else:
        request.method == 'GET'
        return render_template('login.html')
@app.route('/registrationform', methods=['POST', 'GET'])

def registrationform():
    brawlStarsMapTrackerRegistrationForm=BrawlStarsMapTrackerRegistrationForm()
    con=sqlite3.connect('user1.db')
    c=con.cursor()
    if request.method=='POST':
        if(request.form["name"]!="" and request.form["passWord"]!=""):
            name=request.form["name"]
            passWord=request.form["passWord"]
            statement=f"SELECT * from user1 WHERE name='{name}' AND passWord='{passWord}';"
            c.execute(statement)
            data=c.fetchone()
            if data:
                return render_template("error.html")
            else:
                if not data:
                    c.execute("INSERT INTO user1 (name,passWord, notifications) VALUES (?,?,?)",(name,passWord, True))
                    con.commit()
                    con.close()
                return render_template('successformsubmission.html')
    elif request.method=='GET':
        return render_template('register.html', form=brawlStarsMapTrackerRegistrationForm)
      
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/successformsubmission')
def successformsubmission():
    name=session.get('name', None)
    return render_template('successformsubmission.html')

@app.route('/toggle_notifications', methods=['POST'])
def toggle_notifications():
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    con = sqlite3.connect('user1.db')
    c = con.cursor()
    c.execute("SELECT notifications FROM user1 WHERE name = ?", (username,))
    current_notifications = c.fetchone()
    if current_notifications is not None:
        new_notifications = not current_notifications[0] 
        c.execute("UPDATE user1 SET notifications = ? WHERE name = ?", (new_notifications, username))
        con.commit()
        con.close()
        return redirect('/home')
    else:
        con.close()

def notify():
    update_data()
    notify_users(data['active_map_names'])

scheduler.add_job(func=notify, trigger='interval', seconds = 120, id='notifs')
scheduler.start()
# app.run(debug=True)


#email app password: hxqg qban uwxu spns
