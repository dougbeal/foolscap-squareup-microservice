from datetime import datetime, timedelta

def event_month():
    return 2

# before/during feburary 2020
#  2019
#  2020
#  2021
# after

def years():
    now = datetime.now()
    current = now.year
    if now.month > event_month():
        current = current+1
    return list(range(current, current+2))

def active():
    # current year event is no longer active when March is reached

    # in year 2019, active events could be:
    #  foolscap-2019
    #  foolscap-2020
    #  foolscap-2021
    return [f"foolscap-{year}" for year in years()]

def earliest_order_date():
    now = datetime.now()
    year = now.year
    if not now.month > event_month():
        year = year-1
    return datetime(day=1, month=1, year=year)-timedelta(days=1)

def square_foolscap_date_range(foolscap_year):
    return (membership_order_start_date(foolscap_year),
            membership_order_end_date(foolscap_year))
            

def membership_order_start_date(foolscap_year):
    # presales at previous con
    return datetime(day=1, month=event_month(), year=foolscap_year)-timedelta(days=400)

def membership_order_end_date(foolscap_year):
    # presales at previous con
    return datetime(day=1, month=event_month(), year=foolscap_year)+timedelta(days=32)
    

def square_item_year_prefix_to_event(name):
    for idx, year in enumerate(years()):
        prefix = f"F{str(year%100).zfill(2)}"
        if name.startswith(prefix):
            return active()[idx]
    return None
