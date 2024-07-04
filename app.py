from flask import Flask, render_template, redirect, url_for, request, flash, jsonify , session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime , timedelta
import os
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from datetime import date
import requests
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crmdigifalx.db'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'digifalx.head@gmail.com'
app.config['MAIL_PASSWORD'] = 'gggu ujvb teok zgnw'
app.config['MAIL_DEFAULT_SENDER'] = 'digifalx.head@gmail.com'
UPLOAD_FOLDER = 'static/profile_pics'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    contact_no = db.Column(db.String(15), nullable=True)
    profile_pic = db.Column(db.String(20), nullable=True, default='default.jpg')
    joining_date = db.Column(db.DateTime, nullable=False)
    position = db.Column(db.String(100), nullable=True)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    priority = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='backlog')
    assignees = db.relationship('User', secondary='task_assignees', backref='tasks')
    observers = db.relationship('User', secondary='task_observers', backref='observed_tasks')
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    creator = db.relationship('User', backref='created_tasks', foreign_keys=[creator_id])

task_assignees = db.Table('task_assignees',
    db.Column('task_id', db.Integer, db.ForeignKey('task.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

task_observers = db.Table('task_observers',
    db.Column('task_id', db.Integer, db.ForeignKey('task.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    start_time = db.Column(db.String(50), nullable=False)
    end_time = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    attendees = db.Column(db.String(1000), nullable=False)  

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'start': self.start_time,
            'end': self.end_time,
            'description': self.description,
            'attendees': self.attendees.split(','),  # Assuming attendees are stored as a comma-separated string
            'url': url_for('view_meeting', meeting_id=self.id)  # Add this line
        }

class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='pending')
    user = db.relationship('User', backref='leaves')

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client = db.Column(db.String(150), nullable=False)
    phone_no = db.Column(db.String(20), nullable=False)
    linkedin = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    website = db.Column(db.String(150), nullable=True)
    requirements = db.Column(db.Text, nullable=True)
    platform = db.Column(db.String(50), nullable=True)
    first_call = db.Column(db.Date, nullable=True)
    follow_up = db.Column(db.Date, nullable=True)
    details = db.Column(db.Text, nullable=True)


class WorkSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    clock_in = db.Column(db.DateTime, nullable=False)
    clock_out = db.Column(db.DateTime)
    clock_in_location = db.Column(db.String(100))
    clock_out_location = db.Column(db.String(100))
    total_hours = db.Column(db.Float, default=0.0)
    locations = db.relationship('Location', backref='session', lazy=True)
    breaks = db.relationship('Break', backref='session', lazy=True)

class Break(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('work_session.id'), nullable=False)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime)

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('work_session.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(255))



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_profile_picture(form_picture):
    filename = secure_filename(form_picture.filename)
    form_picture.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return filename


def send_task_notification(task, recipients):
    from flask_mail import Message
    from app import mail

    for user in recipients:
        msg = Message(
            subject="New Task Assigned",
            recipients=[user.email],
            body=f"""
                You have been assigned a new task:
                Title: {task.title}
                Description: {task.description}
                Start Date: {task.start_date}
                End Date: {task.end_date}
                Priority: {task.priority}
                Assigned by: {task.creator.username}
            """,
            sender="no-reply@yourapp.com"
        )
        mail.send(msg)


def send_updatedtask_notification(task, recipients):
    from flask_mail import Message
    from app import mail

    for user in recipients:
        msg = Message(
            subject="Task Updated",
            recipients=[user.email],
            body=f"""
                Task has been updated:
                Title: {task.title}
                Description: {task.description}
                Start Date: {task.start_date}
                End Date: {task.end_date}
                Priority: {task.priority}
                Assigned by: {task.creator.username}
            """,
            sender="no-reply@yourapp.com"
        )
        mail.send(msg)

def lead_email(subject, recipients, body):
    

    msg = Message(
        subject=subject,
        recipients=recipients,
        body=body,
        sender="no-reply@yourapp.com"
    )
    mail.send(msg)



##################################################AUTH#################################################
#######################################################################################################
#######################################################################################################

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')


    return render_template('login.html')

@app.route('/register_superadmin', methods=['GET', 'POST'])
def register_superadmin():
    # Check if the number of superadmins is less than 10
    if User.query.filter_by(role='superadmin').count() >= 10:
        flash('The limit of 10 superadmins has been reached.', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        joining_date = datetime.strptime(request.form['joining_date'], '%Y-%m-%d')

        if 'profile_pic' in request.files and allowed_file(request.files['profile_pic'].filename):
            profile_pic = save_profile_picture(request.files['profile_pic'])
        else:
            profile_pic = 'default.jpg'

        superadmin = User(username=username, email=email, password=password, role='superadmin', joining_date=joining_date, profile_pic=profile_pic)
        db.session.add(superadmin)
        db.session.commit()
        flash('Superadmin registered successfully', 'success')
        return redirect(url_for('login'))
    
    return render_template('register_superadmin.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'employee':
        return redirect(url_for('employee_dashboard'))
    elif current_user.role == 'superadmin':
        
        return redirect(url_for('superadmin_dashboard'))
    return 'Invalid role'




#####################################################SUPERADMIN######################################
#####################################################################################################
#####################################################################################################

@app.route('/superadmin_dashboard')
@login_required
def superadmin_dashboard():
    if current_user.role != 'superadmin':
        return redirect(url_for('dashboard'))
    tasks = Task.query.all()
    users = User.query.all()  # Query for users
    task_count_total = Task.query.count()
    user_count_total = User.query.count()
    
    today = date.today().strftime('%Y-%m-%d')
    meetings_today = Meeting.query.filter(Meeting.start_time.like(f"{today}%")).all()
    
    return render_template(
        'superadmin_dashboard.html', 
        tasks=tasks, 
        users=users,
        user=current_user,
        task_count_total=task_count_total,
        user_count_total=user_count_total,
        meetings_today=meetings_today
    )




@app.route('/tasks')
@login_required
def tasks():
    if current_user.role not in [ 'superadmin']:
        return redirect(url_for('dashboard'))
    tasks = Task.query.all()
      # Query for users
    
    return render_template('tasks.html', tasks=tasks, user=current_user)


@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form['description']
        task.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        task.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        task.priority = request.form['priority']
        task.assignees = [User.query.get(int(id)) for id in request.form.getlist('assignees')]
        task.observers = [User.query.get(int(id)) for id in request.form.getlist('observers')]
        db.session.commit()

        # Send email notification to observers
        send_updatedtask_notification(task, task.observers)
        flash('Task updated successfully', 'success')
        return redirect(url_for('dashboard'))
    
    employees = User.query.all()
    admins = User.query.all()
    return render_template('edit_task.html', task=task, employees=employees, admins=admins)

@app.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    if current_user.role in ['admin', 'superadmin', 'employee']:
        employees = User.query.all()
        admins = User.query.all()
        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%dT%H:%M')
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%dT%H:%M')
            priority = request.form['priority']
            assignees_ids = request.form.getlist('assignees')
            observers_ids = request.form.getlist('observers')

            assignees = [User.query.get(int(id)) for id in assignees_ids]
            observers = [User.query.get(int(id)) for id in observers_ids]

            new_task = Task(
                title=title, 
                description=description, 
                start_date=start_date, 
                end_date=end_date, 
                priority=priority,
                assignees=assignees,
                observers=observers,
                creator_id=current_user.id  # Set the creator_id to the currently logged-in user's id
            )
            db.session.add(new_task)
            db.session.commit()

            recipients = assignees + observers
            send_task_notification(new_task, recipients)

            flash('Task added successfully and notifications sent', 'success')
            return redirect(url_for('dashboard'))

        return render_template('add_task.html', employees=employees, admins=admins)
    
    flash('Access Denied', 'danger')
    return redirect(url_for('dashboard'))



@app.route('/delete_task/<int:task_id>')
@login_required
def delete_task(task_id):
    if current_user.role != 'superadmin':
        return redirect(url_for('dashboard'))
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully', 'success')
    return redirect(url_for('superadmin_dashboard'))


@app.route('/super_userlist')
@login_required
def super_userlist():
    if current_user.role != 'superadmin':
        return redirect(url_for('dashboard'))
    
    users = User.query.all()  # Query for users
    return render_template('super_userlist.html', users=users, user=current_user)



@app.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role != 'superadmin':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        joining_date = datetime.strptime(request.form['joining_date'], '%Y-%m-%d')

        if 'profile_pic' in request.files and allowed_file(request.files['profile_pic'].filename):
            profile_pic = save_profile_picture(request.files['profile_pic'])
        else:
            profile_pic = 'default.jpg'

        new_user = User(username=username, email=email, password=password, role=role, joining_date=joining_date, profile_pic=profile_pic)
        db.session.add(new_user)
        db.session.commit()
        flash('User added successfully', 'success')
        return redirect(url_for('superadmin_dashboard'))
    return render_template('add_user.html')



@app.route('/employee/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    employee = User.query.get_or_404(employee_id)
    if current_user.role != 'superadmin':
        flash('You do not have permission to perform this action', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Update all fields
        employee.username = request.form['username']
        employee.email = request.form['email']
        employee.address = request.form['address']
        employee.contact_no = request.form['contact_no']
        employee.position = request.form['position']
        employee.role = request.form['role']  # Update the role field
        db.session.commit()
        flash('Employee details updated successfully', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_employee.html', employee=employee)




################################################ADMIN#######################################
############################################################################################
############################################################################################

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    tasks = Task.query.all()
    users = User.query.all()  # Query for users
    task_count_total = Task.query.count()
    user_count_total = User.query.count()
    
    today = date.today().strftime('%Y-%m-%d')
    meetings_today = Meeting.query.filter(Meeting.start_time.like(f"{today}%")).all()
    
    return render_template(
        'admin_dashboard.html', 
        tasks=tasks, 
        users=users,
        user=current_user,
        task_count_total=task_count_total,
        user_count_total=user_count_total,
        meetings_today=meetings_today
    )

@app.route('/admin_tasks')
@login_required
def admin_tasks():
    if current_user.role not in [ 'admin']:
        return redirect(url_for('dashboard'))
    tasks = Task.query.all()
      # Query for users
    
    return render_template('admin_tasks.html', tasks=tasks, user=current_user)

@app.route('/admin_userlist')
@login_required
def admin_userlist():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    users = User.query.all()  # Query for users
    return render_template('admin_userlist.html', users=users, user=current_user)


@app.route('/admin_add_user', methods=['GET', 'POST'])
@login_required
def admin_add_user():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        joining_date = datetime.strptime(request.form['joining_date'], '%Y-%m-%d')

        if 'profile_pic' in request.files and allowed_file(request.files['profile_pic'].filename):
            profile_pic = save_profile_picture(request.files['profile_pic'])
        else:
            profile_pic = 'default.jpg'

        new_user = User(username=username, email=email, password=password,  joining_date=joining_date, profile_pic=profile_pic)
        db.session.add(new_user)
        db.session.commit()
        flash('User added successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_add_user.html')

@app.route('/admin_edit_employee/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_employee(employee_id):
    employee = User.query.get_or_404(employee_id)
    if current_user.role != 'admin':
        flash('You do not have permission to perform this action', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        employee.username = request.form['username']
        employee.email = request.form['email']
        employee.address = request.form['address']
        employee.contact_no = request.form['contact_no']
        employee.position = request.form['position']
        db.session.commit()
        flash('Employee details updated successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin_edit_employee.html', employee=employee)


@app.route('/admin_add_task', methods=['GET', 'POST'])
@login_required
def admin_add_task():
    if current_user.role in ['admin']:
        employees = User.query.all()
        admins = User.query.all()
        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%dT%H:%M')
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%dT%H:%M')
            priority = request.form['priority']
            assignees_ids = request.form.getlist('assignees')
            observers_ids = request.form.getlist('observers')

            assignees = [User.query.get(int(id)) for id in assignees_ids]
            observers = [User.query.get(int(id)) for id in observers_ids]

            new_task = Task(
                title=title, 
                description=description, 
                start_date=start_date, 
                end_date=end_date, 
                priority=priority,
                assignees=assignees,
                observers=observers
            )
            db.session.add(new_task)
            db.session.commit()

            recipients = assignees + observers
            send_task_notification(new_task, recipients)

            flash('Task added successfully and notifications sent', 'success')
            return redirect(url_for('dashboard'))

        return render_template('admin_add_task.html', employees=employees, admins=admins)
    
    flash('Access Denied', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/admin_edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form['description']
        task.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        task.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        task.priority = request.form['priority']
        task.assignees = [User.query.get(int(id)) for id in request.form.getlist('assignees')]
        task.observers = [User.query.get(int(id)) for id in request.form.getlist('observers')]
        db.session.commit()

        # Send email notification to assignees
        send_updatedtask_notification(task, task.observers)
        flash('Task updated successfully', 'success')
        return redirect(url_for('dashboard'))
    employees = User.query.all()
    admins = User.query.all()
    return render_template('admin_edit_task.html', task=task, employees=employees, admins=admins)


#######################################EMPLOYEE########################################################
#######################################################################################################
#######################################################################################################



@app.route('/employee_dashboard')
@login_required
def employee_dashboard():
    if current_user.role != 'employee':
        return redirect(url_for('dashboard'))

    tasks = Task.query.all()
    users = User.query.all()  # Query for users
    task_count_total = Task.query.count()
    user_count_total = User.query.count()
    
    today = date.today().strftime('%Y-%m-%d')
    meetings_today = Meeting.query.filter(Meeting.start_time.like(f"{today}%")).all()
    
    return render_template(
        'employee_dashboard.html', 
        tasks=tasks, 
        users=users,
        user=current_user,
        task_count_total=task_count_total,
        user_count_total=user_count_total,
        meetings_today=meetings_today
    )
@app.route('/emp_tasks')
@login_required
def emp_tasks():
    if current_user.role not in [ 'employee']:
        return redirect(url_for('dashboard'))
    tasks = Task.query.all()
      # Query for users
    
    return render_template('emp_tasks.html', tasks=tasks, user=current_user)

@app.route('/emp_userlist')
@login_required
def emp_userlist():
    if current_user.role != 'employee':
        return redirect(url_for('dashboard'))
    
    users = User.query.all()  # Query for users
    return render_template('emp_userlist.html', users=users, user=current_user)



@app.route('/emp_add_task', methods=['GET', 'POST'])
@login_required
def emp_add_task():
    if current_user.role in ['employee']:
        employees = User.query.filter_by(role='employee').all()
        admins = User.query.filter_by(role='admin').all()
        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%dT%H:%M')
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%dT%H:%M')
            priority = request.form['priority']
            assignees_ids = request.form.getlist('assignees')
            observers_ids = request.form.getlist('observers')

            assignees = [User.query.get(int(id)) for id in assignees_ids]
            observers = [User.query.get(int(id)) for id in observers_ids]

            new_task = Task(
                title=title, 
                description=description, 
                start_date=start_date, 
                end_date=end_date, 
                priority=priority,
                assignees=assignees,
                observers=observers
            )
            db.session.add(new_task)
            db.session.commit()

            recipients = assignees + observers
            send_task_notification(new_task, recipients)

            flash('Task added successfully and notifications sent', 'success')
            return redirect(url_for('dashboard'))

        return render_template('admin_add_task.html', employees=employees, admins=admins)
    
    flash('Access Denied', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/emp_edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def emp_edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form['description']
        task.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        task.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        task.priority = request.form['priority']
        task.assignees = [User.query.get(int(id)) for id in request.form.getlist('assignees')]
        task.observers = [User.query.get(int(id)) for id in request.form.getlist('observers')]
        db.session.commit()

        # Send email notification to assignees
        send_updatedtask_notification(task, task.observers)
        
        flash('Task updated successfully', 'success')
        return redirect(url_for('dashboard'))
    employees = User.query.filter_by(role='employee').all()
    admins = User.query.filter_by(role='admin').all()
    return render_template('emp_edit_task.html', task=task, employees=employees, admins=admins)


#######################################################KANBAN############################################
#########################################################################################################
#########################################################################################################

@app.route('/kanban_board')
def kanban_board():
    backlog_tasks = Task.query.filter_by(status='backlog').all()
    in_progress_tasks = Task.query.filter_by(status='in_progress').all()
    completed_tasks = Task.query.filter_by(status='completed').all()
    return render_template('kanban_board.html', backlog_tasks=backlog_tasks, in_progress_tasks=in_progress_tasks, completed_tasks=completed_tasks)



@app.route('/update_task_status', methods=['POST'])
def update_task_status():
    data = request.get_json()
    task_id = data.get('taskId')
    new_status = data.get('newStatus')
    
    task = Task.query.get(task_id)
    if task:
        task.status = new_status
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

##############################################################profile########################################
#############################################################################################################
#############################################################################################################
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if 'username' in request.form:
            current_user.username = request.form['username']
        if 'email' in request.form:
            current_user.email = request.form['email']
        if 'address' in request.form:
            current_user.address = request.form['address']
        if 'contact_no' in request.form:
            current_user.contact_no = request.form['contact_no']
        if 'position' in request.form:
            current_user.position = request.form['position']

        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file.filename != '':
                filename = current_user.username + "_" + file.filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                current_user.profile_pic = filename
        
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=current_user)


#######################################################common views####################################
#######################################################################################################
#######################################################################################################

@app.route('/view_task/<int:task_id>')
@login_required
def view_task(task_id):
    task = Task.query.get_or_404(task_id)
    return render_template('view_task.html', task=task)

@app.route('/employee/<int:employee_id>')
@login_required
def view_employee(employee_id):
    employee = User.query.get_or_404(employee_id)
    return render_template('view_employee.html', employee=employee)


##############################################LEADS###############################################
##################################################################################################
##################################################################################################

@app.route('/leads')
@login_required
def leads():
    leads = Lead.query.all()
    return render_template('leads.html', leads=leads)

@app.route('/add_lead', methods=['GET', 'POST'])
@login_required
def add_lead():
    if request.method == 'POST':
        try:
            first_call_str = request.form.get('first_call')
            follow_up_str = request.form.get('follow_up')

            first_call_date = datetime.strptime(first_call_str, '%Y-%m-%d').date() if first_call_str else None
            follow_up_date = datetime.strptime(follow_up_str, '%Y-%m-%d').date() if follow_up_str else None

            new_lead = Lead(
                client=request.form['client'],
                phone_no=request.form['phone_no'],
                linkedin=request.form.get('linkedin'),
                email=request.form.get('email'),
                website=request.form.get('website'),
                requirements=request.form.get('requirements'),
                platform=request.form.get('platform'),
                first_call=first_call_date,
                follow_up=follow_up_date,
                details=request.form.get('details')
            )
            db.session.add(new_lead)
            db.session.commit()

            # Send email to all users
            users = User.query.all()
            recipients = [user.email for user in users]
            email_body = f"New lead added:\nClient: {new_lead.client}\nPhone: {new_lead.phone_no}\nEmail: {new_lead.email}\nDetails: {new_lead.details}"
            lead_email(subject="New Lead Added", recipients=recipients, body=email_body)

            flash('Lead added successfully!')
            return redirect(url_for('leads'))
        except Exception as e:
            flash(f'Error adding lead: {str(e)}')
    
    return render_template('add_lead.html')

@app.route('/edit_lead/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_lead(id):
    lead = Lead.query.get_or_404(id)
    if request.method == 'POST':
        try:
            # Convert date strings to date objects
            first_call_date = datetime.strptime(request.form.get('first_call'), '%Y-%m-%d').date()
            follow_up_date = datetime.strptime(request.form.get('follow_up'), '%Y-%m-%d').date()
            
            lead.client = request.form['client']
            lead.phone_no = request.form['phone_no']
            lead.linkedin = request.form.get('linkedin')
            lead.email = request.form.get('email')
            lead.website = request.form.get('website')
            lead.requirements = request.form.get('requirements')
            lead.platform = request.form.get('platform')
            lead.first_call = first_call_date
            lead.follow_up = follow_up_date
            lead.details = request.form.get('details')
            db.session.commit()

            # Send email to admin and superadmin users
            admins = User.query.filter(User.role.in_(['admin', 'superadmin'])).all()
            recipients = [user.email for user in admins]
            email_body = f"Lead updated:\nClient: {lead.client}\nPhone: {lead.phone_no}\nEmail: {lead.email}\nDetails: {lead.details}"
            lead_email(subject="Lead Updated", recipients=recipients, body=email_body)

            flash('Lead updated successfully!')
            return redirect(url_for('leads'))
        except Exception as e:
            flash(f'Error updating lead: {str(e)}')
    return render_template('add_lead.html', lead=lead)

@app.route('/delete_lead/<int:id>')
@login_required
def delete_lead(id):
    if current_user.role != 'superadmin':
        flash('You do not have permission to delete leads.')
        return redirect(url_for('dashboard'))
    lead = Lead.query.get_or_404(id)
    db.session.delete(lead)
    db.session.commit()
    flash('Lead deleted successfully!')
    return redirect(url_for('leads'))

@app.route('/lead/<int:id>', methods=['GET'])
@login_required
def view_lead(id):
    lead = Lead.query.get_or_404(id)
    return render_template('view_lead.html', lead=lead)

#################################################attendance########################################
###################################################################################################
###################################################################################################

def get_address(latitude, longitude):
    try:
        response = requests.get(f'https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}', headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()  # Raises an HTTPError for bad responses
        data = response.json()
        return data.get('display_name', 'Unknown location')
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching address for {latitude}, {longitude}: {e}")
        return 'Unknown location'
def calculate_total_hours(session):
    if not session.clock_out:
        return 0.0
    total_time = session.clock_out - session.clock_in
    break_time = timedelta(0)
    for br in session.breaks:
        if br.end:
            break_time += br.end - br.start
    worked_time = total_time - break_time
    return round(worked_time.total_seconds() / 3600, 2)


@app.route('/attendance')
def attendance():
    if current_user.is_authenticated:
        current_time = datetime.now().strftime("%H:%M:%S")
        return render_template('attendance.html', user=current_user, current_time=current_time)
    return redirect(url_for('attendance'))

@app.route('/clockin', methods=['POST'])
@login_required
def clockin():
    user_id = current_user.id
    latitude, longitude = map(float, request.form['location'].split(','))
    address = get_address(latitude, longitude)
    work_session = WorkSession(user_id=user_id, clock_in=datetime.now(), clock_in_location=address)
    db.session.add(work_session)
    db.session.commit()
    session['session_id'] = work_session.id  # Store session ID in the user's session
    return redirect(url_for('attendance'))

@app.route('/clockout', methods=['POST'])
@login_required
def clockout():
    session_id = session.pop('session_id', None)  # Get session ID from user's session
    if not session_id:
        return 'No active session'
    latitude, longitude = map(float, request.form['location'].split(','))
    address = get_address(latitude, longitude)
    work_session = WorkSession.query.get(session_id)
    if work_session:
        work_session.clock_out = datetime.now()
        work_session.clock_out_location = address
        work_session.total_hours = calculate_total_hours(work_session)
        db.session.commit()
    return redirect(url_for('attendance'))

@app.route('/break/start', methods=['POST'])
@login_required
def start_break():
    session_id = session.get('session_id')
    if not session_id:
        return 'No active session'
    work_break = Break(session_id=session_id, start=datetime.now())
    db.session.add(work_break)
    db.session.commit()
    session['break_id'] = work_break.id  # Store break ID in the user's session
    return redirect(url_for('attendance'))

@app.route('/break/end', methods=['POST'])
@login_required
def end_break():
    break_id = session.pop('break_id', None)  # Get break ID from user's session
    if not break_id:
        return 'No active break'
    work_break = Break.query.get(break_id)
    if work_break:
        work_break.end = datetime.now()
        db.session.commit()
    return redirect(url_for('attendance'))

@app.route('/update_location', methods=['POST'])
@login_required
def update_location():
    session_id = session.get('session_id')
    if not session_id:
        return 'No active session'
    latitude, longitude = map(float, request.form['location'].split(','))
    address = get_address(latitude, longitude)
    location = Location(session_id=session_id, timestamp=datetime.now(), latitude=latitude, longitude=longitude, address=address)
    db.session.add(location)
    db.session.commit()
    return 'Location updated'

@app.route('/sessions/<int:user_id>')
@login_required
def get_sessions(user_id):
    sessions = WorkSession.query.filter_by(user_id=user_id).all()
    return jsonify([{
        'id': session.id,
        'clock_in': session.clock_in,
        'clock_out': session.clock_out,
        'clock_in_location': session.clock_in_location,
        'clock_out_location': session.clock_out_location,
        'total_hours': session.total_hours,
        'breaks': [{'start': br.start, 'end': br.end} for br in session.breaks],
        'locations': [{'timestamp': loc.timestamp, 'latitude': loc.latitude, 'longitude': loc.longitude, 'address': loc.address} for loc in session.locations]
    } for session in sessions])

@app.route('/total_hours/<int:user_id>')
@login_required
def total_hours(user_id):
    sessions = WorkSession.query.filter_by(user_id=user_id).all()
    total_hours = sum(calculate_total_hours(session) for session in sessions)
    return jsonify({'total_hours': round(total_hours, 2)})



@app.route('/emp_attendance', methods=['GET'])
@login_required
def emp_attendance():
    if current_user.role != 'employee':
        return redirect(url_for('index'))
    
    # Get the month from the query parameter or default to the current month
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    start_date = datetime.strptime(month + '-01', '%Y-%m-%d')
    end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    # Calculate total hours, total days, and leaves taken for the specific month
    sessions = WorkSession.query.filter(
        WorkSession.user_id == current_user.id,
        WorkSession.clock_in >= start_date,
        WorkSession.clock_in <= end_date
    ).all()
    
    total_hours = sum(session.total_hours for session in sessions)
    total_days = len(sessions)
    leaves_taken = Leave.query.filter(
        Leave.user_id == current_user.id,
        Leave.start_date >= start_date,
        Leave.start_date <= end_date
    ).count()
    
    return render_template('emp_attendance.html', total_hours=total_hours, total_days=total_days, leaves_taken=leaves_taken, sessions=sessions, month=month)



@app.route('/view_attendance', methods=['GET'])
@login_required
def view_attendance():
    if current_user.role not in ['admin', 'superadmin']:
        return redirect(url_for('dashboard'))
    
    employees = User.query.filter(User.role == 'employee').all()
    employee_id = request.args.get('employee_id')
    month = request.args.get('month')
    
    sessions = []
    total_hours = 0
    total_days = 0
    leaves_taken = 0
    selected_employee = None

    if employee_id and month:
        selected_employee = User.query.get(employee_id)
        start_date = datetime.strptime(month + '-01', '%Y-%m-%d')
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        sessions = WorkSession.query.filter(
            WorkSession.user_id == employee_id,
            WorkSession.clock_in >= start_date,
            WorkSession.clock_in <= end_date
        ).all()
        
        total_hours = sum(session.total_hours for session in sessions)
        total_days = len(sessions)
        leaves_taken = Leave.query.filter(
            Leave.user_id == employee_id,
            Leave.start_date >= start_date,
            Leave.start_date <= end_date
        ).count()

    return render_template('view_attendance.html', employees=employees, sessions=sessions, total_hours=total_hours, total_days=total_days, leaves_taken=leaves_taken, selected_employee=selected_employee, month=month)

##########################################LEAVE#############################################################
############################################################################################################
############################################################################################################
@app.route('/leave')
@login_required
def leave():
    my_leaves = Leave.query.filter_by(user_id=current_user.id).all()
    return render_template('leave.html', my_leaves=my_leaves)


# Route to apply for leave
@app.route('/apply_leave', methods=['GET', 'POST'])
@login_required
def apply_leave():
    if request.method == 'POST':
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%dT%H:%M')
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%dT%H:%M')
        reason = request.form['reason']
        leave = Leave(user_id=current_user.id, start_date=start_date, end_date=end_date, reason=reason)
        db.session.add(leave)
        db.session.commit()

        # Send email to admin
        admin_email = "digifalx.head@gmail.com"  # Replace with admin email
        msg = Message(
            subject=f"New Leave Request from {current_user.username}",
            recipients=[admin_email],
            body=f"Leave Details:\nStart Date: {start_date}\nEnd Date: {end_date}\nReason: {reason}"
        )
        mail.send(msg)

        flash('Leave request submitted successfully', 'success')
        return redirect(url_for('apply_leave'))
    return render_template('leave_application.html')

# Route to update leave status
@app.route('/update_leave_status/<int:leave_id>', methods=['POST'])
@login_required
def update_leave_status(leave_id):
    leave = Leave.query.get_or_404(leave_id)
    leave.status = request.form['status']
    db.session.commit()
    flash(f'Leave request {leave.status}', 'success')
    return redirect(url_for('admin_dashboard'))

# Route for admin dashboard
@app.route('/admin_leave')
@login_required
def admin_leave():
    if current_user.role not in ['admin', 'superadmin']:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    pending_leaves = Leave.query.filter_by(status='pending').all()
    all_leaves = Leave.query.all()
    return render_template('admin_leave.html', pending_leaves=pending_leaves, all_leaves=all_leaves)



###############################################MEETSCHEDULER CALENDER#######################################
############################################################################################################
############################################################################################################

@app.route('/schedule', methods=['GET', 'POST'])
@login_required
def schedule():
    users = User.query.all()  # Fetch all users
    if request.method == 'POST':
        title = request.form['title']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        description = request.form['description']
        attendees_ids = request.form.getlist('attendees')
        attendees = [User.query.get(int(id)).email for id in attendees_ids]  # Get the emails of the attendees
        
        new_meeting = Meeting(title=title, start_time=start_time, end_time=end_time, description=description, attendees=','.join(attendees))
        db.session.add(new_meeting)
        db.session.commit()

        # Send email notification
        msg = Message('Meeting Scheduled: ' + title,
                      sender='digifalx.head@gmail.com',
                      recipients=attendees)
        msg.body = f'''
        Meeting Details:
        Title: {title}
        Start Time: {start_time}
        End Time: {end_time}
        Description: {description}
        '''
        mail.send(msg)

        flash('Meeting scheduled successfully!')
        return redirect(url_for('calendar'))

    return render_template('schedule.html', users=users)


@app.route('/calendar')
@login_required
def calendar():
    meetings = Meeting.query.all()
    meetings_dict = [meeting.to_dict() for meeting in meetings]
    return render_template('calendar.html', meetings=meetings_dict)

@app.route('/meeting/<int:meeting_id>')
@login_required
def view_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    return render_template('view_meeting.html', meeting=meeting)







if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
