from flask import Flask,render_template,redirect,url_for,flash,request,session,logging
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:  
            return f(*args, **kwargs)
        else:   
            flash("Bu sayfayı görüntülemek için önce giriş yapmalısın.","danger")
            return redirect(url_for("login"))
    return decorated_function

def logout_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:  
            flash("Bu sayfayı görüntülemek için önce çıkış yapmalısın.","danger")
            return redirect(url_for("index"))
        else:   
            return f(*args, **kwargs)
    return decorated_function

class RegisterForm(Form):   
    name=StringField("Ad Soyad  ",validators=[validators.Length(min=4,max=25,message="4-25 Arası karakter sınırlaması."),validators.DataRequired(message="Bu alan boş bırakılamaz.")])
    email=StringField("E-Mail  ",validators=[validators.Email(message="Geçersiz e-mail adresi."),validators.DataRequired(message="Bu alan boş bırakılamaz.")])
    username=StringField("Kullanıcı Ad  ",validators=[validators.length(min=4,max=25,message="4-25 Arası karakter sınırlaması."),validators.DataRequired(message="Bu alan boş bırakılamaz.")])
    password=PasswordField("Parola  ",validators=[validators.EqualTo(fieldname="confirm",message="Parolalar birbiriyle uyuşmuyor."),validators.Length(min=4,max=25,message="4-25 Arası karakter sınırlaması."),validators.DataRequired(message="Bu alan boş bırakılamaz.")])
    confirm=PasswordField("Parola Onay  ")

class LoginForm(Form):  
    username=StringField("Kullanıcı Ad")
    password=PasswordField("Parola")

class ArticleForm(Form):    
    title=StringField("Makale Başlığı  ",validators=[validators.Length(min=5,max=100,message="5-100 Arası karakter sınırlaması."),validators.DataRequired(message="Bu alan boş bırakılamaz.")])
    content=TextAreaField("Makale İçeriği  ",validators=[validators.Length(min=10,message="En az 10 karakter girebilirsiniz."),validators.DataRequired(message="Bu alan boş bırakılamaz.")])

app=Flask(__name__)

app.secret_key="yblog"

app.config["MYSQL_HOST"]="localhost"
app.config["MYSQL_USER"]="root"
app.config["MYSQL_PASSWORD"]=""
app.config["MYSQL_DB"]="ybblog"
app.config["MYSQL_CURSORCLASS"]="DictCursor"

mysql=MySQL(app)

@app.route("/")
def index():    
    return render_template("index.html")

@app.route("/about")
def about():    
    return render_template("about.html")

@app.route("/register",methods=["GET","POST"])
@logout_required
def register(): 
    form=RegisterForm(request.form)

    if request.method=="POST" and form.validate():  
        name=form.name.data
        email=form.email.data
        username=form.username.data
        password=sha256_crypt.encrypt(form.password.data)

        cursor=mysql.connection.cursor()
        sorgu="INSERT INTO users(name,email,username,password) VALUES(%s,%s,%s,%s)"
        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit()
        cursor.close()

        flash("Başarıyla kayıt olundu.","success")

        return redirect(url_for("login"))
    else:   
        return render_template("register.html",form=form)

@app.route("/login",methods=["GET","POST"])
@logout_required
def login():    
    form=LoginForm(request.form)

    if request.method=="POST":  
        username=form.username.data
        password_entered=form.password.data

        cursor=mysql.connection.cursor()
        sorgu="SELECT * FROM users WHERE username=%s"
        result=cursor.execute(sorgu,(username,))

        if result>0:    
            data=cursor.fetchone()
            real_password=data["password"]
            if sha256_crypt.verify(password_entered,real_password): 
                flash("Hoşgeldiniz {}".format(data["username"]),"success")

                session["logged_in"]=True
                session["username"]=username

                return redirect(url_for("index"))
            else:   
                flash("Girdiğiniz parola hatalı.","danger")
                return redirect(url_for("login"))
        else:   
            flash("Böyle bir kullanıcı bulunmamaktadır.","danger")
            return redirect(url_for("login"))
    else:   
        return render_template("login.html",form=form)

