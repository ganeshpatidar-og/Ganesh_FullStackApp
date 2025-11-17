import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from config import Config
from models import db, AdminUser, Project, Client, ContactMessage, NewsletterSubscriber

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return AdminUser.query.get(int(user_id))

# ------- CLI COMMANDS -------

@app.cli.command("create-db")
def create_db():
    with app.app_context():
        db.create_all()
        print("Database tables created.")

@app.cli.command("create-admin")
def create_admin():
    """Create default admin: username=admin, password=admin123"""
    with app.app_context():
        if AdminUser.query.filter_by(username="admin").first():
            print("Admin already exists.")
            return
        pw_hash = bcrypt.generate_password_hash("admin123").decode("utf-8")
        admin = AdminUser(username="admin", password_hash=pw_hash)
        db.session.add(admin)
        db.session.commit()
        print("Admin created: admin / admin123")

# ------- PUBLIC ROUTES -------

@app.route("/")
def index():
    projects = Project.query.all()
    clients = Client.query.all()
    return render_template("index.html", projects=projects, clients=clients)

@app.route("/projects")
def public_projects():
    projects = Project.query.all()
    return render_template("projects.html", projects=projects)

@app.route("/clients")
def public_clients():
    clients = Client.query.all()
    return render_template("clients.html", clients=clients)

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        mobile = request.form.get("mobile")
        city = request.form.get("city")

        msg = ContactMessage(
            full_name=full_name,
            email=email,
            mobile=mobile,
            city=city
        )
        db.session.add(msg)
        db.session.commit()
        flash("Thank you! We will contact you soon.")
        return redirect(url_for("contact"))

    return render_template("contact.html")

@app.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email")
    if email and not NewsletterSubscriber.query.filter_by(email=email).first():
        sub = NewsletterSubscriber(email=email)
        db.session.add(sub)
        db.session.commit()
        flash("Subscribed successfully!")
    else:
        flash("You are already subscribed or email is invalid.")
    return redirect(url_for("index"))

# ------- AUTH -------

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = AdminUser.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("admin_dashboard"))
        flash("Invalid credentials")
    return render_template("login.html")

@app.route("/admin/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ------- ADMIN PANEL -------

@app.route("/admin")
@login_required
def admin_dashboard():
    project_count = Project.query.count()
    client_count = Client.query.count()
    contact_count = ContactMessage.query.count()
    sub_count = NewsletterSubscriber.query.count()
    return render_template(
        "admin_dashboard.html",
        project_count=project_count,
        client_count=client_count,
        contact_count=contact_count,
        sub_count=sub_count
    )

# --- Helper for image saving ---

def save_image(file):
    if not file or not file.filename:
        return None
    filename = file.filename
    upload_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    file.save(upload_path)
    return filename

# --- Projects CRUD ---

@app.route("/admin/projects")
@login_required
def admin_projects():
    projects = Project.query.all()
    return render_template("admin_projects.html", projects=projects)

@app.route("/admin/projects/new", methods=["GET", "POST"])
@login_required
def admin_projects_new():
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        image_file = request.files.get("image")
        img_name = save_image(image_file) if image_file and image_file.filename else None

        proj = Project(name=name, description=description, image=img_name)
        db.session.add(proj)
        db.session.commit()
        flash("Project created.")
        return redirect(url_for("admin_projects"))

    return render_template("admin_project_form.html", project=None)

@app.route("/admin/projects/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def admin_projects_edit(project_id):
    project = Project.query.get_or_404(project_id)
    if request.method == "POST":
        project.name = request.form.get("name")
        project.description = request.form.get("description")
        image_file = request.files.get("image")
        if image_file and image_file.filename:
            img_name = save_image(image_file)
            project.image = img_name
        db.session.commit()
        flash("Project updated.")
        return redirect(url_for("admin_projects"))
    return render_template("admin_project_form.html", project=project)

@app.route("/admin/projects/<int:project_id>/delete")
@login_required
def admin_projects_delete(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    flash("Project deleted.")
    return redirect(url_for("admin_projects"))

# --- Clients CRUD ---

@app.route("/admin/clients")
@login_required
def admin_clients():
    clients = Client.query.all()
    return render_template("admin_clients.html", clients=clients)

@app.route("/admin/clients/new", methods=["GET", "POST"])
@login_required
def admin_clients_new():
    if request.method == "POST":
        name = request.form.get("name")
        designation = request.form.get("designation")
        description = request.form.get("description")
        image_file = request.files.get("image")
        img_name = save_image(image_file) if image_file and image_file.filename else None

        client = Client(
            name=name,
            designation=designation,
            description=description,
            image=img_name
        )
        db.session.add(client)
        db.session.commit()
        flash("Client created.")
        return redirect(url_for("admin_clients"))

    # 👇 pass form_action explicitly
    return render_template(
        "admin_client_form.html",
        client=None,
        form_action=url_for("admin_clients_new")
    )


@app.route("/admin/clients/<int:client_id>/edit", methods=["GET", "POST"])
@login_required
def admin_clients_edit(client_id):
    client = Client.query.get_or_404(client_id)
    if request.method == "POST":
        client.name = request.form.get("name")
        client.designation = request.form.get("designation")
        client.description = request.form.get("description")
        image_file = request.files.get("image")
        if image_file and image_file.filename:
            img_name = save_image(image_file)
            client.image = img_name
        db.session.commit()
        flash("Client updated.")
        return redirect(url_for("admin_clients"))

    return render_template(
        "admin_client_form.html",
        client=client,
        form_action=url_for("admin_clients_edit", client_id=client.id)
    )

@app.route("/admin/clients/<int:client_id>/delete")
@login_required
def admin_clients_delete(client_id):
    client = Client.query.get_or_404(client_id)
    db.session.delete(client)
    db.session.commit()
    flash("Client deleted.")
    return redirect(url_for("admin_clients"))

# --- Contacts & Subscribers (read-only) ---

@app.route("/admin/contacts")
@login_required
def admin_contacts():
    contacts = ContactMessage.query.all()
    return render_template("admin_contacts.html", contacts=contacts)

@app.route("/admin/subscribers")
@login_required
def admin_subscribers():
    subs = NewsletterSubscriber.query.all()
    return render_template("admin_subscribers.html", subscribers=subs)

if __name__ == "__main__":
    app.run(debug=True)
