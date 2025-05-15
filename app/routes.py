from app import app, db, mail
from flask import render_template, request, redirect, session, flash, Response
from app.services import (
    add_income, list_incomes, get_total_income, del_income, update_income_db, get_income_by_type,
    add_expense, list_expenses, get_total_expense, del_expense, update_expanse_db, get_expense_by_type,
    add_card, get_cards, delete_card, add_card_purchase
)
from app.models import User, Income, Expense, PasswordResetToken
from werkzeug.security import generate_password_hash, check_password_hash
import io
import xlsxwriter
from datetime import datetime
from flask_mail import Message
import secrets
from datetime import datetime, timedelta

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    month = request.args.get('month')
    year = request.args.get('year')
    
    if not month or not year:
        today = datetime.now()
        month = today.strftime('%m')
        year = today.strftime('%Y')

    total_income = get_total_income(user_id, month, year)
    total_expense = get_total_expense(user_id, month, year)
    balance = total_income - total_expense

    income_by_type = get_income_by_type(user_id, month, year)
    expense_by_type = get_expense_by_type(user_id, month, year)

    incomes_labels = []
    incomes_values = []

    for row in income_by_type:
        if row and len(row) >= 2:
            incomes_labels.append(row[0])
            incomes_values.append(row[1])

    expenses_labels = []
    expenses_values = []

    for row in expense_by_type:
        if row and len(row) >= 2:
            expenses_labels.append(row[0])
            expenses_values.append(row[1])



    return render_template('index.html', total_expense=total_expense, total_income=total_income, balance=balance, incomes_labels=incomes_labels, incomes_values=incomes_values, expenses_labels=expenses_labels, expenses_values=expenses_values, month=month, year=year)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        hashed_password = generate_password_hash(request.form['password'])

        try:
            user = User(name=name, email=email, password=hashed_password)
            db.session.add(user)
            db.session.commit()
            flash('Cadastro realizado com sucesso!', 'success')
            return redirect('/login')
        except:
            flash('Este e-mail já está cadastrado.', 'danger')
            return redirect('/register')
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            return redirect('/incomes')
        else:
            flash('Credenciais inválidas!', 'danger')
            return redirect('/login')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu da conta', 'info')
    return redirect('/login')

@app.route('/incomes', methods=['GET', 'POST'])
def incomes():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']

    if request.method == 'POST':
        description = request.form['description']
        amount = float(request.form['amount'])
        type_ = request.form['type_']
        date = request.form.get('date') or None
        is_recurring = 'recurring' in request.form
        
        add_income(user_id, type_, description, amount, date, is_recurring)
        return redirect('/incomes')
    
    month = request.args.get('month')
    year = request.args.get('year')
    type_ = request.args.get('type_')

    if not month or not year:
        today = datetime.now()
        month = today.strftime('%m')
        year = today.strftime('%Y')

    incomes_list = list_incomes(user_id, month, year, type_)
    return render_template('incomes.html', incomes=incomes_list, month=month, year=year, type_=type_)

@app.route('/expenses', methods=['GET', 'POST'])
def expenses():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']

    if request.method == 'POST':
        description = request.form['description']
        amount = float(request.form['amount'])
        type_ = request.form['type_']
        date = request.form.get('date') or None
        is_recurring = 'recurring' in request.form
        
        add_expense(user_id, type_, description, amount, date, is_recurring)
        return redirect('/expenses')
    
    month = request.args.get('month')
    year = request.args.get('year')
    type_ = request.args.get('type_')

    if not month or not year:
        today = datetime.now()
        month = today.strftime('%m')
        year = today.strftime('%Y')
    
    expenses_list = list_expenses(user_id, month, year, type_)
    return render_template('expenses.html', expenses=expenses_list, month=month, year=year, type_=type_)


@app.route('/cards', methods=['GET','POST'])
def cards():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']

    if request.method == 'POST':
        name = request.form['name']
        card_limit = float(request.form['card_limit'])
        closing_day = int(request.form['closing_day'])
        due_day = int(request.form['due_day'])

        add_card(user_id, name, card_limit, closing_day, due_day)
        flash('Cartão cadastrado com sucesso!', 'success')
        return redirect('/cards')
    cards_list = get_cards(user_id)
    return render_template('cards.html', cards=cards_list)

@app.route('/del_income/<int:id>', methods=['POST'])
def delete_income(id):
    del_income(id)
    flash('Receita deletada', 'info')
    return redirect('/incomes')

@app.route('/del_expense/<int:id>', methods=['POST'])
def delete_expense(id):
    del_expense(id)
    flash('Despesa deletada', 'info')
    return redirect('/expenses')

@app.route('/update_income/<int:id>', methods=['POST'])
def update_income(id):
    type_ = request.form['type_']
    description = request.form['description']
    amount_str = request.form['amount']

    if not amount_str:
        flash('O valor não pode estar vazio.', 'danger')
        return redirect('/incomes')

    try:
        amount = float(amount_str)
    except ValueError:
        flash('Valor inválido para o campo de valor.', 'danger')
        return redirect('/incomes')

    update_income_db(id, type_, description, amount)
    flash('Receita atualizada com sucesso!', 'success')
    return redirect('/incomes')


@app.route('/update_expense/<int:id>', methods=['POST'])
def update_expense(id):
    type_ = request.form['type_']
    description = request.form['description']
    amount_str = request.form['amount']

    if not amount_str:
        flash('O valor não pode estar vazio.', 'danger')
        return redirect('/expenses')

    try:
        amount = float(amount_str)
    except ValueError:
        flash('Valor inválido para o campo de valor.', 'danger')
        return redirect('/expenses')

    update_expanse_db(id, type_, description, amount)
    flash('Despesa atualizada com sucesso!', 'success')
    return redirect('/expenses')
    
