from gettext import gettext
from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    flash,

)
from functools import wraps

import os, math
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import json
from datetime import date as d
from smtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

with open("config.json", "r") as c:
    params = json.load(c)["params"]

local_server = True
app = Flask(__name__)
app.secret_key = "super-secret-key"

app.config["UPLOAD_FOLDER"] = params["upload_location"]
app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USE_TLS=False,
    MAIL_USERNAME=params["gmail-user"],
    MAIL_PASSWORD=params["gmail-password"],
)

mail = Mail(app)
db_name = "learn2cod.db"
if local_server:
    app.config["SQLALCHEMY_DATABASE_URI"] = params["local_uri"] + db_name

else:
    app.config["SQLALCHEMY_DATABASE_URI"] = params["prod_uri"]

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


a = 0


class Contacts(db.Model):

    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone_num = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(20))
    email = db.Column(db.String(20), nullable=False)


class Posts(db.Model):

    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(12), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    tagline = db.Column(db.String(12))

    date = db.Column(db.String(12))
    img_file = db.Column(db.String(12))

    # email = db.Column(db.String(120),  nullable=False)


class Registration(db.Model):

    username = db.Column(db.String(80), primary_key=True)
    name = db.Column(db.String(80))
    email = db.Column(db.String(80), nullable=True)
    pasword = db.Column(db.String(80), nullable=False)


def login_required(f):
    @wraps(f)
    def wrap():
        if a:
            return f()
        else:

            flash("You need to login first")
            return redirect("/login")

    return wrap


@app.route("/")
def index():
    posts = Posts.query.filter_by().all()
    post_len = len(posts)
    last = math.ceil(post_len / int(params["no_of_posts"]))
    page = request.args.get("page")
    print("Page", page)
    if not str(page).isnumeric():
        page = 1
    page = int(page)

    posts = posts[
        (page - 1)
        * int(params["no_of_posts"]) : (page - 1)
        * int(params["no_of_posts"])
        + int(params["no_of_posts"])
    ]

    if page == 1:
        prev = "#"
        next = "/?page=" + str(page + 1)

    elif page == last:
        prev = "/?page=" + str(page - 1)
        next = "#"

    else:
        prev = "/?page=" + str(page - 1)
        next = "/?page=" + str(page + 1)
    hide = False
    if post_len<=page*params["no_of_posts"]:
        print("IN if",post_len, len(posts), (page*params["no_of_posts"]))
        hide = True
    prev_hide = False
    if prev == "#":
        prev_hide = True
    if next == "#":
        hide = True
    return render_template(
        "index.html", params=params, posts=posts, prev=prev, next=next, hide=hide, prev_hide = prev_hide
    )


@app.route("/post/<string:post_slug>", methods=["GET"])
def post_route(post_slug):

    post = Posts.query.filter_by(slug=post_slug).first()

    return render_template("post.html", params=params, post=post)


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" in session and session["user"] == params["admin_user"]:
        posts = Posts.query.all()

        return render_template("dashboard.html", params=params, posts=posts)

    if request.method == "POST":
        username = request.form.get("uname")
        userpass = request.form.get("pass")

        if (
            username == params["admin_user"]
            and userpass == params["admin_password"]
        ):
            # set the session variable
            session["user"] = username
            posts = Posts.query.all()
            return render_template(
                "dashboard.html", params=params, posts=posts
            )

        else:
            flash("Wrong Username or Password")
            return render_template("admin.html", params=params)

    else:
        return render_template("admin.html", params=params)


@app.route("/about")
def about():
    return render_template("about.html", params=params)


@app.route("/editor")
def editor():
    return render_template("editor.html", params=params)


@app.route("/practice")
def practice():
    if "logged_in" in session and session["logged_in"]:
        return render_template("practice.html", params=params)
    else:
        return redirect("/login")


@app.route("/edit/<string:sno>", methods=["GET", "POST"])
def edit(sno):
    if "user" in session and session["user"] == params["admin_user"]:
        if request.method == "POST":
            box_title = request.form.get("title")
            tline = request.form.get("tline")
            slug = request.form.get("slug")
            content = request.form.get("content")
            img_file = request.form.get("img_file")
            date = d.today()

            if sno == "0":
                post = Posts(
                    title=box_title,
                    slug=slug,
                    content=content,
                    tagline=tline,
                    img_file=img_file,
                    date=date,
                )
                db.session.add(post)
                db.session.commit()

            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = box_title
                post.slug = slug
                post.content = content
                post.tagline = tline
                post.img_file = img_file
                post.date = date
                db.session.commit()
                return redirect("/edit/" + sno)

        post = Posts.query.filter_by(sno=sno).first()
        return render_template("edit.html", params=params, sno=sno, post=post)
    else:

        return dashboard()


@app.route("/uploader", methods=["GET", "POST"])
def uploader():
    if "user" in session and session["user"] == params["admin_user"]:

        if request.method == "POST":
            f = request.files["file1"]
            f.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"], secure_filename(f.filename)
                )
            )
            return "Uploaded Successfully!"


