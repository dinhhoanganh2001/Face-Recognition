from flask import Flask, render_template, Response
import cv2
import face_recognition
import numpy as np
import os


from flask import Flask, render_template, request, session, url_for, redirect, flash
import sqlite3
from flask_login._compat import unicode
import datetime

from forms import RegisterForm, LoginForm
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, login_required, UserMixin, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = ['832790179812']
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access this page!'
login_manager.login_message_category = "warning"
conn = sqlite3.connect('database.db')
cur = conn.cursor()


class User(UserMixin):
    def __init__(self, user_id, username, email, password):
        self.user_id = unicode(user_id)
        self.email = email
        self.username = username
        self.password = generate_password_hash(password)
        self.authenticated = False

    def verify_password(self, password):
        return check_password_hash(self.password, password)

    def is_active(self):
        return self.is_active()

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return self.authenticated

    def get_id(self):
        return self.user_id


@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('database.db')
    curs = conn.cursor()
    curs.execute("SELECT * from user where user_id= (?)", (user_id,))
    lu = curs.fetchone()
    if lu is None:
        return None
    else:
        return User(int(lu[0]), lu[1], lu[2], lu[3])




camera = cv2.VideoCapture(0)
# Load a sample picture and learn how to recognize it.
path = "Image"
images = []
classNames = []
myList = os.listdir(path)

# Create arrays of known face encodings and their names
for img in myList:
    curImg = cv2.imread(f'{path}/{img}')
    images.append(curImg)
    classNames.append(os.path.splitext(img)[0])

def findEncodings(images):
    encodeList = []
    for img in images:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encode = face_recognition.face_encodings(img)[0]
        encodeList.append(encode)
    return encodeList

encodeListKnown = findEncodings(images)


# Initialize some variables
face_locations = []
face_encodings = []
face_names = []
process_this_frame = 10

