from flask import Flask, render_template, request, session, url_for, redirect
import hashlib
import pymysql
import datetime
import os
import copy
from werkzeug.utils import secure_filename

SALT = 'cs3083'  # Define what your salt will be.
app = Flask(__name__)

# Setup the connection to your database. You can change port, user, password, and db.
# Configure MySQL
conn = pymysql.connect(host='localhost',
                       port=8889,
                       user='root',
                       password='root',
                       database='Finstagram',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)


# Define a function that will execute a query and return just one result. This function
# makes more sense once you understand the bottom three routes. You do not have to use this.
# You can setup your own way of running queries and grabbing the results. This is just one way.
def run_sql_one(query, data):
    cursor = conn.cursor()
    cursor.execute(query, data)
    data = cursor.fetchone()
    cursor.close()
    return data


# Define a function that will execute a query and return all results. This function
# makes more sense once you understand the bottom three routes. You do not have to use this.
# You can setup your own way of running queries and grabbing the results. This is just one way.
def run_sql_all(query, data):
    cursor = conn.cursor()
    cursor.execute(query, data)
    data = cursor.fetchall()
    cursor.close()
    return data


# Define route for the homepage.
@app.route('/')
def home():
    rows = []

    if (session.get('isLoggedIn') is None):
        # Initialize the session information.
        session['isLoggedIn'] = 'Login'
        text = 'Welcome To Finstagram, Please Login To Start Using This Program.'
    else:
        # Get the path names of all images for this user.
        query = '(SELECT DISTINCT p.filePath, p.postingDate FROM BelongTo b, SharedWith s, Photo p WHERE b.username = %s AND b.groupCreator = p.poster) UNION (SELECT DISTINCT filePath, postingDate FROM Photo WHERE poster = %s) UNION (SELECT DISTINCT filePath, postingDate FROM Photo p, Follow f WHERE f.follower = %s AND f.followee = p.poster AND f.followStatus = 1) ORDER BY postingDate DESC'
        data = run_sql_all(query, (session['username'], session['username'], session['username']))
        for i in range(len(data)):
            rows.append("/static/{0}".format(data[i]['filePath']))
            print(data[i]['filePath'])
        text = ''
    if (session.get('username') is None):
        session['username'] = ''
    return render_template('index.html',
                           isLoggedIn=session['isLoggedIn'],
                           username=session['username'],
                           photoURLs=rows,
                           content=text)


# Define route for login
@app.route('/login')
def login():
    if (session.get('isLoggedIn') == 'Login'):
        # HTML for loginpage is easy to make. Just have a form with action pointing to loginauth with post method.
        return render_template('login.html')
    else:
        session['isLoggedIn'] = 'Login'
        return render_template('index.html', isLoggedIn='Login',
                               content='Welcome To Finstagram, Please Login To Start Using This Program.')


# Define route for register
@app.route('/register')
def register():
    return render_template('register.html')


# Define route for login
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAdd():
    username = request.form['username']
    password = request.form['password'] + SALT
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    firstname = request.form['First Name']
    lastname = request.form['Last Name']
    email = request.form['email']

    # Run a query with the appropriate values inserted to check if it is a valid user. Grab one result. Null if empty
    query = 'SELECT * FROM Person WHERE username = %s'
    data = run_sql_one(query, (username))

    if (data):
        return render_template('register.html', error='Username is already in use.')
    else:
        # Insert the file into the database.
        query = 'INSERT INTO Person VALUES (%s, %s, %s, %s, %s)'
        cursor = conn.cursor()
        cursor.execute(query, (username, hashed_password, firstname, lastname, email))
        cursor.close()
        return render_template('login.html')


# Define login authentication process
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    # Grab the username and password from the form. Add the SALT at the end of password. Hash the password.
    username = request.form['username']
    password = request.form['password'] + SALT
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()

    # Run a query with the appropriate values inserted to check if it is a valid user. Grab one result. Null if empty
    query = 'SELECT * FROM Person WHERE username = %s and password = %s'
    data = run_sql_one(query, (username, hashed_password))

    # NOTE: In order for this to work you must hash the password when the user registers and insert the hashed version into the password.
    # Attempt to login and redirect to the homepage if success. Otherwise, it is an invalid login and returns to the login page.
    if (data):
        # Save the username into session.
        session['username'] = data['username']
        session['isLoggedIn'] = 'Logout'

        # Get the path names of all images for this user.
        query = 'SELECT DISTINCT p.filePath FROM (SELECT groupName FROM BelongTo WHERE username = %s) res, SharedWith s, Photo p WHERE res.groupName = s.groupName AND s.pID = p.pID AND p.allFollowers = 1 ORDER BY postingDate'
        data = run_sql_all(query, (data['username']))
        rows = []
        for i in range(len(data)):
            rows.append("/static/{0}".format(data[i]['filePath']))
            print(data[i]['filePath'])
        return redirect(url_for('home', photoURLs=rows, isLoggedIn=session['isLoggedIn']))
    else:
        return render_template('login.html', error='Invalid login. Please try again')


