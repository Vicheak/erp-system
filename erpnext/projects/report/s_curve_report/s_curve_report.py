# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from datetime import date

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    return columns, data, None, chart

def get_columns():
    return [
        {"label": "ID", "fieldname": "name", "fieldtype": "Link", "options": "Task", "width": 120},
        {"label": "Subject", "fieldname": "subject", "fieldtype": "Data", "width": 180},
        {"label": "Weight", "fieldname": "task_weight", "fieldtype": "Float", "width": 100},
        {"label": "Expected Start Date", "fieldname": "exp_start_date", "fieldtype": "Date", "width": 120},
        {"label": "Expected End Date", "fieldname": "exp_end_date", "fieldtype": "Date", "width": 120},
        {"label": "Started On", "fieldname": "custom_started_on", "fieldtype": "Date", "width": 120},
        {"label": "Completed On", "fieldname": "completed_on", "fieldtype": "Date", "width": 120},
        {"label": "Actual % Progress", "fieldname": "progress", "fieldtype": "Percent", "width": 120}
    ]

def get_data(filters):
    tasks = frappe.get_all(
        "Task",
        fields=[
            "name",
            "subject",
            "task_weight",
            "exp_start_date",
            "exp_end_date",
            "custom_started_on",
            "completed_on",
            "progress"
        ],
        filters=filters,
        order_by="exp_end_date asc"
    )
    return tasks

def safe_date(val):
    # if None, return far future so task goes to the end
    return val or date.max

def calculate_s_curve(tasks):
    print("="*20)
    print("tasks:", tasks)
    print("="*20)

    total_weight = sum([t.task_weight or 0 for t in tasks if t.task_weight]) or 1

    print("="*20)
    print("total_weight:", total_weight)
    print("="*20)

    # --- Planned Progress (by expected end date)
    planned_curve = []
    cumulative_planned = 0
    for t in sorted(tasks, key=lambda x: safe_date(x.expected_end_date or x.expected_start_date)):
        print("for task:", t)
        cumulative_planned += (t.task_weight or 0)
        planned_curve.append(round(cumulative_planned / total_weight * 100, 2))
        print("cumulative_planned:", cumulative_planned)

    print("*="*20)
    print("planned_curve y-axis:", planned_curve)
    print("*="*20)

    # --- Actual Progress (by completed date)
    actual_curve = []
    cumulative_actual = 0
    for t in sorted(tasks, key=lambda x: safe_date(x.completed_on or x.expected_end_date)):
        print("for task:", t)
        w = (t.task_weight or 0) * (t.progress or 0) / 100
        cumulative_actual += w
        actual_curve.append(round(cumulative_actual / total_weight * 100, 2))
        print("cumulative_actual:", cumulative_actual)

    print("*="*20)
    print("actual_curve y-axis:", actual_curve)
    print("*="*20)

    # labels (milestones = subjects)
    labels = [t.subject for t in sorted(tasks, key=lambda x: safe_date(x.expected_end_date or x.completed_on))]

    print("="*20)
    print("labels x-axis:", labels)
    print("="*20)

    return labels, planned_curve, actual_curve

def get_chart(tasks):
    labels, planned, actual = calculate_s_curve(tasks)
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Planned Progress", "values": planned},
                {"name": "Actual Progress", "values": actual}
            ]
        },
        "type": "line",
        "colors": ["#5e64ff", "#ff5858"],
        "lineOptions": {"regionFill": 0}
    }
