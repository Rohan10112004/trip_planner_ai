from flask import Flask, flash, render_template, request, redirect, url_for, session, jsonify
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, auth
import pyrebase
from dotenv import load_dotenv
import os
import json
import markdown2

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Use the secret key from environment variables
app.secret_key = os.getenv('SECRET_KEY')

# Initialize Firebase Admin SDK for server-side Firebase functions
cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_SDK_PATH'))
firebase_admin.initialize_app(cred)

# Pyrebase config for client-side Firebase Authentication
firebaseConfig = {
    "apiKey": os.getenv('FIREBASE_API_KEY'),
    "authDomain": os.getenv('FIREBASE_AUTH_DOMAIN'),
    "projectId": os.getenv('FIREBASE_PROJECT_ID'),
    "storageBucket": os.getenv('FIREBASE_STORAGE_BUCKET'),
    "messagingSenderId": os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
    "appId": os.getenv('FIREBASE_APP_ID'),
    "measurementId": os.getenv('FIREBASE_MEASUREMENT_ID'),
    "databaseURL": os.getenv('FIREBASE_DATABASE_URL')
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth_client = firebase.auth()

# Authenticate with your Google API Key
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

# Set up system instructions with embedded formatting support for the chatbot
instruction = os.getenv('AI_INSTRUCTION')
model = genai.GenerativeModel(os.getenv('AI_MODEL_NAME'), system_instruction=instruction)
chat = model.start_chat()

# Serve the chat room page
@app.route('/chat_room')
def chat_room():
    if 'user' in session:
        return render_template('chat_room.html')  # Render chat_room.html if user is logged in
    else:
        return redirect(url_for('index'))  # Redirect to the index if not logged in

# Serve the home page
@app.route('/')
def index():
    return render_template('index.html')

# Endpoint to handle sending messages
@app.route('/send_message', methods=['POST'])
def send_message():
    user_message = request.json.get('message')
    bot_response = chat.send_message(user_message)
    formatted_response = markdown2.markdown(bot_response.text)
    return jsonify({'response': formatted_response})

# Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            # Using the Firebase Admin SDK to list users
            users = auth.list_users().users
            existing_user = next((user for user in users if user.email == email), None)

            if existing_user:
                return render_template('signup.html', firebase_config=firebaseConfig, error="Email already in use.")
            
            # Create a new user if email doesn't exist
            user = auth_client.create_user_with_email_and_password(email, password)
            session['user'] = user['idToken']
            session['uid']=user['localId']
            return redirect(url_for('chat_room'))
            
        except Exception as e:
            error_message = str(e)
            try:
                error_str = str(e)
                json_start_index = error_str.find("{")
                if json_start_index != -1:
                    error_data = error_str[json_start_index:]
                    error_data = json.loads(error_data)
                    if 'error' in error_data and 'message' in error_data['error']:
                        error_message = error_data['error']['message']
                        error_message = str(error_message).replace("_", " ").title()
                    else:
                        error_message = error_str
                else:
                    error_message = error_str
            except json.JSONDecodeError:
                error_message = str(e)

            return render_template('signup.html', firebase_config=firebaseConfig, error=error_message)
    else:
        return render_template('signup.html', firebase_config=firebaseConfig, google_client_id=os.getenv('GOOGLE_CLIENT_ID'))

# Login route (Email/Password)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            user = auth_client.sign_in_with_email_and_password(email, password)
            
            session['user'] = user['idToken']
            session['uid']=user['localId']
            return redirect(url_for('chat_room'))
        except Exception as e:
            error_message = "An unknown error occurred."
            try:
                error_str = str(e)
                json_start_index = error_str.find("{")
                if json_start_index != -1:
                    error_data = error_str[json_start_index:]
                    error_data = json.loads(error_data)
                    if 'error' in error_data and 'message' in error_data['error']:
                        error_message = error_data['error']['message']
                        error_message = str(error_message).replace("_", " ").title()
                    else:
                        error_message = error_str
                else:
                    error_message = error_str
            except json.JSONDecodeError:
                error_message = str(e)

            return render_template('login.html', error_message=error_message)
    else:
        return render_template('login.html')

# Google sign-in route
@app.route('/google_signin', methods=['POST'])
def google_signin():
    token = request.json.get('token')
    try:
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']
        user = auth.get_user(uid)
        session['user'] = user.uid
        return jsonify({"message": "Login successful!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Password reset route
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        try:
            auth_client.send_password_reset_email(email)
            return render_template('forgot_password.html', message="Password reset email sent. Check your inbox.")
        except Exception as e:
            error_message = str(e)
            try:
                error_str = str(e)
                json_start_index = error_str.find("{")
                if json_start_index != -1:
                    error_data = error_str[json_start_index:]
                    error_data = json.loads(error_data)
                    if 'error' in error_data and 'message' in error_data['error']:
                        error_message = error_data['error']['message']
                        error_message = str(error_message).replace("_", " ").title()
                    else:
                        error_message = error_str
                else:
                    error_message = error_str
            except json.JSONDecodeError:
                error_message = str(e)

            return render_template('forgot_password.html', error=error_message)

    return render_template('forgot_password.html')

# Get user info (for username display)
@app.route('/get_user_info', methods=['GET'])
def get_user_info():
    if 'user' in session:
        try:
            uid = session['uid']  # Get the UID from the session
            user = auth.get_user(uid) 
            print(user.email) # Fetch user using the UID
            return jsonify({'username': user.email}), 200  # Return user email
        except Exception as e:
            return jsonify({'error': str(e)}), 500  # Return error if fetching fails
    return jsonify({'error': 'User not authenticated'}), 401  # Handle unauthenticated access

# Route to log out user
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    session.pop('uid',None)  # Remove user from session
    return jsonify({"message": "Logged out successfully"}), 200

if __name__ == '__main__':
    app.run(debug=True)
