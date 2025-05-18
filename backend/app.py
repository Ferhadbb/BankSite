from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bank.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Database Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    full_name = db.Column(db.String(120), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    balance = db.Column(db.Float, default=0.0)
    account_type = db.Column(db.String(50), default='Savings') # e.g., Savings, Checking
    user = db.relationship('User', backref=db.backref('accounts', lazy=True))

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False) # e.g., deposit, withdrawal, transfer
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    description = db.Column(db.String(200))
    account = db.relationship('Account', backref=db.backref('transactions', lazy=True))

class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    card_number = db.Column(db.String(16), unique=True, nullable=False)
    expiry_date = db.Column(db.String(5), nullable=False) # MM/YY
    cvv = db.Column(db.String(3), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    account = db.relationship('Account', backref=db.backref('cards', lazy=True))

# --- Helper Functions ---
def generate_account_number():
    import random
    return str(random.randint(1000000000, 9999999999))

def generate_card_details():
    import random, datetime
    card_number = ''.join([str(random.randint(0, 9)) for _ in range(16)])
    # Ensure expiry is in the future
    current_year = datetime.date.today().year % 100 # last two digits
    current_month = datetime.date.today().month
    exp_year = current_year + random.randint(3, 5) # Expires in 3-5 years
    exp_month = random.randint(1, 12)
    # If expiring this year, ensure month is ahead
    if exp_year == current_year and exp_month <= current_month:
        exp_month = random.randint(current_month + 1, 12) if current_month < 12 else current_month # avoid issues with december

    expiry_date = f"{exp_month:02d}/{exp_year:02d}"
    cvv = ''.join([str(random.randint(0, 9)) for _ in range(3)])
    return card_number, expiry_date, cvv

# --- Routes ---
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form.get('full_name', '')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
            return render_template('register.html')

        new_user = User(username=username, full_name=full_name)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Create a default account for the new user
        new_account = Account(
            user_id=new_user.id,
            account_number=generate_account_number(),
            account_type='Savings',
            balance=1000.0 # Starting balance for new users
        )
        db.session.add(new_account)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
            return render_template('login.html')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access the dashboard.', 'info')
        return redirect(url_for('login'))
    
    user = db.session.get(User, session['user_id'])
    accounts = Account.query.filter_by(user_id=user.id).all()

    if not accounts:
        # This case should ideally not happen if an account is created upon registration
        flash('No accounts found. Please contact support.', 'warning')
        return render_template('dashboard_overview.html', user=user, accounts=[])

    # If only one account, maybe redirect to its detail page directly?
    # For now, let's always show the overview.
    return render_template('dashboard_overview.html', user=user, accounts=accounts)

@app.route('/account/<int:account_id>')
def account_details(account_id):
    if 'user_id' not in session:
        flash('Please log in.', 'info')
        return redirect(url_for('login'))

    account = Account.query.filter_by(id=account_id, user_id=session['user_id']).first_or_404()
    # In a real app, you might want more specific error handling or a custom 404 page.
    # For now, first_or_404() will raise a Werkzeug NotFound exception if no account is found
    # or if the account doesn't belong to the logged-in user.

    return render_template('account_detail.html', account=account)

@app.route('/account/<int:account_id>/transactions')
def account_transactions(account_id):
    if 'user_id' not in session:
        flash('Please log in.', 'info')
        return redirect(url_for('login'))

    account = Account.query.filter_by(id=account_id, user_id=session['user_id']).first_or_404()
    transactions = Transaction.query.filter_by(account_id=account.id).order_by(Transaction.timestamp.desc()).all()
    return render_template('account_transactions.html', account=account, transactions=transactions)

@app.route('/account/<int:account_id>/cards')
def account_cards(account_id):
    if 'user_id' not in session:
        flash('Please log in.', 'info')
        return redirect(url_for('login'))
    
    account = Account.query.filter_by(id=account_id, user_id=session['user_id']).first_or_404()
    cards = Card.query.filter_by(account_id=account.id).all()
    return render_template('account_cards.html', account=account, cards=cards)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/deposit', methods=['POST'])
def deposit():
    if 'user_id' not in session:
        flash('Please log in to make a deposit.', 'info')
        return redirect(url_for('login'))

    try:
        amount = float(request.form['amount'])
        account_id = int(request.form['account_id'])
    except ValueError:
        flash('Invalid amount or account ID.', 'error')
        return redirect(request.referrer or url_for('dashboard'))

    if amount <= 0:
        flash('Deposit amount must be positive.', 'error')
        return redirect(request.referrer or url_for('account_details', account_id=account_id))

    account = db.session.get(Account, account_id)
    if account and account.user_id == session['user_id']:
        account.balance += amount
        new_transaction = Transaction(account_id=account.id, type='deposit', amount=amount, description='User deposit')
        db.session.add(new_transaction)
        db.session.commit()
        flash(f'${amount:.2f} deposited successfully to account {account.account_number}.', 'success')
    else:
        flash('Account not found or you do not have permission to access it.', 'error')
    
    return redirect(url_for('account_details', account_id=account_id))

@app.route('/withdraw', methods=['POST'])
def withdraw():
    if 'user_id' not in session:
        flash('Please log in to make a withdrawal.', 'info')
        return redirect(url_for('login'))

    try:
        amount = float(request.form['amount'])
        account_id = int(request.form['account_id'])
    except ValueError:
        flash('Invalid amount or account ID.', 'error')
        return redirect(request.referrer or url_for('dashboard'))

    if amount <= 0:
        flash('Withdrawal amount must be positive.', 'error')
        return redirect(request.referrer or url_for('account_details', account_id=account_id))

    account = db.session.get(Account, account_id)
    if account and account.user_id == session['user_id']:
        if account.balance >= amount:
            account.balance -= amount
            new_transaction = Transaction(account_id=account.id, type='withdrawal', amount=amount, description='User withdrawal')
            db.session.add(new_transaction)
            db.session.commit()
            flash(f'${amount:.2f} withdrawn successfully from account {account.account_number}.', 'success')
        else:
            flash('Insufficient funds.', 'error')
    else:
        flash('Account not found or you do not have permission to access it.', 'error')
    
    return redirect(url_for('account_details', account_id=account_id))

@app.route('/issue_card', methods=['POST'])
def issue_card():
    if 'user_id' not in session:
        flash('Please log in to issue a card.', 'info')
        return redirect(url_for('login'))

    account_id = int(request.form['account_id'])
    account = db.session.get(Account, account_id)

    if account and account.user_id == session['user_id']:
        # Basic check: limit to 3 cards per account for simplicity
        existing_cards_count = Card.query.filter_by(account_id=account.id).count()
        if existing_cards_count >= 3:
            flash('You have reached the maximum number of cards for this account.', 'warning')
            return redirect(url_for('account_cards', account_id=account_id))

        card_number, expiry_date, cvv = generate_card_details()
        
        new_card = Card(
            account_id=account.id,
            card_number=card_number,
            expiry_date=expiry_date,
            cvv=cvv
        )
        db.session.add(new_card)
        db.session.commit()
        flash(f'New card issued successfully for account {account.account_number}.', 'success')
    else:
        flash('Account not found or you do not have permission to access it.', 'error')
    
    return redirect(url_for('account_cards', account_id=account_id))

@app.route('/transfer', methods=['GET', 'POST'])
def transfer_funds():
    if 'user_id' not in session:
        flash('Please log in to transfer funds.', 'info')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_accounts = Account.query.filter_by(user_id=user_id).all()

    if not user_accounts or len(user_accounts) < 1: # Need at least one account to transfer from, ideally 2 for internal transfer
        flash('You need at least one account to transfer funds. Consider opening another account if you wish to transfer internally.', 'warning')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            from_account_id = int(request.form['from_account'])
            to_account_number = request.form['to_account_number'] # Target account number (string)
            amount = float(request.form['amount'])
            description = request.form.get('description', 'Fund transfer')
        except ValueError:
            flash('Invalid data provided for transfer.', 'error')
            return render_template('transfer_funds.html', accounts=user_accounts, error='Invalid input.')

        if amount <= 0:
            flash('Transfer amount must be positive.', 'error')
            return render_template('transfer_funds.html', accounts=user_accounts)

        from_account = db.session.get(Account, from_account_id)
        # For simplicity, allowing transfer to any account in the system by account number.
        # In a real system, you'd have stricter checks and differentiate between internal and external transfers.
        to_account = Account.query.filter_by(account_number=to_account_number).first()

        if not from_account:
            flash('Invalid source account selected.', 'error')
        elif not to_account:
            flash(f'Recipient account {to_account_number} not found.', 'error')
        elif from_account.id == to_account.id:
            flash('Cannot transfer funds to the same account.', 'error')
        elif from_account.balance < amount:
            flash('Insufficient funds in the source account.', 'error')
        else:
            # Perform the transfer
            from_account.balance -= amount
            to_account.balance += amount

            # Record transactions
            withdrawal_tx = Transaction(
                account_id=from_account.id,
                type='transfer_out',
                amount=amount,
                description=f'Transfer to {to_account.account_number} - {description}'
            )
            deposit_tx = Transaction(
                account_id=to_account.id,
                type='transfer_in',
                amount=amount,
                description=f'Transfer from {from_account.account_number} - {description}'
            )
            db.session.add_all([withdrawal_tx, deposit_tx, from_account, to_account])
            db.session.commit()
            flash(f'Successfully transferred ${amount:.2f} from {from_account.account_number} to {to_account.account_number}.', 'success')
            return redirect(url_for('dashboard')) 
        
        # If any error occurred before success, re-render the form
        return render_template('transfer_funds.html', accounts=user_accounts, 
                               from_account_id=from_account_id, 
                               to_account_number=to_account_number, 
                               amount=amount, 
                               description=description) # Pass back form values

    return render_template('transfer_funds.html', accounts=user_accounts)

@app.route('/open_account', methods=['GET', 'POST'])
def open_account():
    if 'user_id' not in session:
        flash('Please log in to open a new account.', 'info')
        return redirect(url_for('login'))

    if request.method == 'POST':
        account_type = request.form.get('account_type')
        user_id = session['user_id']

        if not account_type:
            flash('Please select an account type.', 'error')
            return render_template('open_account.html') # Re-render with error

        # For simplicity, let's say a user can have max 2 accounts of each type
        existing_same_type_accounts = Account.query.filter_by(user_id=user_id, account_type=account_type).count()
        if existing_same_type_accounts >= 2:
            flash(f'You already have the maximum number of {account_type} accounts allowed (2).', 'warning')
            return redirect(url_for('dashboard'))
        
        # Basic check: limit total accounts per user (e.g., 5 total)
        total_user_accounts = Account.query.filter_by(user_id=user_id).count()
        if total_user_accounts >= 5:
            flash('You have reached the maximum total number of accounts allowed (5).', 'warning')
            return redirect(url_for('dashboard'))

        new_account_number = generate_account_number()
        # Ensure the generated account number is unique (highly likely, but good practice for a real system)
        while Account.query.filter_by(account_number=new_account_number).first() is not None:
            new_account_number = generate_account_number()

        initial_balance = 0.0 # New accounts start with zero balance
        if account_type == "Savings":
             initial_balance = 50.0 # Small bonus for opening a savings account

        new_acc = Account(
            user_id=user_id,
            account_number=new_account_number,
            account_type=account_type,
            balance=initial_balance 
        )
        db.session.add(new_acc)
        db.session.commit()

        flash(f'New {account_type} account ({new_account_number}) opened successfully with an initial balance of ${initial_balance:.2f}!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('open_account.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Please log in to view your profile.', 'info')
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    if not user:
        flash('User not found. Please log in again.', 'error')
        session.clear()
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_full_name = request.form.get('full_name', '').strip()
        if new_full_name:
            user.full_name = new_full_name
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        else:
            flash('Full name cannot be empty.', 'error')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)

# --- Interest Calculation (Simplified Example) ---
# This would typically be a scheduled task
def apply_interest():
    with app.app_context(): # Ensure we are in application context
        accounts = Account.query.filter(Account.account_type == 'Savings').all()
        interest_rate = 0.01 # 1% annual interest, applied monthly for simplicity
        
        for account in accounts:
            interest_earned = account.balance * (interest_rate / 12) # Monthly interest
            if interest_earned > 0:
                account.balance += interest_earned
                new_transaction = Transaction(
                    account_id=account.id,
                    type='interest',
                    amount=interest_earned,
                    description='Monthly interest accrued'
                )
                db.session.add(new_transaction)
        db.session.commit()
        print("Applied monthly interest to savings accounts.")


if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Create database tables if they don't exist
    
    # For demonstration, let's schedule interest calculation (in a real app, use APScheduler or Celery)
    # import threading
    # def run_interest_job():
    #     import time
    #     while True:
    #         time.sleep(60*60*24*30) # Roughly monthly
    #         apply_interest()
    # if os.environ.get('WERKZEUG_RUN_MAIN') == 'true': # Ensure this runs only once with Flask reloader
    #    interest_thread = threading.Thread(target=run_interest_job)
    #    interest_thread.daemon = True # Allow main program to exit even if thread is running
    #    interest_thread.start()

    app.run(debug=True, port=5001) 