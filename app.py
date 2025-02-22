from flask import Flask, render_template, request, Response, url_for
import csv
import io

app = Flask(__name__)

def calculate_amortization_schedule(principal, annual_rate, years, extra_emis, step_up_percent):
    """
    Calculate the amortization schedule for a loan with extra EMI payments,
    an annual EMI step-up, and track cumulative interest paid.
    """
    monthly_rate = annual_rate / 100 / 12
    total_payments = years * 12
    initial_emi = principal * monthly_rate * (1 + monthly_rate) ** total_payments / ((1 + monthly_rate) ** total_payments - 1)
    
    schedule = []
    balance = principal
    month = 1
    current_emi = initial_emi
    cumulative_interest = 0.0

    while balance > 0:
        # Increase the EMI at the start of every new year (after the first year).
        if month > 1 and (month - 1) % 12 == 0:
            current_emi *= (1 + step_up_percent / 100)

        interest_payment = balance * monthly_rate
        cumulative_interest += interest_payment

        regular_principal_payment = current_emi - interest_payment
        if regular_principal_payment > balance:
            regular_principal_payment = balance
            regular_payment = interest_payment + balance
        else:
            regular_payment = current_emi

        balance -= regular_principal_payment

        extra_payment = 0
        # Apply extra EMI in the first 'extra_emis' months of each year.
        if extra_emis > 0 and ((month - 1) % 12) < extra_emis and balance > 0:
            extra_payment = current_emi
            if extra_payment > balance:
                extra_payment = balance
            balance -= extra_payment

        total_payment = regular_payment + extra_payment
        total_principal = regular_principal_payment + extra_payment

        schedule.append({
            'Month': month,
            'Payment': round(total_payment, 2),
            'Regular Payment': round(current_emi, 2),
            'Extra Payment': round(extra_payment, 2),
            'Interest': round(interest_payment, 2),
            'Cumulative Interest': round(cumulative_interest, 2),
            'Principal': round(total_principal, 2),
            'Balance': round(balance, 2)
        })
        month += 1

    return schedule

# Jinja filter for formatting numbers with commas.
def format_number(value):
    try:
        # If the value is an integer, no decimals
        if isinstance(value, int):
            return "{:,}".format(value)
        # Otherwise, format as a float with 2 decimal places
        return "{:,.2f}".format(float(value))
    except Exception:
        return value

app.jinja_env.filters['commas'] = format_number

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Retrieve form data.
        principal = float(request.form["principal"])
        annual_rate = float(request.form["annual_rate"])
        years = int(request.form["years"])
        extra_emis = int(request.form["extra_emis"])
        step_up_percent = float(request.form["step_up_percent"])

        # Calculate the revised schedule.
        schedule = calculate_amortization_schedule(principal, annual_rate, years, extra_emis, step_up_percent)
        
        # Calculate the baseline schedule (no extra EMIs, no step-ups).
        baseline_schedule = calculate_amortization_schedule(principal, annual_rate, years, extra_emis=0, step_up_percent=0)
        
        revised_tenure = schedule[-1]['Month']
        revised_interest = schedule[-1]['Cumulative Interest']
        baseline_tenure = baseline_schedule[-1]['Month']
        baseline_interest = baseline_schedule[-1]['Cumulative Interest']
        
        # Convert months to years (rounded down) for display.
        baseline_years = baseline_tenure // 12
        revised_years = revised_tenure // 12

        tenure_reduction = baseline_tenure - revised_tenure
        interest_saved = baseline_interest - revised_interest
        
        return render_template(
            "result.html",
            schedule=schedule,
            principal=principal,
            annual_rate=annual_rate,
            years=years,
            extra_emis=extra_emis,
            step_up_percent=step_up_percent,
            baseline_tenure=baseline_tenure,
            revised_tenure=revised_tenure,
            baseline_years=baseline_years,
            revised_years=revised_years,
            tenure_reduction=tenure_reduction,
            baseline_interest=baseline_interest,
            revised_interest=revised_interest,
            interest_saved=interest_saved
        )
    return render_template("index.html")

@app.route("/download")
def download_csv():
    try:
        principal = float(request.args.get("principal"))
        annual_rate = float(request.args.get("annual_rate"))
        years = int(request.args.get("years"))
        extra_emis = int(request.args.get("extra_emis"))
        step_up_percent = float(request.args.get("step_up_percent"))
    except (TypeError, ValueError):
        return "Invalid parameters", 400

    schedule = calculate_amortization_schedule(principal, annual_rate, years, extra_emis, step_up_percent)
    
    si = io.StringIO()
    writer = csv.DictWriter(si, fieldnames=['Month', 'Payment', 'Regular Payment', 'Extra Payment', 'Interest', 'Cumulative Interest', 'Principal', 'Balance'])
    writer.writeheader()
    for row in schedule:
        writer.writerow(row)
    
    output = si.getvalue()
    return Response(output,
                    mimetype="text/csv",
                    headers={"Content-disposition": "attachment; filename=amortization_schedule.csv"})

if __name__ == "__main__":
    app.run(debug=True)
