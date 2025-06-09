import csv
import random
from faker import Faker

fake = Faker()

statuses = ["open", "closed", "pending"]

with open("pro_bono_cases.csv", "w", newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["case_id", "attorney_id", "title", "status", "start_date", "closed_date"])
    for i in range(1001, 1101):
        attorney_id = random.randint(1, 100)
        title = fake.sentence(nb_words=4).rstrip('.')
        status = random.choice(statuses)
        start = fake.date_between(start_date='-3y', end_date='today')
        start_date = start.isoformat()

        # Randomly inject foreign key or data issues
        if random.random() < 0.1:
            error_type = random.choice(['invalid_attorney', 'bad_status', 'bad_date'])
            if error_type == 'invalid_attorney':
                attorney_id = random.randint(101, 120)  # invalid FK
            elif error_type == 'bad_status':
                status = 'archived'  # not in allowed status list
            elif error_type == 'bad_date':
                start_date = 'not_a_date'

        closed_date = ""
        if status == "closed":
            closed_date = fake.date_between(start_date=start, end_date='today').isoformat()
        writer.writerow([i, attorney_id, title, status, start_date, closed_date])