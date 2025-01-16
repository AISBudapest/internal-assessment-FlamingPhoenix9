import sqlite3
import smtplib
from datetime import datetime

def send_email(user_email, map_name):
#source - https://www.youtube.com/watch?v=ueqZ7RL8zxM
    sender_email = "brawlstarsmaptracker@gmail.com"

    subject = f"One of your favorite maps is currently active: {map_name}"
    body_message = f" The map '{map_name}' has become active in Brawl Stars."

    text = f"Subject: {subject}\n\n{body_message}"
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()

    server.login(sender_email, "hxqgqbanuwxuspns")
    server.sendmail(sender_email, user_email, text)

def notify_users(active_map_names):
    con = sqlite3.connect('user1.db')
    c = con.cursor()

    c.execute("SELECT DISTINCT user_name, map_name FROM favoriteMaps")
    favorite_maps = c.fetchall()
    
    for user_name, map_name in favorite_maps:
        print("working...")
        c.execute("SELECT notifications FROM user1 WHERE name = ?", (user_name,))
        notifications_enabled = c.fetchone()
        
        if not notifications_enabled or notifications_enabled[0] != 1:
            print(f"Notifications disabled for {user_name}.")
            continue
        
        if map_name in active_map_names:
            today = datetime.now().strftime('%Y-%m-%d')
            
            c.execute("SELECT * FROM notifications WHERE map_name = ? AND user_name = ? AND notified_date = ?", 
                      (map_name, user_name, today))
            if c.fetchone():
                print(f"Notification for {map_name} already sent to {user_name} today.")
                continue 

            c.execute("SELECT email FROM user1 WHERE name = ?", (user_name,))
            user_email = c.fetchone()
            if user_email:
                send_email(user_email[0], map_name)
                print(f"Notification sent to {user_name} for {map_name}.")
                
                c.execute("INSERT INTO notifications (map_name, user_name, notified_date) VALUES (?, ?, ?)",
                          (map_name, user_name, today))
                con.commit()

    con.close()
   