# Define image display
@app.route('/image', methods=['GET'])
def image():
    # Grab the username and password from the form. Add the SALT at the end of password. Hash the password.
    imgName = request.args['img_name']

    # Get all poster username information so we can output the right person to the screen.
    query = 'SELECT poster FROM Photo WHERE filePath = %s'
    data = run_sql_one(query, (imgName[8:]))
    username = data['poster']

    # Run a query with the appropriate values inserted to check if it is a valid user. Grab one result. Null if empty
    query = 'SELECT p.pID, e.firstName, e.lastName, p.postingDate FROM Photo p, Person e WHERE p.poster = %s AND p.poster = e.username AND filePath = %s'
    data = run_sql_one(query, (username, imgName[8:]))

    # Get the data from the query.
    pID = int(data['pID'])
    firstName = data['firstName']
    lastName = data['lastName']
    postDate = data['postingDate'].strftime("%m/%d/%Y, %H:%M:%S")

    # Determine who was tagged in the photo.
    query = 'SELECT e.firstName, e.lastName FROM Photo p, Tag t, Person e WHERE p.pID = t.pID AND p.pID = %s AND t.username = e.username AND t.tagStatus = 1'
    data = run_sql_all(query, (pID))
    firstNameTagRows = []
    lastNameTagRows = []
    if (session['username'] == username):
        for i in range(len(data)):
            firstNameTagRows.append(data[i]['firstName'])
            lastNameTagRows.append(data[i]['lastName'])

    # Determine who has reacted to the photo.
    query = 'SELECT r.username, r.emoji FROM Photo p, ReactTo r WHERE p.pID = r.pID AND p.pID = %s'
    data = run_sql_all(query, (pID))
    usernameReactRows = []
    emojiReactRows = []
    if (session['username'] == username):
        for i in range(len(data)):
            usernameReactRows.append(data[i]['username'])
            # No empty emojis on screen.
            if (data[i]['emoji'] is not None):
                emojiReactRows.append(data[i]['emoji'])
            else:
                emojiReactRows.append('')

    return render_template('image.html',
                           fName=firstName,
                           lName=lastName,
                           pDate=postDate,
                           fnTagRows=firstNameTagRows,
                           lsTagRows=lastNameTagRows,
                           numTags=len(firstNameTagRows),
                           unReactRows=usernameReactRows,
                           emReactRows=emojiReactRows,
                           numReacts=len(usernameReactRows),
                           imgName=imgName,
                           isLoggedIn=session['isLoggedIn'])


# Define route for trying to post
@app.route('/post')
def post():
    # Get all groups you belong to.
    query = 'SELECT groupName FROM BelongTo WHERE username = %s'
    data = run_sql_all(query, (session['username']))
    groups = []
    for i in range(len(data)):
        groups.append(data[i]['groupName'])

    # Render post.html.
    return render_template('post.html',
                           isLoggedIn='Login',
                           groups=groups)


# Determine if the file has the appropriate extension to it.
def allowedExtensions(file):
    return '.' in file and file.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


# Define route for inserting the post
@app.route('/photoAdd', methods=['GET', 'POST'])
def postAdd():
    # Get information about the name, caption, visibility, and groups that this photo will be in.
    name = request.files['filename'].filename
    caption = request.form['caption']
    isVisible = 0
    if (request.form.get('isvisible') is not None):
        isVisible = 1
    selGroups = []
    if (request.form.get('groups') is not None):
        selGroups = request.form.getlist('groups')
    print(selGroups, isVisible)

    # Get all group names that you belong to.
    query = 'SELECT groupName FROM BelongTo WHERE username = %s'
    data = run_sql_all(query, (session['username']))
    groups = []
    for i in range(len(data)):
        groups.append(data[i]['groupName'])

    # Check if the file is allowed.
    if (allowedExtensions(name)):
        # Save the file.
        UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
        savedFile = request.files['filename']
        savedFile.save(os.path.join(UPLOAD_FOLDER, savedFile.filename))

        # Insert the file into the database.
        query = 'INSERT INTO Photo(postingDate, filePath, allFollowers, caption, poster) VALUES (NOW(), %s, %s, %s, %s)'
        cursor = conn.cursor()
        cursor.execute(query, (request.files['filename'].filename, isVisible, caption, session['username']))
        cursor.close()

        # get the new PID of the photo for sharing with the group.
        query = 'SELECT pID FROM Photo WHERE filePath = %s'
        data = run_sql_one(query, (savedFile.filename))
        pID = int(data['pID'])

        # Share to all groups selected.
        for i in range(len(selGroups)):
            # Select the creator and share with the group.
            query = 'SELECT groupCreator FROM FriendGroup WHERE groupName = %s'
            data = run_sql_one(query, (selGroups[i]))
            print(selGroups[i])
            creator = data['groupCreator']

            # Share with the group.
            query = 'INSERT INTO SharedWith VALUES (%s, %s, %s)'
            cursor = conn.cursor()
            cursor.execute(query, (pID, selGroups[i], creator))
            cursor.close()
        conn.commit()

        return render_template('post.html', groups=groups, success='File Uploaded!')
    else:
        return render_template('post.html', groups=groups, error='Invalid File: Not an image of type jpg, png, or gif')


