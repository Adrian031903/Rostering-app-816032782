from datetime import date, datetime
from decimal import Decimal
from ..database import db
from ..models.core import User, TimeLog, PayRate, PayrollRun, PayrollLine

def _active_rate(user_id: int, moment: datetime):
    q = PayRate.query.filter(PayRate.user_id == user_id, PayRate.effective_from <= moment)
    q = q.filter((PayRate.effective_to == None) | (PayRate.effective_to >= moment))  # noqa: E711
    return q.order_by(PayRate.effective_from.desc()).first()

def create_payroll_run(period_start_iso: str, period_end_iso: str, generated_by_email: str):
    run = PayrollRun(period_start=date.fromisoformat(period_start_iso),
                     period_end=date.fromisoformat(period_end_iso),
                     generated_by=User.query.filter_by(email=generated_by_email).first().id)
    db.session.add(run); db.session.commit(); return run

def generate_lines(run_id: int):
    run = PayrollRun.query.get(run_id)
    if not run: raise ValueError("Payroll run not found")

    for line in run.lines: db.session.delete(line)
    db.session.commit()

    logs = (TimeLog.query
            .filter(TimeLog.clock_out != None)  # noqa: E711
            .filter(TimeLog.clock_in >= datetime.combine(run.period_start, datetime.min.time()))
            .filter(TimeLog.clock_out <= datetime.combine(run.period_end, datetime.max.time()))
            .all())

    totals = {}
    for tl in logs:
        mins = tl.worked_minutes()
        if mins > 0: totals[tl.user_id] = totals.get(tl.user_id, 0) + mins

    for user_id, minutes in totals.items():
        moment = datetime.combine(run.period_end, datetime.max.time())
        rate = _active_rate(user_id, moment)
        hourly = Decimal(str(rate.hourly_rate)) if rate else Decimal("0.00")
        gross = (Decimal(minutes) / Decimal(60)) * hourly
        db.session.add(PayrollLine(payroll_run_id=run.id, user_id=user_id,
                                   total_minutes=minutes, gross_pay=gross.quantize(Decimal("0.01"))))

    run.status = "approved"; db.session.commit(); return run
