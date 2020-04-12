#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect
import hashlib
import pymysql

#Initialize the app from Flask
app = Flask(__name__)

# Configure MySQL
conn = pymysql.connect(host='localhost',
                       port=8889,
                       user='root',
                       password='root',
                       db='Finstagram',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)


# Define a route to hello function
@app.route('/')
def hello():
    # return ('hello world')
    return render_template('index.html')

#Define a function that will execute a query and return just one result. This function
#makes more sense once you understand the bottom three routes. You do not have to use this.
#You can setup your own way of running queries and grabbing the results. This is just one way.
def run_sql_one(query, data):
    cursor = conn.cursor()
    cursor.execute(query, data)
    data = cursor.fetchone()
    cursor.close()
    return data


# Define route for login
@app.route('/login')
def login():
    return render_template('login.html')


# Define route for register
@app.route('/register')
def register():
    return render_template('register.html')


salt = 'cs3083'


# Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    # grabs information from the forms
    username = request.form['username']
    password = request.form['password'] + salt

    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()

    # cursor used to send queries
    cursor = conn.cursor()
    # executes query
    query = 'SELECT * FROM Person WHERE username = %s and password = %s'
    cursor.execute(query, (username, password))
    # stores the results in a variable
    data = run_sql_one(query, (username, hashed_password))
    error = None
    if (data):
        # creates a session for the the user
        # session is a built in
        session['username'] = data['username']
        return redirect(url_for('home'))
    else:
        # returns an error message to the html page
        error = 'Invalid login or username'
        return render_template('login.html', error=error)


# Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    # grabs information from the forms
    username = request.form['username']
    password = request.form['password'] + salt
    email = request.form['email']
    firstName = request.form['First Name']
    lastName = request.form['Last Name']

    # cursor used to send queries
    cursor = conn.cursor()
    # executes query
    queryUsername = 'SELECT * FROM Person WHERE username = %s'
    cursor.execute(queryUsername, (username))
    # stores the results in a variable
    dataUsername = cursor.fetchone()
    # use fetchall() if you are expecting more than 1 data row
    error = None

    if (dataUsername):
        # If the previous query returns data, then user exists
        error = "This user already exists"
        return render_template('register.html', error=error)

    # cursor used to send queries
    cursor = conn.cursor()
    # executes query
    queryEmail = 'SELECT * FROM Person WHERE email = %s'
    cursor.execute(queryEmail, (email))
    # stores the results in a variable
    dataEmail = cursor.fetchone()
    # use fetchall() if you are expecting more than 1 data row
    error = None

    if (dataEmail):
        # If the previous query returns data, then a user with this email exists
        error = "This email is already registered"
        return render_template('register.html', error=error)
    else:
        ins = 'INSERT INTO Person VALUES(%s, %s, %s, %s, %s)'
        cursor.execute(ins, (username, password, email, firstName, lastName))
        conn.commit()
        cursor.close()
        return render_template('index.html')

@app.route('/home')
def home():
    user = session['username']
    cursor = conn.cursor();
    #query = 'SELECT ts, blog_post FROM blog WHERE username = %s ORDER BY ts DESC'
    #cursor.execute(query, (user))
    #data = cursor.fetchall()
    #cursor.close()
    return render_template('home.html', username=user, posts=data)



@app.route('/addFriendGroup', methods=['GET', 'POST'])
def addFriendGroup():
    groupName = request.form['groupName']
    description = request.form['description']
    username = session['username']

    # cursor used to send queries
    cursor = conn.cursor()
    # executes query
    query = 'SELECT * FROM FriendGroup WHERE groupCreator = %s AND groupName = %s'
    cursor.execute(query, (groupCreator, groupName))
    # stores the results in a variable
    data = run_sql_one(query, (groupCreator, groupName))
    # use fetchall() if you are expecting more than 1 data row
    error = None

    if(data):
    # If the previous query returns data, then a group with this name owned by the user exists
        error = "You have already used this name for another group"
        return render_template('addFriendGroup.html', error=error)
    else:
        ins = 'INSERT INTO FriendGroup VALUES(%s, %s, %s)'
        cursor.execute(ins, (description, groupCreator, groupName))
        conn.commit()
        cursor.close()
        return render_template('addFriendGroup.html')

# @app.route('/post', methods=['GET', 'POST'])
# def post():
#     username = session['username']
#     cursor = conn.cursor();
#     blog = request.form['blog']
#     query = 'INSERT INTO blog (blog_post, username) VALUES(%s, %s)'
#     cursor.execute(query, (blog, username))
#     conn.commit()
#     cursor.close()
#     return redirect(url_for('home'))


# @app.route('/select_blogger')
# def select_blogger():
#     # check that user is logged in
#     # username = session['username']
#     # should throw exception if username not found
#
#     cursor = conn.cursor();
#     query = 'SELECT DISTINCT username FROM blog'
#     cursor.execute(query)
#     data = cursor.fetchall()
#     cursor.close()
#     return render_template('select_blogger.html', user_list=data)

@app.route('/viewVisiblePhotos', methods=["GET", "POST"])
def viewVisiblePhotos():
     poster = request.args['poster']
     cursor = conn.cursor();
     query = 'SELECT postingDate, pID FROM photo WHERE poster = %s ORDER BY postingDate DESC'
     cursor.execute(query, poster)
     data = cursor.fetchall()
     cursor.close()
     return render_template('show_posts.html', poster_name=poster, posts=data)


@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')


app.secret_key = 'some key that you will never guess'
# Run the app on localhost port 5000
# debug = True -> you don't have to restart flask
# for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug=True)
