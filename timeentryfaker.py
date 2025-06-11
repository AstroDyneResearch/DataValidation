import csv
import random
from faker import Faker

fake = Faker()

with open("time_entries.csv", "w", newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["entry_id", "case_id", "attorney_id", "hours", "date"])
    for i in range(5001, 5101):
        case_id = random.randint(1001, 1100)
        attorney_id = random.randint(1, 100)
        hours = round(random.uniform(0.5, 8.0), 2)
        date = fake.date_between(start_date='-2y', end_date='today').isoformat()
        # Randomly inject foreign key and data errors
        if random.random() < 0.1:
            error_type = random.choice(['bad_case_id', 'bad_attorney_id', 'bad_hours', 'bad_date'])
            if error_type == 'bad_case_id':
                case_id = random.randint(1101, 1200)  # FK violation
            elif error_type == 'bad_attorney_id':
                attorney_id = random.randint(101, 120)  # FK violation
            elif error_type == 'bad_hours':
                hours = "not_a_number"
            elif error_type == 'bad_date':
                date = "not_a_date"
        writer.writerow([i, case_id, attorney_id, hours, date])