# Define route for inserting the post
@app.route('/followers', methods=['GET', 'POST'])
def followers():
    # Select all followers for me.
    query = 'SELECT follower FROM Follow WHERE followee = %s AND followStatus = 0'
    data = run_sql_all(query, (session['username']))
    followers = []
    for i in range(len(data)):
        followers.append(data[i]['follower'])

    return render_template('followers.html', reqList=followers, msg='')


# Define route for inserting the post
@app.route('/addFollower', methods=['GET', 'POST'])
def addFollower():
    followee = request.form['followee']

    # Check if followee exists.  If so insert it.
    query = 'SELECT * FROM Person WHERE username = %s'
    data = run_sql_one(query, (followee))

    if (data):
        # Insert Follow request for followee.
        query = 'INSERT INTO Follow VALUES (%s, %s, %s)'
        cursor = conn.cursor()
        cursor.execute(query, (session['username'], followee, 0))
        cursor.close()
        conn.commit()

        # Update ist of request to the screen.
        query = 'SELECT follower FROM Follow WHERE followee = %s AND followStatus = 0'
        data = run_sql_all(query, (session['username']))
        followers = []
        for i in range(len(data)):
            followers.append(data[i]['follower'])

        return render_template('followers.html', followmsg='Success! Sent Follower Request.')
    else:
        # Update ist of request to the screen.
        query = 'SELECT follower FROM Follow WHERE followee = %s AND followStatus = 0'
        data = run_sql_all(query, (session['username']))
        followers = []
        for i in range(len(data)):
            followers.append(data[i]['follower'])
        return render_template('followers.html', followmsg='Failed. Could Not Find Follower.')


# Define route for inserting the post
@app.route('/updateRequest', methods=['GET', 'POST'])
def updateRequest():
    # If no user is chosen, then reject automatically.
    if (request.form.get('reqAccept') is None):
        return render_template('followers.html', acceptmsg='Failed. No user accepted')
    else:
        # Get the request.
        user = request.form['reqAccept']
        method = request.form['subReq']

        # Accept will update the followStatus to 1.
        # Deny will delete the entire record.
        if (method == 'Accept'):
            query = 'UPDATE Follow SET followStatus = 1 WHERE follower = %s AND followee = %s'
            cursor = conn.cursor()
            cursor.execute(query, (user, session['username']))
            cursor.close()
        else:
            query = 'DELETE FROM Follow WHERE follower = %s AND followee = %s AND followStatus = 0'
            cursor = conn.cursor()
            cursor.execute(query, (user, session['username']))
            cursor.close()
        conn.commit()

        # Update the requests that are remaining.
        query = 'SELECT follower FROM Follow WHERE followee = %s AND followStatus = 0'
        data = run_sql_all(query, (session['username']))
        followers = []
        for i in range(len(data)):
            followers.append(data[i]['follower'])

        return render_template('followers.html', reqList=followers, acceptmsg='')


# Define route for inserting the post
@app.route('/addgroup')
def addgroup():
    return render_template('addgroup.html', msg='')


# Define route for inserting the post
@app.route('/addgroupReq', methods=['GET', 'POST'])
def addgroupRequest():
    # Determine name and description of group.
    name = request.form['name']
    description = request.form['description']

    # No name provided is automatic rejection.
    if (name == ''):
        return render_template('addgroup.html', msg='Error: No group name provided.')
    else:
        # Get the username to make sure it doesn't exist.  If so, reject it.
        query = 'SELECT * FROM FriendGroup WHERE groupName = %s AND groupCreator = %s'
        data = run_sql_all(query, (name, session['username']))
        if (data):
            return render_template('addgroup.html', msg='Error: Group already exists for this user.')
        else:
            # Insert the group into the DB.
            query = 'INSERT INTO FriendGroup VALUES (%s, %s, %s)'
            cursor = conn.cursor()
            cursor.execute(query, (name, session['username'], description))
            cursor.close()

            # Insert the user into the group into the DB.
            query = 'INSERT INTO BelongTo VALUES (%s, %s, %s)'
            cursor = conn.cursor()
            cursor.execute(query, (session['username'], name, session['username']))
            cursor.close()
            conn.commit()

            return render_template('addgroup.html', msg='Success: Group Created!')


# secret key must be set in order to use session. think of it as cookies
app.secret_key = 'c89vhj9nq92ign9hnvasv'

# Run on localhost port 5000, and restart flask automatically on changes. Turn off on production.
if __name__ == "__main__":
    app.run('localhost', 5000, debug=True)
