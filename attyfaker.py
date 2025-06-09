import csv
import random
from faker import Faker

fake = Faker()

departments = ["Corporate", "Litigation", "IP", "Pro Bono"]

with open("attorneys.csv", "w", newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["attorney_id", "first_name", "last_name", "email", "department", "bar_admission_date"])
    for i in range(1, 101):
        first = fake.first_name()
        last = fake.last_name()
        email = f"{first.lower()}.{last.lower()}@lawfirm.com"
        dept = random.choice(departments)
        bar_date = fake.date_between(start_date='-15y', end_date='-1y').isoformat()

        # Random error injection: 10% chance of a formatting error
        if random.random() < 0.1:
            error_type = random.choice(['email_invalid', 'email_missing', 'date_invalid'])
            if error_type == 'email_invalid':
                email = email.replace('@', '')  # Invalid email
            elif error_type == 'email_missing':
                email = ''  # Missing email
            elif error_type == 'date_invalid':
                bar_date = 'not_a_date'  # Malformed date

        writer.writerow([i, first, last, email, dept, bar_date])