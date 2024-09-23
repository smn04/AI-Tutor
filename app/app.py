# app/app.py
import cv2
from flask import Flask, render_template, redirect, url_for, flash, session, request, jsonify
from flask_wtf import FlaskForm
import numpy as np
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from flask_sqlalchemy import SQLAlchemy
import random
import smtplib
import pytesseract
from email.message import EmailMessage
from textblob import TextBlob
from lesson.app import lesson_bp  # Import the lesson blueprint
from learning.app1 import learning_bp
from summariser.app import summariser_bp
from scipy.ndimage import interpolation as inter
from models import Registration
from models import db
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/ai_tutor'  # Replace with your MySQL connection details
db.init_app(app)

# Register the lesson blueprint with the main app
app.register_blueprint(lesson_bp, url_prefix='/lesson_module')
app.register_blueprint(learning_bp,url_prefix='/scheduler')
app.register_blueprint(summariser_bp,url_prefix='/summariser')

class SignUpForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


@app.route('/')
def index():
    return render_template('AITUTOR-INDEX PAGE/indexpage-AItutor.html')

@app.route('/indexx')
def indexx():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm()
    if form.validate_on_submit():
        name=form.name.data
        username = form.username.data
        email = form.email.data
        password = form.password.data
        print(password)
        
        existing_email = Registration.query.filter_by(email=email).first()
        existing_username=Registration.query.filter_by(username=username).first()
        if existing_email:
            response = {'success': False, 'message': 'Email already registered. Please use a different email.'}
        elif existing_username:
            response = {'success': False, 'message': 'Username already exists. Please use a different username.'}
        else:
            otp = ''.join(random.choices('0123456789', k=6))

            # Send the OTP to the user's email
            send_otp_to_email(email, otp)

            # Store the OTP in the session for later verification
            session['otp'] = otp

            # Store other user data in the session for later use
            session['name'] = name
            session['username'] = username
            session['email'] = email
            session['password'] = password

            response = {'success': True, 'message': 'OTP sent to your email for verification.'}
        
        return jsonify(response)
    return render_template('signup.html', form=form)
def send_otp_to_email(email, otp):
    msg = EmailMessage()
    msg.set_content(f'Your OTP for email verification: {otp}')
    msg['Subject'] = 'Email Verification OTP'
    msg['From'] = 'nairsreeshma2907@gmail.com'  # Replace with your email address
    msg['To'] = email

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login('nairsreeshma2907@gmail.com', 'wkln jypr ozwq hwxk')  # Replace with your email and password

    server.send_message(msg)
    server.quit()

