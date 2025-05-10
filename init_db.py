from app import db, app  # adjust import to your actual app name
from models import *  # make sure all models are imported

with app.app_context():
    db.create_all()
    print("Database initialized.")

# from app import app, db
# from models import User  # adjust import path as needed

# with app.app_context():
#     if not User.query.filter_by(username='admin').first():
#         admin = User(
#             name='Prashant Saini',
#             username='admin',
#             mobile='9818401912',
#             role='admin'
#         )
#         admin.set_password('admin')  # Use a strong password in production
#         db.session.add(admin)
#         db.session.commit()
#         print("✅ Prashant Saini user created with username 'admin' and password 'admin'")
#     else:
#         print("⚠️ Admin user already exists")