@app.route("/delete/<string:sno>", methods=["GET", "POST"])
def delete(sno):
    if "user" in session and session["user"] == params["admin_user"]:
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
        return redirect("/dashboard")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":

        """Add entry to DB"""
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        message = request.form.get("message")
        if not name or not email or not phone or not message:
            flash('All fields are required, Please Try Again!')
            return redirect("/contact")
        print("Email: ", request.form)
        entry = Contacts(
            name=name,
            phone_num=phone,
            msg=message,
            date=d.today(),
            email=email,
        )
        db.session.add(entry)
        db.session.commit()

        msg = MIMEMultipart()
        msg["From"] = email
        msg["To"] = params["gmail-user"]
        msg["Subject"] = "New message from learn2_cod " + name
        message = (
            message + "\n\n\n" + "Phone: " + phone + "\n" + "Email: " + email
        )
        print("messafe", msg)
        msg.attach(MIMEText(message))
        with SMTP("smtp.gmail.com", 587) as mail_server:
            # identify ourselves to smtp gmail client
            mail_server.ehlo()
            # secure our email with tls encryption
            mail_server.starttls()
            # re-identify ourselves as an encrypted connection
            mail_server.ehlo()
            mail_server.login(params["gmail-user"], params["gmail-password"])
            mail_server.sendmail(
                from_addr=email,
                to_addrs=params["gmail-user"],
                msg=msg.as_string(),
            )
            return redirect("/")

    return render_template("contact.html", params=params)


@app.route("/contact1", methods=["GET", "POST"])
def contact1():
    if request.method == "POST":

        """Add entry to DB"""
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        message = request.form.get("message")

        entry = Contacts(
            name=name,
            phone_num=phone,
            msg=message,
            date=d.today(),
            email=email,
        )
        if not name or not email or not phone or not message:
            flash('All fields are required, Please Try Again!')
            return redirect("/contact")
        db.session.add(entry)
        db.session.commit()
        msg = MIMEMultipart()
        msg["From"] = email
        msg["To"] = params["gmail-user"]
        msg["Subject"] = "New message from learn2_cod " + name
        message = (
            message + "\n\n\n" + "Phone: " + phone + "\n" + "Email: " + email
        )
        msg.attach(MIMEText(message))
        with SMTP("smtp.gmail.com", 587) as mail_server:
            # identify ourselves to smtp gmail client
            mail_server.ehlo()
            # secure our email with tls encryption
            mail_server.starttls()
            # re-identify ourselves as an encrypted connection
            mail_server.ehlo()
            mail_server.login(params["gmail-user"], params["gmail-password"])
            mail_server.sendmail(
                from_addr=email,
                to_addrs=params["gmail-user"],
                msg=msg.as_string(),
            )
            return redirect("/")
    return render_template("contact1.html", params=params)


@app.route("/signup")
def signup():
    return render_template("signup.html", params=params)


@app.route("/signup", methods=["POST"])
def signup_post():
    # '''Add entry to DB'''
    name = request.form.get("name")
    username = request.form.get("uname")
    email = request.form.get("email")
    password = request.form.get("pass")
    confirmpassword = request.form.get("cpass")

    email_exist = Registration.query.filter_by(email=email).first()
    username_exist = Registration.query.filter_by(username=username).first()

    if email_exist:
        flash(email_exist)
        flash(" Email already exists!")

    elif username_exist:
        flash("Username Already Taken !")
        flash("Try Different Username!")
    elif password != confirmpassword:
        flash("Password not same! ")
        flash("Try Again!")
    else:
        entry = Registration(
            name=name,
            username=username,
            pasword=generate_password_hash(password, method="sha256"),
            email=email,
        )
        db.session.add(entry)
        db.session.commit()
        flash("You are Succefully Registered!")
        return redirect("/login")
    return redirect("/signup")


@app.route("/logout")
def logout():
    if session["user"] == params["admin_user"]:
        session["user"] = False
    else:
        session["logged_in"] = False
    return redirect("/")


@app.route("/login")
def login():
    return render_template("login.html", params=params)


@app.route("/login", methods=["POST"])
def login_post():
    """Add entry to DB"""
    if request.method == "POST":
        session["username"] = request.form.get("uname")
        session["password"] = request.form.get("pass")
        user = Registration.query.filter_by(
            username=session["username"]
        ).first()
    print("User", user.__dict__)
    if not user:
        flash("Please check your login details and try again.")
        return redirect("/login")
    elif not check_password_hash(user.pasword, session["password"]):
        flash("Please check your login details and try again.")
        return redirect("/login")

    session["name"] = user.name
    session["email"] = user.email

    session["logged_in"] = True
    return redirect("/")

    # return render_template('login.html' , params = params)


@app.route("/profile/<string:name>")
def profile(name):
    return render_template("profile.html", params=params, name=name)


@app.route("/profile/<string:name>", methods=["POST"])
def profile_post(name):
    # '''Add entry to DB'''
    if request.method == "POST":
        # nam = request.form.get('name')
        email = request.form.get("email")
        img = request.form.get("img")
        email_exist = Registration.query.filter_by(email=email).first()

        if email_exist:
            flash(email_exist)
            flash(" Email already exists!")

        else:
            user = Registration.query.filter_by(
                username=session["username"]
            ).first()
            user.email = email
            session["email"] = email
            db.session.commit()
            flash("Succefully Updated!")
            return redirect("/")
        return redirect("/profile")


if __name__ == "__main__":
    app.run(debug=True)
    app.run()
