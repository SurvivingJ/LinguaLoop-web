import json
from datetime import datetime


def _parse_plan(row):
    if not row:
        return None
    return {
        'id': int(row.get('id', 0)),
        'week_start': row.get('week_start', ''),
        'plan_data': json.loads(row['plan_data']) if row.get('plan_data') else {},
        'total_cost': float(row['total_cost']) if row.get('total_cost') else 0,
        'macro_summary': json.loads(row['macro_summary']) if row.get('macro_summary') else {},
        'shopping_list': json.loads(row['shopping_list']) if row.get('shopping_list') else {},
        'savings_from_offers': float(row.get('savings_from_offers', 0)),
        'accepted': row.get('accepted', 'False') == 'True',
        'created_at': row.get('created_at', ''),
    }


def get_current_plan(store):
    rows = store.read_all('meal_plans')
    if not rows:
        return None
    # Return most recent accepted plan, or most recent overall
    accepted = [r for r in rows if r.get('accepted', 'False') == 'True']
    if accepted:
        accepted.sort(key=lambda r: r.get('created_at', ''), reverse=True)
        return _parse_plan(accepted[0])
    rows.sort(key=lambda r: r.get('created_at', ''), reverse=True)
    return _parse_plan(rows[0])


def get_plan_for_week(store, week_start):
    results = store.query('meal_plans', week_start=str(week_start))
    return _parse_plan(results[0]) if results else None


def save_plan(store, plan_data):
    row = {
        'id': str(store.next_id('meal_plans')),
        'week_start': plan_data.get('week_start', ''),
        'plan_data': json.dumps(plan_data.get('plan_data', {})),
        'total_cost': str(plan_data.get('total_cost', 0)),
        'macro_summary': json.dumps(plan_data.get('macro_summary', {})),
        'shopping_list': json.dumps(plan_data.get('shopping_list', {})),
        'savings_from_offers': str(plan_data.get('savings_from_offers', 0)),
        'accepted': 'False',
        'created_at': datetime.now().isoformat(),
    }
    store.append_row('meal_plans', row)
    return _parse_plan(row)


def accept_plan(store, plan_id):
    rows = store.read_all('meal_plans')
    for r in rows:
        if r.get('id') == str(plan_id):
            r['accepted'] = 'True'
    store.write_all('meal_plans', rows)
