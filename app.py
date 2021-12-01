
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


@app.route('/profile', methods = ["GET", "POST"])
@login_required
def profile():
    return 0

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
            cur.execute("insert into user(username,email,password)values(?,?,?)",
                        (username, email, password))
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
def view():  
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
def add():  
    return render_template("add.html")  
 
@app.route("/manager/savedetails",methods = ["POST","GET"])  
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
def delete():  
    return render_template("delete.html")  
 
@app.route("/manager/deleterecord",methods = ["POST"])  
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
def update():  
    return render_template("update.html")  
 
@app.route("/manager/updaterecord",methods = ["POST"])  
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
def transaction():  
    con = sqlite3.connect("database.db")  
    con.row_factory = sqlite3.Row  
    cur = con.cursor()  
    cur.execute("SELECT h.id_user, h.id_product, h.time, p.Type, p.Price, p.Category FROM history h LEFT JOIN product p ON h.id_product=p.productID")  
    rows = cur.fetchall()  
    return render_template("transaction.html",rows = rows)

if __name__ == '__main__':
    app.run(debug=True)

#Set-ExecutionPolicy Unrestricted -Scope Process
#env\Scripts\activate