@app.route('/export/incomes')
def export_incomes():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    incomes = list_incomes(user_id)

    export_format = request.args.get('format', 'csv')

    if export_format == 'xlsx':
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()

        headers = ['ID', 'User ID', 'Tipo', 'Valor', 'Descrição', 'Data']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        for row, income, in enumerate(incomes, start=1):
            worksheet.write(row, 0, income.id)
            worksheet.write(row, 1, income.user_id)
            worksheet.write(row, 2, income.type_)
            worksheet.write(row, 3, income.amount)
            worksheet.write(row, 4, income.description)
            worksheet.write(row, 5, income.date.strftime('%Y-%m-%d'))

        
        workbook.close()
        output.seek(0)

        return Response(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers ={
                'Content-Disposition': 'attachment; filename=incomes.xlsx'
            }
        )
    
    else:
        def generate():
            yield f"{income.id},{income.type_},{income.amount},{income.description},{income.date.strftime('%Y-%m-%d')}\n"
            for income in incomes:
                yield f"{income[0]},{income[2]},{income[3]},{income[4]},{income[5]}\n"

        return Response(
            generate(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=incomes.csv'}
        )

@app.route('/export/expenses')
def export_expenses():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    expenses = list_expenses(user_id)

    export_format = request.args.get('format', 'csv')

    if export_format == 'xlsx':
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()

        headers = ['ID', 'User ID', 'Tipo', 'Valor', 'Descrição', 'Data']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        for row, expense, in enumerate(expenses, start=1):
            worksheet.write(row, 0, expense.id)
            worksheet.write(row, 1, expense.user_id)
            worksheet.write(row, 2, expense.type_)
            worksheet.write(row, 3, expense.amount)
            worksheet.write(row, 4, expense.description)
            worksheet.write(row, 5, expense.date.strftime('%Y-%m-%d'))
        
        workbook.close()
        output.seek(0)

        return Response(
            output,
            mimetype='application/vnd.openxmlformats-officeddocument.spreadsheetml.sheet',
            headers ={
                'Content-Disposition': 'attachment; filename=expenses.xlsx'
            }
        )
    
    else:
        def generate():
            yield f"{expense.id},{expense.type_},{expense.amount},{expense.description},{expense.date.strftime('%Y-%m-%d')}\n"
            for expense in expenses:
                yield f"{expense[0]},{expense[2]},{expense[3]},{expense[4]},{expense[5]}\n"

        return Response(
            generate(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=expense.csv'}
        )

@app.route('/toggle_status_expense/<int:id>', methods=['POST'])
def toggle_status_expense(id):
    expense = Expense.query.get(id)
    if expense:
        expense.status = 'Efetivada' if expense.status == 'Pendente' else 'Pendente'
        db.session.commit()
    return redirect('/expenses')


@app.route('/toggle_status_income/<int:id>', methods=['POST'])
def toggle_status_income(id):
    income = Income.query.get(id)
    if income:
        income.status = 'Efetivada' if income.status == 'Pendente' else 'Pendente'
        db.session.commit()
    return redirect('/incomes')

@app.route('/delete_card/<int:card_id>', methods=['POST'])
def delete_card_route(card_id):
    delete_card(card_id)
    flash('Cartão deletado com sucesso!', 'info')
    return redirect('/cards')

@app.route('/card_purchases', methods=['GET', 'POST'])
def card_purchases():
    if 'user_id' not in session:
        return redirect('/login')
    cards = get_cards(session['user_id'])
    if request.method == 'POST':
        card_id = int(request.form['card_id'])
        description = request.form['description']
        total_amount = float(request.form['total_amount'])
        installments = int(request.form['installments'])
        purchase_date = request.form['purchase_date'] or None

        try:
            add_card_purchase(card_id, session['user_id'], description, total_amount, installments, purchase_date)
            flash('Compra parcelada registrada com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao registrar compra: {str(e)}', 'danger')

        return redirect('/card_purchases')
    
    return render_template('card_purchases.html', cards=cards)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = secrets.token_urlsafe(32)
            expiration = datetime.utcnow() + timedelta(hours=1)
            
            reset = PasswordResetToken(user_id=user.id, token=token, expiration=expiration)
            db.session.add(reset)
            db.session.commit()
            
            link = f'{request.host_url}reset-password/{token}'
            msg = Message('Redefinir sua senha', recipients=[user.email])
            msg.body = f'Olá {user.name}, \n\nClique no link abaixo para redefinir sua senha: \n{link}\n\nEste link expira em 1 hora.'
            mail.send(msg)
        flash('Se o email estiver cadastrado, um link foi enviado.', 'info')
        return redirect('/login')
    return render_template('forgot-password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset_token = PasswordResetToken.query.filter_by(token=token).first()

    if not reset_token or reset_token.expiration < datetime.utcnow():
        flash("Link inválido ou expirado.", "danger")
        return redirect('/forgot-password')

    if request.method == 'POST':
        new_password = request.form['password']
        user = reset_token.user
        user.password = generate_password_hash(new_password)
        db.session.delete(reset_token)
        db.session.commit()
        flash("Senha redefinida com sucesso!", "success")
        return redirect('/login')

    return render_template("reset_password.html")

