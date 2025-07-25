import sys
import os
import pandas as pd
import datetime
import glob
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

app = Flask(__name__)
app.secret_key = 'cryo_em_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=30)

# Email configuration
# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = 'newstarinfosis@gmail.com'
app.config['MAIL_PASSWORD'] = 'jxetbmkjapaknmhx'
app.config['MAIL_DEFAULT_SENDER'] = 'newstarinfosis@gmail.com'


mail = Mail(app)

# Ensure data directory exists
os.makedirs('src/data', exist_ok=True)

# Initialize Excel files if they don't exist
if not os.path.exists('src/data/registrations.xlsx'):
    df = pd.DataFrame(columns=['User Name', 'PI Name', 'Email', 'Origin', 'ESM', 'Sample Name', 'Grids', 'Days', 'Registration Date', 'Status'])
    df.to_excel('src/data/registrations.xlsx', index=False)

if not os.path.exists('src/data/history.xlsx'):
    df = pd.DataFrame(columns=['User Name', 'PI Name', 'Email', 'Origin', 'ESM', 'Sample Name', 'Grids', 'Days', 'Registration Date', 'Completion Date'])
    df.to_excel('src/data/history.xlsx', index=False)

# Force recreate admin.xlsx to fix the KeyError issue
df = pd.DataFrame({'Username': ['admin'], 'Password': [generate_password_hash('admin123')]})
df.to_excel('src/data/admin.xlsx', index=False)

# Get slideshow images
def get_slideshow_images():
    try:
        slideshow_dir = os.path.join(app.static_folder, 'slideshow')
        print(f"Looking for images in: {slideshow_dir}")  # Debug
        
        if not os.path.exists(slideshow_dir):
            print("Slideshow directory doesn't exist!")  # Debug
            os.makedirs(slideshow_dir)
            return []
            
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif']:
            image_files.extend(glob.glob(os.path.join(slideshow_dir, ext)))
            
        print(f"Found images: {image_files}")  # Debug
        return [os.path.basename(img) for img in image_files]
    except Exception as e:
        print(f"Error getting slideshow images: {e}")  # Debug
        return []

# Send email function
def send_email(recipient, subject, body):
    try:
        msg = Message(subject, recipients=[recipient])
        msg.body = body
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


@app.route('/')
@app.route('/index')
def index():
        return render_template('index.html')


@app.route('/home')
def home():
    slideshow_images = get_slideshow_images()
    print("Found slideshow images:", slideshow_images)  # Debug output
    return render_template('home.html', slideshow_images=slideshow_images)


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/team')
def team():
    return render_template('team.html')

@app.route('/facility')
def facility():
    return render_template('facility.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_name = request.form['user_name']
        pi_name = request.form['pi_name']
        email = request.form['email']
        origin = request.form['origin']
        esm = 'iisc' if origin == 'internal' else request.form['esm']
        sample_name = request.form['sample_name']
        grids = request.form['grids']
        days = request.form['days']
        registration_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Read existing registrations
        df = pd.read_excel('src/data/registrations.xlsx')
        
        # Add new registration
        new_row = {
            'User Name': user_name,
            'PI Name': pi_name,
            'Email': email,
            'Origin': origin,
            'ESM': esm,
            'Sample Name': sample_name,
            'Grids': grids,
            'Days': days,
            'Registration Date': registration_date,
            'Status': 'waiting'
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
        # Save updated registrations
        df.to_excel('src/data/registrations.xlsx', index=False)
        
        # Calculate position in queue
        position = len(df[df['Status'] == 'waiting'])
        
        # Send confirmation email
        subject = "Cryo-EM Slot Registration Confirmation"
        body = f"""
        Dear {user_name},
        
        Thank you for registering for a Cryo-EM slot. Your registration has been received successfully.
        
        Registration Details:
        - User Name: {user_name}
        - PI Name: {pi_name}
        - Sample Name: {sample_name}
        - Grids: {grids}
        - Days Required: {days}
        - Registration Date: {registration_date}
        
        Your current position in the waiting queue is: {position}
        
        You will receive further notifications when your slot status changes.
        
        Best regards,
        The Cryo-EM Advanced Centre Team
        """
        send_email(email, subject, body)
        
        return redirect(url_for('list_view'))
    return render_template('register.html')

@app.route('/list')
def list_view():
    df = pd.read_excel('src/data/registrations.xlsx')
    
    # Filter for ongoing and waiting slots
    ongoing_slots = df[df['Status'] == 'ongoing'].to_dict('records')
    waiting_slots = df[df['Status'] == 'waiting'].to_dict('records')
    
    # Add position numbers
    for i, slot in enumerate(waiting_slots, 1):
        slot['Position'] = i
    
    for i, slot in enumerate(ongoing_slots, 1):
        slot['Position'] = i
    
    return render_template('list.html', ongoing_slots=ongoing_slots, waiting_slots=waiting_slots)

@app.route('/history')
def history():
    df = pd.read_excel('src/data/history.xlsx')
    history_entries = df.to_dict('records')
    
    # Add position numbers
    for i, entry in enumerate(history_entries, 1):
        entry['Position'] = i
    
    return render_template('history.html', history_entries=history_entries)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Read admin credentials
        admin_df = pd.read_excel('src/data/admin.xlsx')
        
        # Check if username exists and convert to lowercase for case-insensitive comparison
        admin_df['Username'] = admin_df['Username'].str.lower()
        username = username.lower()
        
        if username in admin_df['Username'].values:
            stored_password = admin_df.loc[admin_df['Username'] == username, 'Password'].iloc[0]
            
            # Verify password
            if check_password_hash(stored_password, password):
                session['admin_logged_in'] = True
                return redirect(url_for('admin_panel'))
        
        flash('Invalid username or password')
    
    return render_template('admin.html')

@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))

    df = pd.read_excel('src/data/registrations.xlsx')

    if 'Status' not in df.columns:
        df['Status'] = 'waiting'
        df.to_excel('src/data/registrations.xlsx', index=False)

    # Reset index to ensure we have sequential indices
    df = df.reset_index(drop=True)
    
    # Filter waiting and ongoing registrations
    waiting_df = df[df['Status'].isin(['', 'waiting'])]
    ongoing_df = df[df['Status'] == 'ongoing']
    
    # Convert to records and include the DataFrame index
    waiting_regs = waiting_df.reset_index().rename(columns={'index': '_index'}).to_dict('records')
    ongoing_regs = ongoing_df.reset_index().rename(columns={'index': '_index'}).to_dict('records')

    return render_template('admin_panel.html',
                           waiting_registrations=waiting_regs,
                           ongoing_registrations=ongoing_regs)


