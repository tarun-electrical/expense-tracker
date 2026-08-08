from flask import Flask, render_template, request, url_for, make_response, flash, redirect, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime, date as dt_date
from sqlalchemy import func

# tarun_electrical


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'my-secret-key'

db = SQLAlchemy(app)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False, default=0)




with app.app_context():
    db.create_all()


CATEGORIES = ["Food", "Transport", "Entertainment", "Utilities", "Other"]


def parse_date_or_none(s: str):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


@app.route("/")
def index():

    # 1. Read query string parameters
    start_str = (request.args.get("start") or "").strip()
    end_str = (request.args.get("end") or "").strip()
    selected_category = (request.args.get("category") or "").strip()
    search = (request.args.get("search") or "").strip()

    # 2. Parse the dates
    start_date = parse_date_or_none(start_str)
    end_date = parse_date_or_none(end_str)

    # 3. Validate date range
    if start_date and end_date and end_date < start_date:
        flash("End date cannot be before start date", "error")
        start_date = None
        end_date = None
        start_str = ""
        end_str = ""

    # 4. Start query
    q = Expense.query

    # 5. Apply filters
    if start_date:
        q = q.filter(Expense.date >= start_date)

    if end_date:
        q = q.filter(Expense.date <= end_date)

    if selected_category:
        q = q.filter(Expense.category == selected_category)

    if search:
        q = q.filter(Expense.description.ilike(f"%{search}%"))

    # 6. Fetch expenses
    expenses = q.order_by(
        Expense.date.desc(),
        Expense.id.desc()
    ).all()

    # 7. Calculate total
    total = round(sum(e.amount for e in expenses), 2)

    # Budget
    budget = Budget.query.first()
    budget_amount = budget.amount if budget else 0

    # 8. Monthly analytics
    today_date = date.today()
    month_start = today_date.replace(day=1)

    monthly_q = Expense.query.filter(
        Expense.date >= month_start,
        Expense.date <= today_date
    )

    if start_date:
        monthly_q = monthly_q.filter(Expense.date >= start_date)

    if end_date:
        monthly_q = monthly_q.filter(Expense.date <= end_date)

    if selected_category:
        monthly_q = monthly_q.filter(
            Expense.category == selected_category
        )

    if search:
        monthly_q = monthly_q.filter(
            Expense.description.ilike(f"%{search}%")
        )

    monthly_expenses = monthly_q.all()

    monthly_total = round(
        sum(e.amount for e in monthly_expenses),
        2
    )

    monthly_count = len(monthly_expenses)

    monthly_average = round(
        monthly_total / monthly_count,
        2
    ) if monthly_count else 0

    # Budget calculations
    budget_spent = monthly_total

    budget_remaining = round(
        budget_amount - budget_spent,
        2
    )

    budget_percentage = round(
        (budget_spent / budget_amount) * 100,
        1
    ) if budget_amount > 0 else 0

    # Find top spending category
    monthly_category_totals = {}

    for e in monthly_expenses:
        monthly_category_totals[e.category] = (
            monthly_category_totals.get(e.category, 0) + e.amount
        )

    top_category = (
        max(
            monthly_category_totals,
            key=monthly_category_totals.get
        )
        if monthly_category_totals
        else "N/A"
    )

    # Pie chart
    cat_q = db.session.query(
        Expense.category,
        func.sum(Expense.amount)
    )

    if start_date:
        cat_q = cat_q.filter(Expense.date >= start_date)

    if end_date:
        cat_q = cat_q.filter(Expense.date <= end_date)

    if selected_category:
        cat_q = cat_q.filter(
            Expense.category == selected_category
        )

    if search:
        cat_q = cat_q.filter(
            Expense.description.ilike(f"%{search}%")
        )

    cat_rows = cat_q.group_by(Expense.category).all()

    cat_labels = [c for c, _ in cat_rows]

    cat_values = [
        round(float(s or 0), 2)
        for _, s in cat_rows
    ]

    # Day chart
    day_q = db.session.query(
        Expense.date,
        func.sum(Expense.amount)
    )

    if start_date:
        day_q = day_q.filter(Expense.date >= start_date)

    if end_date:
        day_q = day_q.filter(Expense.date <= end_date)

    if selected_category:
        day_q = day_q.filter(
            Expense.category == selected_category
        )

    if search:
        day_q = day_q.filter(
            Expense.description.ilike(f"%{search}%")
        )

    day_rows = day_q.group_by(
        Expense.date
    ).order_by(
        Expense.date
    ).all()

    day_labels = [
        d.isoformat()
        for d, _ in day_rows
    ]

    day_values = [
        round(float(s or 0), 2)
        for _, s in day_rows
    ]

    # Monthly chart
    month_q = db.session.query(
        func.strftime("%Y-%m", Expense.date),
        func.sum(Expense.amount)
    )

    if start_date:
        month_q = month_q.filter(
            Expense.date >= start_date
        )

    if end_date:
        month_q = month_q.filter(
            Expense.date <= end_date
        )

    if selected_category:
        month_q = month_q.filter(
            Expense.category == selected_category
        )

    if search:
        month_q = month_q.filter(
            Expense.description.ilike(f"%{search}%")
        )

    month_rows = month_q.group_by(
        func.strftime("%Y-%m", Expense.date)
    ).order_by(
        func.strftime("%Y-%m", Expense.date)
    ).all()

    month_labels = [
        m for m, _ in month_rows
    ]

    month_values = [
        round(float(s or 0), 2)
        for _, s in month_rows
    ]

    # 9. Render page
    return render_template(
        "index.html",
        expenses=expenses,
        categories=CATEGORIES,
        today=date.today().isoformat(),
        total=total,

        budget_amount=budget_amount,
        budget_spent=budget_spent,
        budget_remaining=budget_remaining,
        budget_percentage=budget_percentage,

        monthly_total=monthly_total,
        monthly_count=monthly_count,
        monthly_average=monthly_average,
        top_category=top_category,

        start_str=start_str,
        end_str=end_str,
        selected_category=selected_category,
        search=search,

        cat_labels=cat_labels,
        cat_values=cat_values,

        day_labels=day_labels,
        day_values=day_values,

        month_labels=month_labels,
        month_values=month_values,
    )

       

