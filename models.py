# models.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.hybrid import hybrid_property
import json
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    mobile = db.Column(db.String(15))
    role = db.Column(db.String(20), nullable=False, default='admin')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Basic Details
    name = db.Column(db.String(100), nullable=False)
    class_name = db.Column(db.String(10), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    alternate_phone = db.Column(db.String(15))
    email = db.Column(db.String(100))
    school = db.Column(db.String(100))

    # Enrollment Info
    joining_date = db.Column(db.Date, nullable=False, default=date.today)
    payment_type = db.Column(db.String(10), nullable=False)  # Monthly or Yearly

    # Subject-wise fees and start dates as nested JSON
    subjects_fees = db.Column(JSON, nullable=False)

    # Notes
    notes = db.Column(db.Text)

    # Relationships
    invoices = db.relationship('Invoice', backref='student', lazy=True, cascade="all, delete-orphan")

    @property
    def has_unpaid_invoice(self):
        return any(inv.status == 'unpaid' for inv in self.invoices)

    def __repr__(self):
        return f'<Student {self.name}>'
    @property
    def parsed_subjects_fees(self):
        if isinstance(self.subjects_fees, str):
            return json.loads(self.subjects_fees or '{}')
        return self.subjects_fees or {}
    
    # Update receive till date.
    def update_subjects_received_till(self):
        for invoice in sorted(self.invoices, key=lambda x: x.to_date, reverse=True):
            if invoice.status == 'paid':
                for subject in invoice.subjects:
                    current = self.subjects_fees.get(subject, {}).get("received_till")
                    to_date_str = invoice.to_date.strftime("%Y-%m-%d")
                    if not current or datetime.strptime(to_date_str, "%Y-%m-%d").date() > datetime.strptime(current, "%Y-%m-%d").date():
                        if subject in self.subjects_fees:
                            self.subjects_fees[subject]["received_till"] = to_date_str
                break  # Only update based on latest paid invoice

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    
    # Dates
    invoice_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)  # When invoice is generated
    from_date = db.Column(db.Date, nullable=False)  # Start of invoice period
    to_date = db.Column(db.Date, nullable=False)    # End of invoice period
    fee_received_on = db.Column(db.Date)            # Actual payment date (if received)

    # Financials
    amount = db.Column(db.Float, nullable=False)            # Invoice total
    amount_received = db.Column(db.Float, default=0.0)       # Payment received
    pending = db.Column(db.Float, default=0.0)               # Auto: amount - amount_received

    # Payment info
    advance_payment = db.Column(db.String(10))               # 'yes' or 'no'
    payment_mode = db.Column(db.String(20))                  # 'online' or 'cash'
    payment_note = db.Column(db.Text)

    # Misc
    subjects = db.Column(JSON, nullable=False)
    status = db.Column(db.String(20), default='unpaid')      # 'paid' or 'unpaid'
    invoice_note = db.Column(db.Text)

    # Relationships
    transactions = db.relationship('PaymentTransaction', back_populates='invoice', lazy=True)
    
    def update_summary(self):
        total_received = sum(t.amount for t in self.transactions)
        self.amount_received = total_received
        self.pending = self.amount - total_received
        self.fee_received_on = max((t.received_on for t in self.transactions), default=None)
        self.status = 'paid' if self.pending <= 0 else 'unpaid'
    

class PaymentTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    
    amount = db.Column(db.Float, nullable=False)
    received_on = db.Column(db.Date, default=datetime.utcnow)
    payment_mode = db.Column(db.String(50))
    payment_note = db.Column(db.String(255))

    # Use explicit relationship and avoid backref conflict
    invoice = db.relationship('Invoice', back_populates='transactions')
    student = db.relationship('Student', backref='payment_transactions')