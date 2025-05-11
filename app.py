from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response, send_file, jsonify
from sqlalchemy import extract
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # Import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
from models import db, User, Student, Invoice, PaymentTransaction
import json
import pdfkit
import io
from calendar import monthrange
import calendar
from dateutil.relativedelta import relativedelta
import copy
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
import platform


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-secret-key'

db.init_app(app)  # ✅ bind db to app here

# Set up Flask-Migrate
migrate = Migrate(app, db)  # Bind migrate to your app and db

# Absolute path to wkhtmltopdf.exe
if platform.system() == "Windows":
    path_to_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
else:
    path_to_wkhtmltopdf = '/usr/bin/wkhtmltopdf'  # Linux path on Render

config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)

csrf = CSRFProtect(app)

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)

@app.template_filter('loads')
def json_loads_filter(s):
    return json.loads(s)

def parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None

@app.template_filter('str_to_date')
def str_to_date(value, format='%Y-%m-%d'):
    """Convert a string to a datetime object."""
    try:
        return datetime.strptime(value, format)
    except Exception:
        return value  # Return original if parsing fails

@app.template_filter('format_date')
def format_date(value, format='%d-%b-%Y'):
    """Format a datetime or date object."""
    try:
        return value.strftime(format)
    except Exception:
        return value

# Login to App
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['logged_in'] = True
            session['username'] = user.username
            session['name'] = user.name
            session['role'] = user.role
            session['user_id'] = user.id
            flash(f"Welcome, {user.name}!", "success")
            return redirect(url_for('dashboard'))

        return render_template('login.html', error='Invalid credentials', hide_navbar=True)
    return render_template('login.html', hide_navbar=True)