@app.route('/admin/complete/<int:index>')
def complete_registration(index):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    # Read registrations
    reg_df = pd.read_excel('src/data/registrations.xlsx')
    
    # Reset index to ensure we have sequential indices
    reg_df = reg_df.reset_index(drop=True)
    
    if index < len(reg_df):
        # Get the registration to complete
        registration = reg_df.iloc[index].to_dict()
        
        # Add completion date
        registration['Completion Date'] = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Read history file
        history_df = pd.read_excel('src/data/history.xlsx')
        
        # Add to history
        history_df = pd.concat([history_df, pd.DataFrame([registration])], ignore_index=True)
        history_df.to_excel('src/data/history.xlsx', index=False)
        
        # Send email notification
        subject = "Cryo-EM Slot Completed"
        body = f"""
        Dear {registration['User Name']},
        
        Your Cryo-EM slot has been marked as completed.
        
        Details:
        - Sample Name: {registration['Sample Name']}
        - Registration Date: {registration['Registration Date']}
        - Completion Date: {registration['Completion Date']}
        
        Thank you for using our services.
        
        Best regards,
        The Cryo-EM Advanced Centre Team
        """
        send_email(registration['Email'], subject, body)
        
        # Remove from registrations
        reg_df = reg_df.drop(index)
        reg_df.to_excel('src/data/registrations.xlsx', index=False)
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/load/<int:index>')
def load_registration(index):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    # Read registrations
    df = pd.read_excel('src/data/registrations.xlsx')
    
    # Reset index to ensure we have sequential indices
    df = df.reset_index(drop=True)
    
    if index < len(df):
        # Update status to ongoing
        df.at[index, 'Status'] = 'ongoing'
        df.to_excel('src/data/registrations.xlsx', index=False)
        
        # Get registration details for email
        registration = df.iloc[index].to_dict()
        
        # Send email notification
        subject = "Cryo-EM Slot Loaded"
        body = f"""
        Dear {registration['User Name']},
        
        Your Cryo-EM slot has been loaded and is now in progress.
        
        Details:
        - Sample Name: {registration['Sample Name']}
        - Registration Date: {registration['Registration Date']}
        
        You can check the status on our website under "Ongoing Slots".
        
        Best regards,
        The Cryo-EM Advanced Centre Team
        """
        send_email(registration['Email'], subject, body)
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete/<int:index>')
def delete_registration(index):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    # Read registrations
    df = pd.read_excel('src/data/registrations.xlsx')
    
    # Reset index to ensure we have sequential indices
    df = df.reset_index(drop=True)
    
    if index < len(df):
        # Get registration details for email
        registration = df.iloc[index].to_dict()
        
        # Send email notification
        subject = "Cryo-EM Slot Deleted"
        body = f"""
        Dear {registration['User Name']},
        
        Your Cryo-EM slot registration has been deleted.
        
        Details:
        - Sample Name: {registration['Sample Name']}
        - Registration Date: {registration['Registration Date']}
        
        If you believe this is an error, please contact us.
        
        Best regards,
        The Cryo-EM Advanced Centre Team
        """
        send_email(registration['Email'], subject, body)
        
        # Remove from registrations
        df = df.drop(index)
        df.to_excel('src/data/registrations.xlsx', index=False)
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

# Auto-logout when leaving admin panel
@app.before_request
def check_admin_session():
    if request.method == 'GET' and session.get('admin_logged_in'):
        if request.endpoint not in [
            'admin_panel', 'admin_logout',
            'complete_registration', 'load_registration',
            'delete_registration', 'static'
        ]:
            session.pop('admin_logged_in', None)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port=5000)
