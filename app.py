import eventlet
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

eventlet.monkey_patch()

# Application setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, async_mode='eventlet')

# User authentication setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    messages = db.relationship('Message', backref='author', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    messages = db.relationship('Message', backref='channel', lazy='dynamic')
    
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database and initial data
with app.app_context():
    db.create_all()
    if not User.query.first():
        admin = User(username='Admin')
        admin.set_password('password')
        db.session.add(admin)
        db.session.commit()
    if not Channel.query.first():
        general_channel = Channel(name='general')
        db.session.add(general_channel)
        db.session.commit()

@app.route('/')
@login_required
def index():
    channels = Channel.query.all()
    return render_template('index.html', channels=channels)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        existing_user = User.query.filter_by(username=username).first()
        
        if existing_user:
            flash('Username already exists', 'error')
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful. You can now log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/create_channel', methods=['POST'])
@login_required
def create_channel():
    channel_name = request.form.get('channel_name')
    if channel_name:
        new_channel = Channel(name=channel_name)
        db.session.add(new_channel)
        db.session.commit()
    return redirect(url_for('index'))

# SocketIO Events for real-time interaction
@socketio.on('join_channel')
@login_required
def handle_join_channel(data):
    channel_id = data.get('channel_id')
    channel = Channel.query.get(channel_id)
    if channel:
        room = f'channel_{channel.id}'
        join_room(room)
        emit('status', {'msg': f'{current_user.username} has entered #{channel.name}.'}, room=room)
        
        # Load message history
        messages = Message.query.filter_by(channel_id=channel.id).order_by(Message.timestamp).all()
        history = [
            {
                'author': m.author.username,
                'content': m.content,
                'timestamp': m.timestamp.strftime('%I:%M %p')
            }
            for m in messages
        ]
        emit('message_history', {'messages': history}, room=request.sid)

@socketio.on('leave_channel')
@login_required
def handle_leave_channel(data):
    channel_id = data.get('channel_id')
    channel = Channel.query.get(channel_id)
    if channel:
        room = f'channel_{channel.id}'
        leave_room(room)
        emit('status', {'msg': f'{current_user.username} has left #{channel.name}.'}, room=room)

@socketio.on('send_message')
@login_required
def handle_send_message(data):
    channel_id = data.get('channel_id')
    content = data.get('content')
    
    if channel_id and content:
        new_message = Message(
            content=content,
            user_id=current_user.id,
            channel_id=channel_id
        )
        db.session.add(new_message)
        db.session.commit()
        
        room = f'channel_{channel_id}'
        emit('new_message', {
            'author': current_user.username,
            'content': content,
            'timestamp': new_message.timestamp.strftime('%I:%M %p')
        }, room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)

