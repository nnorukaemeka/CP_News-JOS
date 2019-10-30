from flask import (Flask, render_template, request, redirect, url_for, session,logging, flash)
# from data import newsArticles
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from functools import wraps
from MySQLdb import escape_string as thwart
import gc
import os
import re
import smtplib




app = Flask(__name__)

#configure secret key
app.secret_key = os.urandom(24)
# app.config['SECRET_KEY'] = 'your_secret_string'

#configure Mysql database
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Olu1989!@'
app.config['MYSQL_DB'] = 'newsdb'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

#init MySQL
mysql = MySQL(app)


# newsArticles = newsArticles()



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


#INDEX
@app.route("/")
def homepage():
    return render_template("index.html")


#ABOUT ROUTE
@app.route("/about")
def history():
    return render_template("about.html")


#CAREERS ROUTE
@app.route("/careers")
def careers():
    return render_template("careers.html")



#REGISTER USER
@app.route("/register", methods=["GET","POST"])
def register():
    form = MyForm(request.form)
    if request.method == "POST" and form.validate():
        #get form fields
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data)) #hashes the password
        
        # Check if account exists using MySQL

        #create cursor
        cur = mysql.connection.cursor()

        #Get user by username
        result = cur.execute("SELECT * FROM signup WHERE email = %s", [email]) 

        account = cur.fetchone()
        # If account exists show error and validation checks
        if account:
            error = 'Account already exists!'
            return render_template("register.html", form=form, error=error)
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            error = 'Invalid email address!'
            return render_template("register.html", form=form, error=error)
        elif not re.match(r'[A-Za-z0-9]+', username):
            error = 'Username must contain only characters and numbers!'
            return render_template("register.html", form=form, error=error)
        else:
            # Account doesnt exists and the form data is valid, now insert new account into signup table
            cur.execute ("INSERT INTO signup (name, email, username, password) VALUES (%s, %s, %s, %s)", (name, email, username, password))

            # commit to database
            mysql.connection.commit()

            #close the cursor
            cur.close()
            gc.collect()
            #flash a message
            flash("You are now registered and can log in.", "success") #success is a category
            return redirect(url_for("login"))
    else:
        #if request.method == "GET"
        return render_template("register.html", form=form)



#LOGIN USER
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
                session['username'] = data['username']
                session['password'] = password_candidate
                flash("You are successfully logged in", "success")
                return redirect(url_for("dashboard"))
            else:
                error = 'Invalid credentials, try again.'
                # flash("Failed, wrong inputs!", "warning")
                return render_template("login.html", error=error)
                # app.logger.info('Password mismatched!') #for development purpose
        else:
            error = 'Invalid credentials, try again.'
            # flash("User not found!", "warning")
            return render_template("login.html", error=error)
            # app.logger.info('User not found!') #for development purpose
        
        #close the cursor
        cur.close()
        gc.collect()
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


@app.route('/dashboard/profile')
@is_logged_in
def profile():
    # Check if user is loggedin
    if session['logged_in'] == True:
        # We need all the account info for the user so we can display it on the profile page

        #create cursor
        cur = mysql.connection.cursor()

        #Get user by username
        result = cur.execute("SELECT * FROM signup WHERE username = %s", [session['username']]) 

        account = cur.fetchone()
        password = sha256_crypt.decrypt(str(account['password']))
        # Show the profile page with account info
        return render_template('profile.html', account=account, password=password)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


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
@app.route("/article/<string:id>/", methods=["GET","POST"])
def article(id):
    #Get form
    form = ArticleForm(request.form)

    #create cursor
    cur = mysql.connection.cursor()
    #Fetch all articles
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id]) 
    article = cur.fetchone()   #select single article with the id from table

    
    result2 = cur.execute("SELECT * FROM comments WHERE articles_id = %s", [id])
    comment = cur.fetchall()

    context = [article,comment]

    if request.method == "POST":
        #get form fields
        body = request.form['body']
        article_id = request.form['id']
        
        #create cursor
        cur = mysql.connection.cursor()

        #post data into database
        cur.execute ("INSERT INTO comments (articles_id, username, body) VALUES (%s, %s, %s)", (article_id, session['username'], body))

        # commit to database
        mysql.connection.commit()

        #close the cursor
        cur.close()
        
        #flash a message
        flash("Comment Added successfully!", "success") #success is a category
        return redirect(url_for("articles"))

    elif result >0 and result2>0:
        return render_template("article.html", context=context, form=form, id=id)
    elif result >0 and result2==0:
        #flash a message
        flash("No Comment Found", "info")
        return render_template("article.html", context=context, form=form, id=id)
    else:
        #flash a message
        flash("No Article Found", "info")
        return redirect(url_for("articles"))



@app.route("/edit_article/<string:id>/", methods=["GET","POST"])
@is_logged_in
def edit_article(id):
    #if request.method == "GET"

    #create cursor
    cur = mysql.connection.cursor()
    #Fetch single row with the article's id
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id]) 
    
    article = cur.fetchone()   #select single article with the id from table
    
    #Get form
    form = ArticleForm(request.form)
    
    #Populate the Article form field
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == "POST" and form.validate():
        #get form fields
        title = request.form['title']
        body = request.form['body']
    
        #create cursor
        cur = mysql.connection.cursor()

        #post data into database
        cur.execute ("UPDATE articles SET author=%s, title=%s, body=%s WHERE id=%s", (session['username'], title, body, id))

        # commit to database
        mysql.connection.commit()

        #close the cursor
        cur.close()

        #flash a message
        flash("Article Updated successfully!", "success") #success is a category
        return redirect(url_for("dashboard"))
    return render_template("edit_article.html", form=form)


@app.route("/delete_article/<string:id>/", methods=["POST"])
@is_logged_in
def delete_article(id):

    #create cursor
    cur = mysql.connection.cursor()

    #Delete single row with the article's id
    cur.execute ("DELETE FROM articles WHERE id=%s", id)
    
    # commit to database
    mysql.connection.commit()

    #close the cursor
    cur.close()

    #flash a message
    flash("Article Deleted Successfully!", "success") #success is a category
    return redirect(url_for("dashboard"))




#RUN THE PYTHON APP.PY
if __name__ == "__main__":        # on running python app.py
    app.run(debug = True)                     # run the flask app