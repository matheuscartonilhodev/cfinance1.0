from datetime import datetime, date as dt
from calendar import monthrange
from app import db
from app.models import Income, Expense, Card, CardPurchase
from sqlalchemy import extract, func

def add_income(user_id, type_, description, amount, date=None):
    today = dt.today()
    date = today if not date else datetime.strptime(date, '%Y-%m-%d').date()
    
    status = 'Efetivada' if date <= today else 'Pendente'

    new_income = Income(
        user_id=user_id,
        type_=type_,
        description=description,
        amount=amount,
        date=date,
        status=status
    )
    
    db.session.add(new_income)
    db.session.commit()

def add_expense(user_id, type_, description, amount, date=None):
    today = dt.today()
    date = today if not date else datetime.strptime(date, '%Y-%m-%d').date()
    status = 'Efetivada' if date <= today else 'Pendente'

    new_expense = Expense(
        user_id=user_id,
        type_=type_,
        description=description,
        amount=amount,
        date=date,
        status=status
    )
    db.session.add(new_expense)
    db.session.commit()

def list_incomes(user_id, month=None, year=None, type_=None):
    query = Income.query.filter_by(user_id=user_id)
    if month and year:
        query = query.filter(
            extract('month', Income.date) == int(month),
            extract('year', Income.date) == int(year)
        )
    if type_:
        query = query.filter_by(type_=type_)
    return query.order_by(Income.date.desc()).all()

def list_expenses(user_id, month=None, year=None, type_=None):
    query = Expense.query.filter_by(user_id=user_id)
    if month and year:
        query = query.filter(
            extract('month', Expense.date) == int(month),
            extract('year', Expense.date) == int(year)
        )
    if type_:
        query = query.filter_by(type_=type_)
    return query.order_by(Expense.date.desc()).all()

def get_total_income(user_id, month=None, year=None):
    query = db.session.query(func.sum(Income.amount)).filter_by(user_id=user_id)
    if month and year:
        query = query.filter(
            extract('month', Income.date) == int(month),
            extract('year', Income.date) == int(year)
        )
    return query.scalar() or 0.0

def get_total_expense(user_id, month=None, year=None):
    query = db.session.query(func.sum(Expense.amount)).filter_by(user_id=user_id)
    if month and year:
        query = query.filter(
            extract('month', Expense.date) == int(month),
            extract('year', Expense.date) == int(year)
        )
    return query.scalar() or 0.0

def del_income(id):
    income = Income.query.get(id)
    if income:
        db.session.delete(income)
        db.session.commit()

def del_expense(id):
    expense = Expense.query.get(id)
    if expense:
        db.session.delete(expense)
        db.session.commit()

def update_income_db(id, type_, description, amount):
    income = Income.query.get(id)
    if income:
        income.type_ = type_
        income.description = description
        income.amount = amount
        db.session.commit()

def update_expanse_db(id, type_, description, amount):
    expense = Expense.query.get(id)
    if expense:
        expense.type_ = type_
        expense.description = description
        expense.amount = amount
        db.session.commit()

def get_income_by_type(user_id, month=None, year=None):
    query = db.session.query(Income.type_, func.sum(Income.amount)).filter_by(user_id=user_id)
    if month and year:
        query = query.filter(
            extract('month', Income.date) == int(month),
            extract('year', Income.date) == int(year)
        )
    return query.group_by(Income.type_).all()

def get_expense_by_type(user_id, month=None, year=None):
    query = db.session.query(Expense.type_, func.sum(Expense.amount)).filter_by(user_id=user_id)
    if month and year:
        query = query.filter(
            extract('month', Expense.date) == int(month),
            extract('year', Expense.date) == int(year)
        )
    return query.group_by(Expense.type_).all()


def add_card(user_id, name, card_limit, closing_day, due_day):
    new_card = Card(
        user_id=user_id,
        name=name,
        card_limit=card_limit,
        closing_day=closing_day,
        due_day=due_day
    )
    db.session.add(new_card)
    db.session.commit()


def delete_card(card_id):
    card = Card.query.get(card_id)
    if card:
        db.session.delete(card)
        db.session.commit()


def get_cards(user_id):
    return Card.query.filter_by(user_id=user_id).all()


def add_card_purchase(card_id, user_id, description, total_amount, installments, purchase_date=None):
    purchase_date = datetime.now().date() if not purchase_date else datetime.strptime(purchase_date, '%Y-%m-%d').date()
    
    card = Card.query.get(card_id)
    if not card:
        raise ValueError("Cartão não encontrado")

    new_purchase = CardPurchase(
        card_id=card_id,
        user_id=user_id,
        description=description,
        total_amount=total_amount,
        installments=installments,
        purchase_date=purchase_date
    )
    db.session.add(new_purchase)

    parcela_valor = round(total_amount / installments, 2)
    tipo = f"Cartão: {card.name}"

    if purchase_date.day > card.closing_day:
        start_month = purchase_date.month + 1
        start_year = purchase_date.year + (1 if start_month > 12 else 0)
        start_month = (start_month - 1) % 12 + 1
    else:
        start_month = purchase_date.month
        start_year = purchase_date.year

    for i in range(installments):
        parcela_month = start_month + i
        parcela_year = start_year + (parcela_month - 1) // 12
        parcela_month = (parcela_month - 1) % 12 + 1
        dia_valido = min(card.due_day, monthrange(parcela_year, parcela_month)[1])
        parcela_data = datetime(parcela_year, parcela_month, dia_valido).date()
        status = 'Efetivada' if parcela_data <= datetime.today().date() else 'Pendente'

        new_expense = Expense(
            user_id=user_id,
            type_=tipo,
            amount=parcela_valor,
            description=f"{description} (parcela {i+1}/{installments})",
            date=parcela_data,
            status=status
        )
        db.session.add(new_expense)

    db.session.commit()
