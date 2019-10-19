from flask import (Flask, render_template, request, redirect, url_for, session,logging, flash)
# from data import newsArticles
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from functools import wraps
import os
import sys


app = Flask(__name__)
app.secret_key = os.urandom(24)


#configure Mysql database
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Olu1989!@'
app.config['MYSQL_DB'] = 'newsdb'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

#init MySQL
mysql = MySQL(app)


# newsArticles = newsArticles()

#INDEX
@app.route("/")
def homepage():
    return render_template("index.html")

#ABOUT
# @app.route("/about")
# def about():
#     return render_template("about.html")

@app.route("/newsfeed")
def newsfeed():
    return render_template("newsfeed.html")

#DISPLAY ARTICLES BY TITLE
@app.route("/articles")
def articles():
     #create cursor
    cur = mysql.connection.cursor()
    #Fetch all articles
    result = cur.execute("SELECT * FROM articles") 
    data = cur.fetchall()   #select all data from table
    if result >0:
        return render_template("articles.html", articles=data)
    else:
        msg = 'No Articles Found'
        return render_template("articles.html", msg=msg)
    #Close cursor
    cur.close()

#DISPLAY SINGLE ARTICLE
@app.route("/article/<string:id>/")
def article(id):
    #create cursor
    cur = mysql.connection.cursor()
    #Fetch all articles
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id]) 
    
    data = cur.fetchall()   #select single article with the id from table
    
    if result >0:
        return render_template("article.html", article=data)
    else:
        msg = 'No Articles Found'
        return render_template("article.html", msg=msg)
    #Close cursor
    cur.close()
    

#REGISTER FORM CLASS
class MyForm(Form):
    name = StringField(u'Name', validators=[validators.input_required(), validators.length(min=3,max=50)])
    email = StringField(u'Email', validators=[validators.input_required(), validators.length(min=3,max=50)])
    username = StringField(u'Username', validators=[validators.input_required(), validators.length(min=3,max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(), 
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


#ARTICLE FORM CLASS
class ArticleForm(Form):
    title = StringField(u'Title', validators=[validators.input_required(), validators.length(min=3,max=200)])
    body = TextAreaField(u'Body', validators=[validators.input_required(), validators.length(min=30)])


#CHECK IF USER IS LOGGED IN
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login','danger')
            return redirect(url_for("login"))
    return wrap


#REGISTER ROUTE
@app.route("/register", methods=["GET","POST"])
def register():
    form = MyForm(request.form)
    if request.method == "POST" and form.validate():
        #get form fields
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data)) #hashes the password
        
        #create cursor
        cur = mysql.connection.cursor()

        #post data into database
        cur.execute ("INSERT INTO signup (name, email, username, password) VALUES (%s, %s, %s, %s)", (name, email, username, password))

        # commit to database
        mysql.connection.commit()

        #close the cursor
        cur.close()

        #flash a message
        flash("You are now registered and can log in.", "success") #success is a category
        return redirect(url_for("login"))
    #if request.method == "GET"
    return render_template("register.html", form=form)


#LOGIN ROUTE
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        #Get form fields
        username = request.form['username']
        password_candidate = request.form['password']
        
        #create cursor
        cur = mysql.connection.cursor()

        #Get user by username
        result = cur.execute("SELECT * FROM signup WHERE username = %s", [username]) 

        if result>0:
            #Get the hash
            data = cur.fetchone()
            password = data['password']

            #compare passwords
            if sha256_crypt.verify(password_candidate, password):
                # app.logger.info('Password matched!') #for development purpose
                session['logged_in'] = True
                session['username'] = username
                flash("You are successfully logged in", "success")
                return redirect(url_for("dashboard"))
            else:
                error = 'Invalid Login Credentials!'
                # flash("Failed, wrong inputs!", "warning")
                return render_template("login.html", error=error)
                # app.logger.info('Password mismatched!') #for development purpose
        else:
            error = 'User Not Found!'
            # flash("User not found!", "warning")
            return render_template("login.html", error=error)
            # app.logger.info('User not found!') #for development purpose
        
        #close the cursor
        cur.close()

    #if request.method == "GET"
    return render_template("login.html")
    

#DASHBOARD ROUTE
@app.route("/dashboard")
@is_logged_in
def dashboard():
     #create cursor
    cur = mysql.connection.cursor()
    #Fetch all articles
    result = cur.execute("SELECT * FROM articles") 
    data = cur.fetchall()   #select all data from table
    if result >0:
        return render_template("dashboard.html", articles=data)
    else:
        msg = 'No Articles Found'
        return render_template("dashboard.html", msg=msg)
    #Close cursor
    cur.close()



#LOGOUT
@app.route("/logout")
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for("login"))


#ADD_ARTICLE ROUTE
@app.route("/add_article", methods=["GET","POST"])
@is_logged_in
def add_articles():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        #get form fields
        title = form.title.data
        body = form.body.data
        
        #create cursor
        cur = mysql.connection.cursor()

        #post data into database
        cur.execute ("INSERT INTO articles (author, title, body) VALUES (%s, %s, %s)", (session['username'], title, body))

        # commit to database
        mysql.connection.commit()

        #close the cursor
        cur.close()

        #flash a message
        flash("Article successfully added!", "success") #success is a category
        return redirect(url_for("dashboard"))
    #if request.method == "GET"
    return render_template("add_article.html", form=form)



#HISTORY ROUTE
@app.route("/history")
def history():
    return render_template("history.html")


#VISION ROUTE
@app.route("/vision")
def vision():
    return render_template("vision.html")


#MISSION ROUTE
@app.route("/mission")
def mission():
    return render_template("mission.html")


#CAREERS ROUTE
@app.route("/careers")
def careers():
    return render_template("careers.html")


#RUN THE PYTHON APP.PY
if __name__ == "__main__":        # on running python app.py
    app.run(debug = True)                     # run the flask app