def gen_frames():
    global process_this_frame
    global face_locations
    global face_names
    global face_encodings
    while True:
        success, frame = camera.read() # read the camera frame
        frame = cv2.flip(frame, 1)
        if not success:
            break
        else:
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = small_frame[:, :, ::-1]

            
           
            # Find all the faces and face encodings in the current frame of video
            if process_this_frame == 10:
                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                face_names = []
                for face_encoding in face_encodings:
                    # See if the face is a match for the known face(s)
                    matches = face_recognition.compare_faces(encodeListKnown, face_encoding)
                    name = "Unknown"
                    # Or instead, use the known face with the smallest distance to the new face
                    face_distances = face_recognition.face_distance(encodeListKnown, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = classNames[best_match_index]

                    face_names.append(name)
                process_this_frame = 1
            process_this_frame += 1
            

            # Display the results
            for (top, right, bottom, left), name in zip(face_locations, face_names):
                # Scale back up face locations since the frame we detected in was scaled to 1/4 size
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4

                # Draw a box around the face
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

                # Draw a label with a name below the face
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def gen_frames_notpredict():
    while True:
           
        ## read the camera frame
        success,frame=camera.read()
        frame = cv2.flip(frame, 1)
        if not success:
            break
        else:
            ret,buffer=cv2.imencode('.jpg',frame)
            frame=buffer.tobytes()

        yield(b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/choose/<id>')
def choose(id):
    conn = sqlite3.connect('database.db')
    curs = conn.cursor()
    curs = conn.execute("SELECT * FROM product where productId = (?)", (id, ))
    data = curs.fetchone()
    return render_template("payment.html", data = data)

@app.route('/')
@app.route('/home', methods = ["GET", "POST"])
def home():
    return render_template('home.html')



@app.route('/history/', methods = ["POST", "GET"])
@login_required
def history():
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute('''
        select history.id, history.time, product.productId, product.Type, product.Price, product.Category
        from history 
        inner join product on history.id_product=product.productId
        where history.id_user=(?)''', (current_user.get_id(),))
    data = list(cur.fetchall())
    return render_template('history.html', data = data)

@app.route('/updatehistory/<id>', methods = ["POST", "GET"])
@login_required
def updatehistory(id):
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("insert into history(id_user, id_product, time)values(?,?,?)",
                        (current_user.get_id(), id, datetime.date.today()))
    cur.execute("update user set role = (?) where user_id = (?)", (1, current_user.get_id()))
    con.commit()
    con.close()
    return redirect("/")



@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = request.form['username']
        email = request.form['email_address']
        password = request.form['password1']
        con = sqlite3.connect("database.db")
        cur = con.cursor()
        cur.execute("select username from user where username=?", (username,))
        data1 = cur.fetchone()
        if data1:
            flash("Username are already exists", "danger")
            return redirect(url_for('register'))
        cur.execute("select email from user where email=?", (email,))
        data2 = cur.fetchone()
        if data2:
            flash("Email are already exists", "danger")
            return redirect(url_for('register'))
        else:
            cur.execute("insert into user(username,email,password,role)values(?,?,?,?)",
                        (username, email, password,0))
        con.commit()
        con.close()
        return redirect(url_for('login'))
    if form.errors != {}:
        for err_msg in form.errors.values():
            flash(f'{err_msg}', category='danger')
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        con = sqlite3.connect("database.db")
        cur = con.cursor()
        cur.execute("select * from user where username=?",
                    [form.username.data])
        data = cur.fetchall()
        if data:
            user = load_user(data[0][0])
            if form.username.data == user.username and user.verify_password(form.password.data):
                login_user(user)
                flash(f'Successfully login', category='success')
                return render_template("home.html")
            else:
                flash(f'Username or Password mismatch. Please try again!', category='danger')
        else:
            flash(f'Username or Password mismatch. Please try again!', category='danger')
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    flash("You have been logged out!", category='info')
    return redirect(url_for("home"))


@app.route('/product/')
@login_required
def product():
    conn = sqlite3.connect('database.db')
    curs = conn.cursor()
    curs = conn.execute("SELECT * FROM product where Category = (?)", ("community", ))
    community = curs.fetchall()
    curs = conn.execute("select count(*) FROM product where Category = (?)", ("community", ))
    countCom = curs.fetchone()

    curs = conn.execute("SELECT * FROM product where Category = (?)", ("professional", ))
    professional = curs.fetchall()
    curs = conn.execute("select count(*) FROM product where Category = (?)", ("professional", ))
    countPro = curs.fetchone()

    return render_template('product.html', community = community, professional = professional, countCom = countCom, countPro = countPro)


@app.route("/manager")
@login_required  
def view():
    con = sqlite3.connect("database.db")
    cur = con.cursor() 
    cur.execute("SELECT * FROM USER WHERE user_id = (?)", (current_user.get_id(), ))
    infor = cur.fetchone()
    if infor[7] != 2:
        return render_template('notadmin.html') 
    else: 
        con = sqlite3.connect("database.db")  
        con.row_factory = sqlite3.Row  
        cur = con.cursor()  
        cur.execute("select * from product")  
        rows = cur.fetchall()  

        cur.execute("select count(*) from history")
        number = cur.fetchone()
        
        cur.execute('''
        select history.id_product, product.price
        from history
        left join product where history.id_product=product.productId
        ''')
        money = cur.fetchall()

        total = 0
        for item in money:
            total += item[1]
        return render_template("index.html",rows = rows, number = number, total = total) 
 
@app.route("/manager/add")  
@login_required
def add():  
    return render_template("add.html")  
 
@app.route("/manager/savedetails",methods = ["POST","GET"]) 
@login_required 
def saveDetails():  
    msg = "msg"  
    if request.method == "POST":  
        try:   
            category = request.form["category"]  
            period = request.form["period"];	price = request.form["price"]

            with sqlite3.connect("database.db") as con:  
                cur = con.cursor()  
                cur.execute("INSERT into product (Category, Type, Price) values (?,?,?)",(category,period,price))  
                con.commit()  
                msg = "APP SUCCESSFULLY ADDED"  
        except:  
            con.rollback()  
            msg = "CAN NOT ADD APP"  
        finally:  
            return render_template("success.html",msg = msg)  
            con.close()  
 
@app.route("/manager/delete")  
@login_required
def delete():  
    return render_template("delete.html")  
 
@app.route("/manager/deleterecord",methods = ["POST"])  
@login_required
def deleterecord():  
    id = request.form["id"]  
    with sqlite3.connect("database.db") as con:  
        try:  
            cur = con.cursor()  
            cur.execute("delete from product where productId = ?",(id,))  
            msg = "APP SUCCESSFULLY REMOVE"  
        except:  
            msg = "CAN NOT REMOVE APP"  
        finally:  
            return render_template("delete_record.html",msg = msg)  

@app.route("/manager/update")
@login_required  
def update():  
    return render_template("update.html")  
 
@app.route("/manager/updaterecord",methods = ["POST"])
@login_required  
def updaterecord():  
    id = request.form["id"]; category = request.form["category"]; period = request.form["period"];	price = request.form["price"]
    with sqlite3.connect("database.db") as con:  
        try:  
            cur = con.cursor()  
            cur.execute("UPDATE product SET Category = ?, Type = ?, Price = ? WHERE productId = ?", (category, period, price, id)) 
            msg = "SUCCESSFULLY UPDATE"  
        except:  
            msg = "CAN NOT UPDATE INFORMATION OF THE APP"  
        finally:  
            return render_template("update_record.html",msg = msg)


@app.route("/manager/transaction")  
@login_required
def transaction():  
    con = sqlite3.connect("database.db")
    cur = con.cursor() 
    cur.execute("SELECT * FROM USER WHERE user_id = (?)", (current_user.get_id(), ))
    infor = cur.fetchone()
    if infor[7] != 2:
        return render_template('notadmin.html') 
    else: 
        con = sqlite3.connect("database.db")  
        con.row_factory = sqlite3.Row  
        cur = con.cursor()  
        cur.execute("SELECT h.id_user, h.id_product, h.time, p.Type, p.Price, p.Category FROM history h LEFT JOIN product p ON h.id_product=p.productID")  
        rows = cur.fetchall()  
        return render_template("transaction.html",rows = rows)


@app.route('/face')
@login_required
def face():
    con = sqlite3.connect("database.db")
    cur = con.cursor() 
    cur.execute("SELECT * FROM USER WHERE user_id = (?)", (current_user.get_id(), ))
    infor = cur.fetchone()
    if infor[7] == 1:
        return render_template('face.html')
    else:
        return render_template('please.html')


@app.route('/face/play')
@login_required
def predict():
    con = sqlite3.connect("database.db")
    cur = con.cursor() 
    cur.execute("SELECT * FROM USER WHERE user_id = (?)", (current_user.get_id(), ))
    infor = cur.fetchone()
    if infor[7] == 1:
        return render_template('face2.html')
    else:
        return render_template('please.html')


@app.route('/video_pause')
@login_required
def video_pause():
    return Response(gen_frames_notpredict(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/video_feed')
@login_required
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/profile')
def profile():
   con = sqlite3.connect("database.db")
   con.row_factory = sqlite3.Row
   cur = con.cursor()
   cur.execute("SELECT * FROM user")
   data  = cur.fetchall()
   return render_template("profile.html", data=data)

@app.route('/modify_name')
def modify_name():
   con = sqlite3.connect("database.db")
   con.row_factory = sqlite3.Row
   cur = con.cursor()
   cur.execute("SELECT * FROM user")
   data  = cur.fetchall()
   return render_template('modify_name.html', data=data)

@app.route('/name_result',methods = ['POST', 'GET'])
def name_result():
   if request.method == 'POST':
   
      try: 
         newName = request.form['new_name']

         with sqlite3.connect("database.db") as con:
            cur = con.cursor()
            
            cur.execute("UPDATE user SET name=? where user_id=?",(newName, current_user.get_id()))
            
            con.commit()
            msg = "Changed name successfully!"
      except:
         con = sqlite3.connect("database.db")
         con.rollback()
         msg = "There's some errors. Please try again!"

      finally:
         return render_template("result.html",msg = msg)
         con.close()  


@app.route('/modify_email')
def modify_email():
   con = sqlite3.connect("database.db")
   con.row_factory = sqlite3.Row
   cur = con.cursor()
   cur.execute("SELECT * FROM user")
   data  = cur.fetchall()
   return render_template('modify_email.html', data=data)

@app.route('/email_result',methods = ['POST', 'GET'])
def email_result():
   if request.method == 'POST':
   
      try: 
         newEmail = request.form['new_email']

         with sqlite3.connect("database.db") as con:
            cur = con.cursor()
            
            cur.execute("UPDATE user SET email=? where user_id=?",(newEmail, current_user.get_id()))
            
            con.commit()
            msg = "Changed email successfully!"
      except:
         con = sqlite3.connect("database.db")
         con.rollback()
         msg = "There's some errors. Please try again!"

      finally:
         return render_template("result.html",msg = msg)
         con.close()  


@app.route('/modify_password')
def modify_password():
   con = sqlite3.connect("database.db")
   con.row_factory = sqlite3.Row
   cur = con.cursor()
   cur.execute("SELECT * FROM user")
   data  = cur.fetchall()
   return render_template('modify_password.html', data=data)

@app.route('/password_result',methods = ['POST', 'GET'])
def password_result():
   if request.method == 'POST':
   
      try: 
         newPw = request.form['new_pw']
         newPw1 = request.form['new_pw1']
         if(newPw != newPw1):
            msg = "Passwords does not match. Try again!"
            return render_template("result.html",msg = msg)
         else:
            with sqlite3.connect("database.db") as con:
               cur = con.cursor()
               
               cur.execute("UPDATE user SET password=? where user_id=?",(newPw, current_user.get_id()))
               
               con.commit()
               msg = "Changed password successfully!"
      except:
         con = sqlite3.connect("database.db")
         con.rollback()
         msg = "There's some errors. Please try again!"

      finally:
         return render_template("result.html",msg = msg)
         con.close() 

if __name__=='__main__':
    app.run(debug=True)

#Set-ExecutionPolicy Unrestricted -Scope Process
#env\Scripts\activate