@app.route('/otp_verification', methods=['GET', 'POST'])
def otp_verification():
    if request.method == 'POST':
        data = request.get_json()
        user_entered_otp = data.get('otp')
        stored_otp = session.get('otp')
        
        if user_entered_otp == stored_otp:
            # OTP verified successfully, activate the user's account in the database
            name = session.get('name')
            username = session.get('username')
            email = session.get('email')
            password = session.get('password')
            
            new_user = Registration(name=name, username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()

            response = {'success': True, 'message': 'OTP verified successfully! Account has been activated.'}
        else:
            response = {'success': False, 'message': 'Invalid OTP. Please try again.'}

        return jsonify(response)
    else:
        # Handle GET request (if needed)
        return render_template('otp_verification.html')
@app.route('/profile')
def profile():
    user = Registration.query.filter_by(username=session['username']).first()
    return render_template('profile.html',user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        print(username,password)
        user = Registration.query.filter_by(username=username).first()
        session['username']= user.username
        session['learning_style']=user.learning_style
        print(user.username,user.password)
        if user and (user.password == password):
            response = {'success': True}
        else:
            response = {'success': False, 'message': 'Invalid email or password. Please try again.'}
        return jsonify(response)
    return render_template('login.html', form=form)
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/ocr')
def ocr():
    return render_template('ocr.html')
@app.route('/lesson_module')
def lesson():
    return redirect(url_for('lesson.lesson_index'))
@app.route('/perform_ocr', methods=['POST'])
def perform_ocr():
    try:
        # Get the uploaded image from the request
        image_file = request.files['image']
        image_data = image_file.read()

        # Convert the image data to a NumPy array
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Step 1: Binarization
        optimal_threshold = 123
        _, binary_image = cv2.threshold(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), optimal_threshold, 255, cv2.THRESH_BINARY)

        # Step 2: Skew Correction
        def find_score(arr, angle):
            data = inter.rotate(arr, angle, reshape=False, order=0)
            hist = np.sum(data, axis=1)
            score = np.sum((hist[1:] - hist[:-1]) ** 2)
            return hist, score

        delta = 1
        limit = 5
        angles = np.arange(-limit, limit + delta, delta)
        scores = []
        for angle in angles:
            hist, score = find_score(binary_image, angle)
            scores.append(score)
        best_score = max(scores)
        best_angle = angles[scores.index(best_score)]

        # Correct skew
        binary_image = inter.rotate(binary_image, best_angle, reshape=False, order=0)
        binary_image_color = cv2.cvtColor(binary_image, cv2.COLOR_GRAY2BGR)
        # Step 3: Noise Removal
        dst = cv2.fastNlMeansDenoisingColored(binary_image_color, None, 10, 10, 7, 15)

        # OCR
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        img = cv2.resize(dst, (800, 800))
        import time
        
        ocr_result = pytesseract.image_to_string(img)
        
        
        # Spell Checker
        corrected_text = str(TextBlob(ocr_result))

        # Return the OCR result and corrected text to the frontend
        return jsonify({'result': corrected_text})
    except Exception as e:
        # Handle exceptions if any
        print(e)
        return jsonify({'error': 'Error occurred during OCR processing.'})
@app.route('/scheduler')
def scheduler():
    return redirect(url_for('learning.learning_index'))
@app.route('/summariser')
def summariser():
    return redirect(url_for('summariser.summariser_index'))
    
@app.route('/vark_quiz')
def vark_quiz():
    
    questions = [
        "I need to find the way to a shop that a friend has recommended. I would:",
        "A website has a video showing how to make a special graph or chart. I would learn most from:",
        "I want to find out more about a tour that I am going on. I would:",
        "When choosing a career or area of study, these are important for me:",
        "When I am learning I:",
        "I want to save more money and to decide between a range of options. I would:",
        "I want to learn how to play a new board game or card game. I would:",
        "I have a problem with my heart. I would prefer that the doctor:",
        "I want to learn to do something new on a computer. I would:",
        "When learning from the Internet I like:",
        "I want to learn about a new project. I would ask for:",
        "I want to learn how to take better photos. I would:",
        "I prefer a presenter or a teacher who uses:",
        "I have finished a competition or test and I would like some feedback. I would like to have feedback:",
        "I want to assemble a wooden table that came in parts (kitset). I would learn best from:"
    ]

    options = [
        ["a. find out where the shop is in relation to somewhere I know.",
        "b. ask my friend to tell me the directions.",
        "c. write down the street directions I need to remember.",
        "d. use a map."],
        
        ["a. seeing the diagrams.",
        "b. listening.",
        "c. reading the words.",
        "d. watching the actions."],
        
        ["a. look at details about the highlights and activities on the tour.",
        "b. use a map and see where the places are.",
        "c. read about the tour on the itinerary.",
        "d. talk with the person who planned the tour or others who are going on the tour."],
        
        ["a. Applying my knowledge in real situations.",
        "b. Communicating with others through discussion.",
        "c. Working with designs, maps or charts.",
        "d. Using words well in written communications."],
        
        ["a. like to talk things through.",
        "b. see patterns in things.",
        "c. use examples and applications.",
        "d. read books, articles and handouts."],
        
        ["a. consider examples of each option using my financial information.",
        "b. read a print brochure that describes the options in detail.",
        "c. use graphs showing different options for different time periods.",
        "d. talk with an expert about the options."],
        
        ["a. watch others play the game before joining in.",
        "b. listen to somebody explaining it and ask questions.",
        "c. use the diagrams that explain the various stages, moves and strategies in the game.",
        "d. read the instructions."],
        
        ["a. gave me something to read to explain what was wrong.",
        "b. used a plastic model to show me what was wrong.",
        "c. described what was wrong.",
        "d. showed me a diagram of what was wrong."],
        
        ["a. read the written instructions that came with the program.",
        "b. talk with people who know about the program.",
        "c. start using it and learn by trial and error.",
        "d. follow the diagrams in a book."],
        
        ["a. videos showing how to do or make things.",
        "b. interesting design and visual features.",
        "c. interesting written descriptions, lists and explanations.",
        "d. audio channels where I can listen to podcasts or interviews."],
        
        ["a. diagrams to show the project stages with charts of benefits and costs.",
        "b. a written report describing the main features of the project.",
        "c. an opportunity to discuss the project.",
        "d. examples where the project has been used successfully."],
        
        ["a. ask questions and talk about the camera and its features.",
        "b. use the written instructions about what to do.",
        "c. use diagrams showing the camera and what each part does.",
        "d. use examples of good and poor photos showing how to improve them."],
        
        ["a. demonstrations, models or practical sessions.",
        "b. question and answer, talk, group discussion, or guest speakers.",
        "c. handouts, books, or readings.",
        "d. diagrams, charts, maps or graphs."],
        
        ["a. using examples from what I have done.",
        "b. using a written description of my results.",
        "c. from somebody who talks it through with me.",
        "d. using graphs showing what I achieved."],
        
        ["a. diagrams showing each stage of the assembly.",
        "b. advice from someone who has done it before.",
        "c. written instructions that came with the parts for the table.",
        "d. watching a video of a person assembling a similar table."]
    ]
    return render_template('vark_quiz.html',questions=questions, options=options)

@app.route('/quiz', methods=['POST'])
def quiz():
    responses = request.form.to_dict()
    answers={'1':{'a':'k','b':'a','c':'r','d':'v'},
             '2':{'a':'v','b':'a','c':'r','d':'k'},
             '3':{'a':'k','b':'a','c':'r','d':'a'},
             '4':{'a':'k','b':'v','c':'r','d':'a'},
             '5':{'a':'a','b':'v','c':'k','d':'r'},
             '6':{'a':'k','b':'r','c':'v','d':'a'},
             '7':{'a':'k','b':'a','c':'v','d':'r'},
             '8':{'a':'r','b':'k','c':'a','d':'v'},
              '9':{'a':'r','b':'a','c':'k','d':'v'},
               '10':{'a':'k','b':'v','c':'r','d':'a'},
                '11':{'a':'v','b':'r','c':'a','d':'k'},
                 '12':{'a':'a','b':'r','c':'v','d':'k'},
                  '13':{'a':'k','b':'a','c':'r','d':'v'},
                   '14':{'a':'k','b':'r','c':'a','d':'v'},
                     '15':{'a':'v','b':'a','c':'r','d':'k'},

             }
   

    learning_style = calculate_learning_style(responses,answers)
    learning_style_mapping = {
    'Visual': 'v',
    'Auditory': 'a',
    'Reading/Writing': 'r',
    'Kinesthetic': 'k'
}


    # Update the learning style in the database
    user = Registration.query.filter_by(username=session['username']).first()
    user.learning_style = learning_style_mapping.get(learning_style, '')

    # Commit the changes to the database
    db.session.commit()
    learning_style_images = {
    'Visual': '/static/visual_image.jpg',  # Replace 'visual_image.jpg' with the actual filename of your visual image
    'Auditory': '/static/auditory_image.png',  # Replace 'auditory_image.jpg' with the actual filename of your auditory image
    'Reading/Writing': '/static/read-write_image.png',  # Replace 'reading_image.jpg' with the actual filename of your reading image
    'Kinesthetic': '/static/kinesthetic_image.png'  # Replace 'kinesthetic_image.jpg' with the actual filename of your kinesthetic image
}
    return render_template('vark_quiz_result.html', learning_style=learning_style,learning_style_images=learning_style_images)

def calculate_learning_style(responses,answers):
    v_count = 0
    a_count = 0
    r_count = 0
    k_count = 0

    # Counting the responses
    for question in responses:
        question_number = question[8:]
        x=int(question_number)+1
        question_number=str(x)
        option_selected=answers[question_number][responses[question]]
        if option_selected == "a":
            a_count += 1
        elif option_selected == "v":
            v_count += 1
        elif option_selected == "r":
            r_count += 1
        else:
            k_count += 1
    print(v_count,a_count,r_count,k_count)
    # Determining the learning style based on counts
    max_count = max(v_count, a_count, r_count, k_count)
    if max_count == v_count:
        learning_style = 'Visual'
    elif max_count == a_count:
        learning_style = 'Auditory'
    elif max_count == r_count:
        learning_style = 'Reading/Writing'
    else:
        learning_style = 'Kinesthetic'

    return learning_style

if __name__ == '__main__':
    db.create_all()  # Create the database tables before running the app
    app.run(debug=True)