@app.route("/add", methods=['POST'])
def add():

    description = (request.form.get("description") or "").strip()
    amount_str = (request.form.get("amount") or "").strip()
    category = (request.form.get("category") or "").strip()
    date_str = (request.form.get("date") or "").strip()


    if not description or not amount_str or not category:
        flash("Please fill the description, amount, category", "error")
        return redirect(url_for("index"))

    try:
         amount = float(amount_str)
         if amount <= 0:
             raise ValueError

    except ValueError:
        flash("Amount must be a positive number", "error")
        return redirect(url_for("index"))


    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    except ValueError:
        d= date.today()

    e = Expense(description=description, amount=amount, category=category, date=d)
    db.session.add(e)
    db.session.commit()

    flash("Expense added successfully!", "success")
    return redirect(url_for("index"))

@app.route('/delete/<int:expense_id>', methods=['POST'])
def delete(expense_id):
    e = Expense.query.get_or_404(expense_id)
    db.session.delete(e)
    db.session.commit()
    flash("Expense deleted successfully!", "success")
    return redirect(url_for("index"))


@app.route("/budget", methods=["POST"])
def set_budget():
    amount_str = (request.form.get("budget") or "").strip()

    try:
        amount = float(amount_str)

        if amount <= 0:
            raise ValueError

    except ValueError:
        flash("Budget must be a positive number", "error")
        return redirect(url_for("index"))

    budget = Budget.query.first()

    if budget:
        budget.amount = amount
    else:
        budget = Budget(amount=amount)
        db.session.add(budget)

    db.session.commit()

    flash("Monthly budget updated successfully!", "success")
    return redirect(url_for("index"))




@app.route('/edit/<int:expense_id>', methods=['GET'])
def edit(expense_id):
    e = Expense.query.get_or_404(expense_id)

    return render_template(
        "edit.html",
        expense=e,
        categories=CATEGORIES,
        today=dt_date.today().isoformat()
    )



@app.route('/edit/<int:expense_id>', methods=['POST'])
def edit_post(expense_id):
    e = Expense.query.get_or_404(expense_id)

    description = (request.form.get("description") or "").strip()
    amount_str = (request.form.get("amount") or "").strip()
    category = (request.form.get("category") or "").strip()
    date_str = (request.form.get("date") or "").strip()

    if not description or not amount_str or not category:
        flash("Please fill all fields", "error")
        return redirect(url_for("edit", expense_id=expense_id))

    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Amount must be a positive number", "error")
        return redirect(url_for("edit", expense_id=expense_id))

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else dt_date.today()
    except ValueError:
        d = dt_date.today()

    e.description = description
    e.amount = amount
    e.category = category
    e.date = d

    db.session.commit()
    flash("Expense updated successfully!", "success")
    return redirect(url_for("index"))





@app.route("/export.csv")
def export_csv():

    # 1. Read query string parameters
    start_str = (request.args.get("start") or "").strip()
    end_str = (request.args.get("end") or "").strip()
    selected_category = (request.args.get("category") or "").strip()
    search = (request.args.get("search") or "").strip()

    # 2. Parse the dates
    start_date = parse_date_or_none(start_str)
    end_date = parse_date_or_none(end_str)


    # 3. Start query
    q = Expense.query

    # 4. Apply filters
    if start_date:
        q = q.filter(Expense.date >= start_date)

    if end_date:
        q = q.filter(Expense.date <= end_date)

    if selected_category:
         q = q.filter(Expense.category == selected_category)

    if search:
        q = q.filter(Expense.description.ilike(f"%{search}%"))


    # 5. Fetch expenses
    expenses = q.order_by(
        Expense.date,
        Expense.id
    ).all()

    lines = ["description,amount,category,date"]

    for e in expenses:
        lines.append(f"{e.description},{e.amount:.2f},{e.category},{e.date.isoformat()}")
    csv_data = "\n".join(lines)


    fname_start = start_str or "all"
    fname_end = end_str or "all"
    filename = f"expenses_{fname_start}_to_{fname_end}.csv" 


    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Type": "text/csv",
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )















if __name__ == "__main__":
    app.run(debug=True)