@app.route("/logout")
def logout():   
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():   
    cursor=mysql.connection.cursor()
    sorgu="SELECT * FROM articles WHERE author=%s"
    result=cursor.execute(sorgu,(session["username"],)) 

    if result>0:    
        articles=cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:   
        return render_template("dashboard.html")

@app.route("/addarticle",methods=["POST","GET"])
@login_required
def addarticle():   
    form=ArticleForm(request.form)

    if request.method=="POST" and form.validate():
        title=form.title.data
        content=form.content.data

        cursor=mysql.connection.cursor()
        sorgu="INSERT INTO articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()

        flash("Makale başarılı bir şekilde eklendi.","success")

        return redirect(url_for("dashboard"))
    else:   
        return render_template("addarticle.html",form=form)

@app.route("/articles")
def articles():
    cursor=mysql.connection.cursor()
    sorgu="SELECT * FROM articles"
    result=cursor.execute(sorgu) 

    if result>0:    
        articles=cursor.fetchall()
        return render_template("articles.html",articles=articles)
    else:   
        flash("Bu blogta henüz makale bulunmamaktadır.","info")
        return render_template("articles.html")

@app.route("/article/<string:id>")
def article(id):    
    cursor=mysql.connection.cursor()
    sorgu="SELECT * FROM articles WHERE id=%s"
    result=cursor.execute(sorgu,(id,))

    if result>0:    
        article=cursor.fetchone()
        return render_template("article.html",article=article)
    else:   
        flash("Bu makaleye ulaşılamıyor.","dark")
        return render_template("article.html")

@app.route("/delete/<string:id>")
@login_required
def delete(id): 
    cursor=mysql.connection.cursor()
    sorgu="SELECT * FROM articles WHERE author=%s and id=%s"
    result=cursor.execute(sorgu,(session["username"],id))

    if result>0:
        sorgu2="DELETE FROM articles  WHERE id=%s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()

        flash("Makale silindi.","success")

        return redirect(url_for("dashboard"))
    else:   
        flash("Böyle bir makale yok ya da boyle bir makaleye erişme yetkiniz yok.","danger")
        return redirect(url_for("dashboard"))

@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required
def edit(id):      
    if request.method=="POST":  
        form=ArticleForm(request.form)

        newtitle=form.title.data
        newcontent=form.content.data

        cursor=mysql.connection.cursor()
        sorgu2="UPDATE articles SET title=%s,content=%s WHERE id=%s"
        cursor.execute(sorgu2,(newtitle,newcontent,id))
        mysql.connection.commit()

        flash("Makale güncelleme başarılı.","success")

        return redirect(url_for("dashboard"))

    else:   
        cursor=mysql.connection.cursor()
        sorgu="SELECT * FROM articles WHERE author=%s and id=%s"
        result=cursor.execute(sorgu,(session["username"],id))

        if result>0:    
            article=cursor.fetchone()

            form=ArticleForm()

            form.title.data=article["title"]
            form.content.data=article["content"]

            return render_template("edit.html",form=form)
        else:   
            flash("Böyle bir makale yok ya da boyle bir makaleye erişme yetkiniz yok.","danger")
            return redirect(url_for("dashboard"))

@app.route("/search",methods=["GET","POST"])
def search():   
    if request.method=="POST":  
        keyword=request.form.get("keyword")
        
        cursor=mysql.connection.cursor()
        sorgu='SELECT * FROM articles WHERE title LIKE "%%{}%%"'.format(keyword)
        result=cursor.execute(sorgu)

        if(result>0):   
            articles=cursor.fetchall()
            return render_template("articles.html",articles=articles)
        else:   
            flash("Aradığınız makale bulunamadı.","info")
            return redirect(url_for("articles"))
    else:   
        return redirect(url_for("articles"))

if __name__=="__main__": 
    app.run(debug=True)