# Logout from App
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# Register New User
@app.route('/register_user', methods=['GET', 'POST'])
def register_user():

    if not session.get('logged_in') or session.get('role') == 'teacher':
        flash("You must be an admin to access that page.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        mobile = request.form['mobile']
        role = request.form['role']

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            return render_template('register_user.html', error='Username already exists!')

        # Create and save user
        new_user = User(name=name, username=username, mobile=mobile, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        # return render_template('register_user.html', success='User registered successfully!')
        flash('User registered successfully!', 'success')
        return redirect(url_for('show_users'))

    return render_template('register_user.html')

# Edit/Update User Profile/Password
@app.route('/update_profile', methods=['GET', 'POST'])
@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def update_profile(user_id=None):
    if user_id is None:
        # Editing own profile
        user_id = session['user_id']

    user = db.session.get(User, user_id)

    if request.method == 'POST':
        updated = False

        name = request.form.get('name')
        if name:
            user.name = name
            updated = True

        username = request.form.get('username')
        if username:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user and existing_user.id != user.id:
                flash("Username already taken!", "danger")
                return render_template('update_profile.html', user=user, editing_other=(user_id != session['user_id']))
            user.username = username
            updated = True

        password = request.form.get('password')
        if password:
            user.set_password(password)
            updated = True

        mobile = request.form.get('mobile')
        if mobile:
            user.mobile = mobile
            updated = True

        role = request.form.get('role')
        if role and session['role'] in ['admin', 'developer']:
            user.role = role
            updated = True

        if updated:
            db.session.commit()
            flash('User details updated successfully!', 'success')
        else:
            flash('No changes submitted.', 'info')

        return redirect(url_for('show_users' if user_id != session['user_id'] else 'dashboard'))

    return render_template('update_profile.html', user=user, editing_other=(user_id != session['user_id']))

# Show All Users
@app.route('/show_users')
def show_users():
    if 'user_id' not in session or session['role'] not in ['admin', 'developer']:
        flash("Access denied.")
        return redirect(url_for('dashboard'))

    users = User.query.all()
    return render_template('show_users.html', users=users)

# Delete Users/ Students
@app.route('/delete_entity', methods=['POST'])
def delete_entity():
    if not session.get('logged_in') or session.get('role') not in ['admin', 'developer']:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    entity_type = request.form.get('entity_type')
    entity_ids_raw = request.form.get('entity_ids')  # comes as comma-separated string from JS

    if not entity_type or not entity_ids_raw:
        flash("No items selected for deletion.", "warning")
        return redirect(url_for('home'))

    try:
        entity_ids = [int(eid.strip()) for eid in entity_ids_raw.split(',') if eid.strip()]
    except ValueError:
        flash("Invalid ID format received.", "danger")
        return redirect(url_for('home'))

    if entity_type == 'student':
        deleted_names = []
        for sid in entity_ids:
            student = Student.query.get(sid)
            if student:
                deleted_names.append(student.name)
                db.session.delete(student)
        db.session.commit()
        flash(f"{len(deleted_names)} student(s) deleted successfully!", "success")
        flash(f"Deleted students: {', '.join(deleted_names)}", "success")

    elif entity_type == 'user':
        deleted_usernames = []
        for uid in entity_ids:
            user = User.query.get(uid)
            if user:
                if user.id == session.get('user_id'):
                    flash("You cannot delete your own account!", "warning")
                    continue
                deleted_usernames.append(user.username)
                db.session.delete(user)
        db.session.commit()
        flash(f"{len(deleted_usernames)} user(s) deleted successfully!", "success")
        flash(f"Deleted users: {', '.join(deleted_usernames)}", "success")

    else:
        flash("Invalid entity type.", "danger")

    return redirect(url_for('show_users' if entity_type == 'user' else 'student_records'))

# App Homepage
@app.route("/")
@app.route("/dashboard")
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    students = Student.query.all()
    total_students = Student.query.count()
    total_invoices = Invoice.query.count()
    total_users = User.query.count()
    paid_invoices = Invoice.query.filter_by(status='paid').count()
    unpaid_invoices = Invoice.query.filter_by(status='unpaid').count()

    total_collected = db.session.query(db.func.sum(Invoice.amount_received)).scalar() or 0
    total_pending = db.session.query(db.func.sum(Invoice.pending)).scalar() or 0

    return render_template('dashboard.html', total_students=total_students, total_invoices=total_invoices, paid_invoices=paid_invoices, 
                           unpaid_invoices=unpaid_invoices, total_collected=total_collected, total_pending=total_pending, students=students, total_users = total_users)

# View All Enrolled Students
@app.route('/students')
def student_records():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    students = Student.query.all()
    return render_template('student_records.html', students=students)

# Add New Student
@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        alternate_phone = request.form.get('alternate_phone')
        class_name = request.form['class_name']
        joining_date = datetime.strptime(request.form['joining_date'], '%Y-%m-%d')
        payment_type = request.form['payment_type']
        school = request.form.get('school')
        email = request.form.get('email')
        notes = request.form.get('notes')

        subjects = request.form.getlist('subjects')
        subjects_fees = {}
        total_fee = 0

        for subject in subjects:
            fee = request.form.get(f'fee[{subject}]')
            start_date = request.form.get(f'start[{subject}]')
            received_till = request.form.get(f'received_till[{subject}]')

            if fee:
                try:
                    fee_int = int(fee)
                except ValueError:
                    fee_int = 0  # or handle error

                total_fee += fee_int
                subjects_fees[subject] = {
                    "fee": fee_int,
                    "start_date": start_date if start_date else '',
                    "received_till": received_till if received_till else ''
                }

        new_student = Student(name=name, mobile=mobile, alternate_phone=alternate_phone, class_name=class_name, subjects_fees=subjects_fees, joining_date=joining_date,
            payment_type=payment_type, school=school, email=email, notes=notes)
        db.session.add(new_student)
        db.session.commit()

        flash('Student added successfully! You can now create an invoice from their profile.', 'success')
        return redirect(url_for('student_records'))

    return render_template('add_student.html')

# View Student Details
@app.route('/student/<int:student_id>')
def view_student(student_id):
    source = request.args.get('from_', 'students')  # default to 'students'
    student = Student.query.get_or_404(student_id)

    # 🔁 Update invoice summaries and student's received_till
    for invoice in student.invoices:
        invoice.update_summary()
    student.update_subjects_received_till()
    db.session.commit()

    invoices = Invoice.query.filter_by(student_id=student.id).order_by(Invoice.from_date.desc()).all()
    all_transactions = db.session.query(PaymentTransaction, Invoice).join(Invoice).filter(PaymentTransaction.student_id == student.id).order_by(PaymentTransaction.received_on.desc()).all()

    subjects_fees = student.parsed_subjects_fees

    return render_template('view_student.html', student=student, invoices=invoices, subject_fees=subjects_fees, source=source, all_transactions=all_transactions)

# Edit Student Details
@app.route('/edit/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    print(request.form)
    student = Student.query.get_or_404(student_id)

    if request.method == 'POST':
        student.name = request.form['name']
        student.mobile = request.form['mobile']
        student.alternate_phone = request.form.get('alternate_phone')
        student.class_name = request.form['class_name']
        student.joining_date = datetime.strptime(request.form['joining_date'], '%Y-%m-%d')
        student.payment_type = request.form['payment_type']
        student.school = request.form.get('school')
        student.email = request.form.get('email')
        student.notes = request.form.get('notes')

        subjects = request.form.getlist('subjects')
        subjects_fees = {}

        for subject in subjects:
            fee = request.form.get(f'fee[{subject}]')
            start_date = request.form.get(f'start[{subject}]')
            received_till = request.form.get(f'received_till[{subject}]')

            if fee:
                try:
                    fee_int = int(fee)
                except ValueError:
                    fee_int = 0  # or flash an error
                subjects_fees[subject] = {
                    'fee': fee_int,
                    'start_date': start_date if start_date else '',
                    'received_till': received_till if received_till else ''
                }
        
        student.subjects_fees = subjects_fees
        db.session.commit()

        flash('Student updated successfully!', 'success')
        return redirect(url_for('view_student', student_id=student.id))
    
    
    subjects_fees = student.parsed_subjects_fees
    return render_template('edit_student.html', student=student, subjects_fees=subjects_fees)

# Create Invoice
@app.route('/create_invoice/<int:student_id>', methods=['GET', 'POST'])
def create_invoice(student_id):
    source = request.args.get('source', 'invoices')
    student = Student.query.get_or_404(student_id)
    subjects_dict = student.parsed_subjects_fees

    if request.method == 'POST':
        # Basic invoice fields
        invoice_date = datetime.strptime(request.form.get('invoice_date'), '%Y-%m-%d')
        from_date = datetime.strptime(request.form.get('from_date'), '%Y-%m-%d')
        to_date = datetime.strptime(request.form.get('to_date'), '%Y-%m-%d')
        fee_received_on = request.form.get('fee_received_on')
        amount = float(request.form.get('amount'))
        amount_received = float(request.form.get('amount_received'))
        advance_payment = request.form.get('advance_payment')
        payment_mode = request.form.get('payment_mode')
        payment_note = request.form.get('payment_note')
        invoice_note = request.form.get('invoice_note')
        invoice_status = 'paid' if amount_received >= amount else 'unpaid'

        # Build subjects section of invoice
        subjects_data = {}
        for subject in subjects_dict:
            fee = request.form.get(f'fee[{subject}]')
            start_date = request.form.get(f'start_date[{subject}]')
            received_till_input = request.form.get(f'received_till[{subject}]')

            # Use user input or set to to_date if paid
            if invoice_status == 'paid':
                received_till = received_till_input or to_date.isoformat()
            else:
                received_till = subjects_dict[subject].get("received_till")

            subjects_data[subject] = {
                'fee': float(fee) if fee else subjects_dict[subject].get("fee", 0),
                'start_date': start_date or subjects_dict[subject].get("start_date"),
                'received_till': received_till
            }

        # Create invoice
        invoice = Invoice(student_id=student.id, from_date=from_date, to_date=to_date, invoice_date=invoice_date, amount=amount, amount_received=amount_received,
            pending=amount - amount_received, advance_payment=advance_payment, payment_mode=payment_mode, payment_note=payment_note,
            fee_received_on=datetime.strptime(fee_received_on, '%Y-%m-%d') if fee_received_on else None,
            subjects=subjects_data, status=invoice_status, invoice_note=invoice_note)
        
        db.session.add(invoice)
        db.session.flush()  # Get invoice.id before commit

        # Log transaction if payment received
        if amount_received > 0:
            transaction = PaymentTransaction(invoice_id=invoice.id, student_id=student.id, amount=amount_received, payment_mode=payment_mode,
                                             received_on=datetime.strptime(fee_received_on, '%Y-%m-%d') if fee_received_on else datetime.utcnow(), payment_note=payment_note)
            
            db.session.add(transaction)
        db.session.commit()

        # Update student's subjects_fees received_till if invoice is fully paid
        if invoice_status == 'paid':
            updated = False
            for subject, data in subjects_data.items():
                new_till_str = data.get("received_till")
                existing_till_str = student.subjects_fees.get(subject, {}).get("received_till")

                try:
                    new_till = datetime.strptime(new_till_str, "%Y-%m-%d").date() if new_till_str else None
                    existing_till = datetime.strptime(existing_till_str, "%Y-%m-%d").date() if existing_till_str else None

                    if new_till and (not existing_till or new_till > existing_till):
                        student.subjects_fees[subject]["received_till"] = new_till_str
                        updated = True
                except Exception:
                    continue

            if updated:
                db.session.commit()
            
            # Automatically update to_date if it's newer
            student.update_subjects_received_till()

        flash('Invoice created successfully!', 'success')
        return redirect(url_for('view_invoice', invoice_id=invoice.id, source=source))

    # Prefill defaults
    today = date.today()
    first_day = today.replace(day=1)
    last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    return render_template('create_invoice.html', student=student, subjects=subjects_dict, fee_received_on=today.isoformat(), invoice_date=today.isoformat(),
                           from_date=first_day.isoformat(), to_date=last_day.isoformat(), invoice={}, source=source)


# View Specific Invoice
@app.route('/invoice/view/<int:invoice_id>')
def view_invoice(invoice_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    source = request.args.get('source', 'invoices')  # Default to 'invoices'

    invoice = Invoice.query.get_or_404(invoice_id)
    student = invoice.student  # Assuming Invoice has a relationship with Student
    all_transactions = db.session.query(PaymentTransaction, Invoice).join(Invoice).filter(PaymentTransaction.invoice_id == invoice.id).order_by(PaymentTransaction.received_on.desc()).all()

    return render_template('view_invoice.html', invoice=invoice, student=student, source=source, all_transactions=all_transactions)

# Edit Invoice
@app.route('/invoice/edit/<int:invoice_id>', methods=['GET', 'POST'])
def edit_invoice(invoice_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # Get the source from the query parameter
    source = request.args.get('source', 'invoices')  # Default to 'invoices'

    invoice = Invoice.query.get_or_404(invoice_id)
    student = invoice.student

    if request.method == 'POST':
        old_amount_received = invoice.amount_received or 0

        invoice.invoice_date = parse_date(request.form.get("invoice_date"))
        invoice.from_date = parse_date(request.form.get("from_date"))
        invoice.to_date = parse_date(request.form.get("to_date"))
        invoice.fee_received_on = parse_date(request.form.get("fee_received_on"))
        invoice.amount = float(request.form.get('amount') or 0)

         # ⚠️ Check for amount_received difference
        new_amount_received = float(request.form.get('amount_received') or 0)
        delta = new_amount_received - old_amount_received

        invoice.amount_received = new_amount_received
        invoice.pending = float(request.form.get('pending') or 0)
        invoice.payment_mode = request.form.get('payment_mode')
        invoice.payment_note = request.form.get('payment_note')
        invoice.invoice_note = request.form.get('invoice_note')

        # Log transaction if there's a change
        if delta != 0:
            transaction = PaymentTransaction(invoice_id=invoice.id, student_id=student.id, amount=delta, payment_mode=invoice.payment_mode, payment_note=invoice.payment_note,
            received_on=invoice.fee_received_on or date.today())
        
            db.session.add(transaction)

        # Process subjects
        updated_subjects = {}
        for subject in request.form.getlist('subjects'):
            fee = float(request.form.get(f'fee[{subject}]') or 0)
            start_date = request.form.get(f'start_date[{subject}]')
            received_till = request.form.get(f'received_till[{subject}]')
            updated_subjects[subject] = {
                'fee': fee,
                'start_date': start_date,
                'received_till': received_till
            }

        invoice.subjects = updated_subjects

        # Update invoice + student summary
        invoice.update_summary()
        student.update_subjects_received_till()

        db.session.commit()
        flash('Invoice updated successfully!', 'success')
        return redirect(url_for('view_invoice', invoice_id=invoice_id, source=source))

    return render_template('create_invoice.html', invoice=invoice, student=student, editing=True, source=source)

# Delete Invoice
@app.route('/invoice/delete/<int:invoice_id>', methods=['POST'])
def delete_invoice(invoice_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    invoice = Invoice.query.get_or_404(invoice_id)
    db.session.delete(invoice)
    db.session.commit()
    flash('Invoice deleted successfully.', 'success')
    return redirect(url_for('invoices'))


@app.route('/invoice_pdfview/<int:invoice_id>')
def show_invoice_pdf(invoice_id):
    print(f"Invoice ID: {invoice_id}")
    invoice = Invoice.query.get_or_404(invoice_id)
    student = invoice.student
    all_transactions = db.session.query(PaymentTransaction, Invoice).join(Invoice).filter(PaymentTransaction.invoice_id == invoice.id).order_by(PaymentTransaction.received_on.desc()).all()
    return render_template('invoice_pdf.html', invoice=invoice, student=student, all_transactions=all_transactions)

# Create pdf of invoice
@app.route('/invoice_pdf/<int:invoice_id>')
def invoice_pdf(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    student = invoice.student

    # ✅ Parse subject-wise fee structure
    subject_fees_dict = student.parsed_subjects_fees
    total_amount = sum(data['fee'] for data in subject_fees_dict.values())
    
    all_transactions = db.session.query(PaymentTransaction, Invoice).join(Invoice).filter(PaymentTransaction.invoice_id == invoice.id).order_by(PaymentTransaction.received_on.desc()).all()

    logo_url = url_for('static', filename='images/logo.png', _external=True)
    qrcode_url = url_for('static', filename='images/qrcode.jpg', _external=True)

    # ✅ Render HTML with extra data
    rendered = render_template('invoice_pdf.html', invoice=invoice, student=student, subject_fees_dict=subject_fees_dict, total_amount=total_amount, all_transactions=all_transactions, logo_url=logo_url, qrcode_url=qrcode_url)

    options = {'enable-local-file-access': '',  # ✅ Allows local static files
        'quiet': '',                     # Optional: suppress console output
        }
    # Generate PDF using configured wkhtmltopdf
    pdf = pdfkit.from_string(rendered, False, configuration=config, options=options)

    # ✅ Generate file name
    invoice_month = invoice.invoice_date.strftime('%b')
    invoice_year = invoice.invoice_date.strftime('%y')
    student_name = student.name.replace(" ", "_")
    filename = f"{student_name}_{invoice_month}_{invoice_year}.pdf"

    return send_file(io.BytesIO(pdf), mimetype='application/pdf', download_name=filename, as_attachment=True)

# View Invoices
@app.route('/invoices')
def invoices():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    month = request.args.get('month') or None
    status = request.args.get('status') or None

    invoices_query = Invoice.query

    # Filter by month
    if month:
        try:
            year, mon = map(int, month.split('-'))
            invoices_query = invoices_query.filter(
                extract('year', Invoice.invoice_date) == year,
                extract('month', Invoice.invoice_date) == mon
            )
        except ValueError:
            flash("Invalid month format. Use YYYY-MM.", "warning")

    # Filter by status
    if status and status.lower() in ['paid', 'unpaid']:
        invoices_query = invoices_query.filter_by(status=status.lower())

    invoices = invoices_query.order_by(Invoice.invoice_date.desc()).all()

    # 🔁 Update each invoice and related student summary
    updated_students = set()
    for invoice in invoices:
        invoice.update_summary()
        updated_students.add(invoice.student)  # Avoid redundant updates

    for student in updated_students:
        student.update_subjects_received_till()
    db.session.commit()

    students = Student.query.all()

    return render_template('invoices.html', invoices=invoices, students=students, selected_month=month or '', selected_status=status or '')

# Auto generate invoice on button click
@app.route('/generate_invoices')
def generate_invoices():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    today = date.today()
    students = Student.query.all()
    generated_count = 0

    for student in students:
        if not student.joining_date:
            continue
        
        subjects_fees = student.parsed_subjects_fees
        if not subjects_fees:
            continue

        total_amount = sum(subject_data['fee'] for subject_data in subjects_fees.values())
        latest_invoice = Invoice.query.filter_by(student_id=student.id).order_by(Invoice.to_date.desc()).first()

        if latest_invoice:
            from_date = latest_invoice.to_date + relativedelta(days=1)
        else:
            # Start from joining date
            from_date = student.joining_date

        while from_date <= today:
            year, month = from_date.year, from_date.month
            start_date = from_date

            # End of the month
            end_day = monthrange(year, month)[1]
            end_date = date(year, month, end_day)

            # Avoid duplicate
            existing = Invoice.query.filter_by(student_id=student.id, from_date=start_date, to_date=end_date).first()
            if existing:
                from_date = end_date + relativedelta(days=1)
                continue

            new_invoice = Invoice(student_id=student.id, invoice_date=today, from_date=start_date, to_date=end_date, amount=total_amount, amount_received=0,
                pending=total_amount, status='unpaid', subjects=copy.deepcopy(subjects_fees), invoice_note='Auto-generated monthly invoice')

            db.session.add(new_invoice)
            generated_count += 1

            # Move to next month
            from_date = end_date + relativedelta(days=1)

    db.session.commit()
    flash(f"{generated_count} new invoice(s) generated.", 'success')
    return redirect(url_for('invoices'))

# Receive Payments
@app.route('/receive_payment/<int:student_id>', methods=['GET', 'POST'])
def receive_payment(student_id):
    student = Student.query.get_or_404(student_id)
    selected_date = request.args.get('date', datetime.today().strftime('%Y-%m-%d'))

    # 🔁 Update all invoice summaries to reflect latest transactions
    for invoice in student.invoices:
        invoice.update_summary()
    student.update_subjects_received_till()
    db.session.commit()

    if request.method == 'POST':
        invoice_ids = request.form.getlist('invoice_ids')
        for invoice_id in invoice_ids:
            invoice = Invoice.query.get(int(invoice_id))
            if not invoice:
                continue
            try:
                amount_received = float(request.form.get(f'amount_received_{invoice_id}', 0))
                if amount_received <= 0:
                    continue  # skip empty/zero inputs
                received_on_str = request.form.get(f'fee_received_on_{invoice_id}', selected_date)
                received_on = datetime.strptime(received_on_str, '%Y-%m-%d').date()
                payment_mode = request.form.get(f'payment_mode_{invoice_id}')
                payment_note = request.form.get(f'payment_note')

                # Create a new transaction record
                transaction = PaymentTransaction(invoice_id=invoice.id, student_id=student.id, amount=amount_received, received_on=received_on, payment_mode=payment_mode, payment_note=payment_note)
                db.session.add(transaction)
                
                # Update invoice summary
                invoice.update_summary()

            except Exception as e:
                db.session.rollback()
                flash(f'Error processing payment for invoice {invoice_id}: {str(e)}', 'danger')
                return redirect(url_for('receive_payment', student_id=student.id))

        # After all invoices, update student received till info
        student.update_subjects_received_till()
        db.session.commit()

        flash('Payments processed successfully.', 'success')
        return redirect(url_for('receive_payment', student_id=student.id))

    invoices = Invoice.query.filter_by(student_id=student.id).order_by(Invoice.from_date.desc()).all()
    unpaid_invoices = Invoice.query.filter(Invoice.student_id == student.id, Invoice.pending != 0).order_by(Invoice.from_date.desc()).all()
    all_transactions = db.session.query(PaymentTransaction, Invoice).join(Invoice).filter(PaymentTransaction.student_id == student.id).order_by(PaymentTransaction.received_on.desc()).all()

    return render_template('receive_payment.html', student=student, invoices=invoices, unpaid_invoices=unpaid_invoices, all_transactions=all_transactions, today=selected_date)

# Edit Transaction
@app.route('/edit_transaction/<int:transaction_id>', methods=['POST'])
def edit_transaction(transaction_id):
    transaction = PaymentTransaction.query.get_or_404(transaction_id)
    invoice = transaction.invoice

    try:
        transaction.received_on = datetime.strptime(request.form['received_on'], '%Y-%m-%d')
        transaction.amount = float(request.form['amount'])
        transaction.payment_mode = request.form['payment_mode']
        transaction.payment_note = request.form['payment_note']

        db.session.commit()
        invoice.update_summary()
        db.session.commit()
        flash('Transaction updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating transaction: {e}', 'danger')

    return redirect(url_for('receive_payment', student_id=invoice.student_id))

# Delete Transaction
@app.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    transaction = PaymentTransaction.query.get_or_404(transaction_id)
    invoice = transaction.invoice

    db.session.delete(transaction)
    db.session.commit()

    invoice.update_summary()
    db.session.commit()

    flash('Transaction deleted successfully.', 'success')
    return redirect(url_for('receive_payment', student_id=invoice.student_id))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
