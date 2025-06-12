import pandas as pd
import logging
import csv
from datetime import datetime
import yaml
from math import isnan
from pydantic import BaseModel, EmailStr, ValidationError
try:
    from pydantic import field_validator
except ImportError:
    # For Pydantic v1 fallback (should not happen for v2)
    field_validator = None

# CaseModel for validating pro_bono_cases rows

# --- Begin updated validation models ---

class BaseValidatorModel(BaseModel):
    @staticmethod
    def parse_date_field(v, field_name="date"):
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            raise ValueError(f"Expected string for {field_name} but got {type(v).__name__}")
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError(f"Invalid {field_name} format (expected YYYY-MM-DD)")


class CaseModel(BaseValidatorModel):
    case_id: int
    attorney_id: int
    title: str
    status: str
    start_date: str
    closed_date: str

    @field_validator("start_date", "closed_date", mode="after")
    @classmethod
    def validate_date_format(cls, v, info):
        return cls.parse_date_field(v, field_name=info.field_name)

    @field_validator("status")
    @classmethod
    def validate_status_enum(cls, v):
        allowed = {"open", "closed", "pending"}
        if v not in allowed:
            raise ValueError(f"Invalid status '{v}', must be one of {allowed}")
        return v


class AttorneyModel(BaseValidatorModel):
    attorney_id: int
    first_name: str
    last_name: str
    email: EmailStr
    department: str
    bar_admission_date: str

    @field_validator("bar_admission_date", mode="after")
    @classmethod
    def validate_date_format(cls, v, info):
        return cls.parse_date_field(v, field_name=info.field_name)


class TimeEntryModel(BaseValidatorModel):
    entry_id: int
    case_id: int
    attorney_id: int
    hours: float
    date: str

    @field_validator("date", mode="after")
    @classmethod
    def validate_date_format(cls, v, info):
        return cls.parse_date_field(v, field_name=info.field_name)

    @field_validator("hours")
    @classmethod
    def validate_hours(cls, v):
        if isinstance(v, str):
            try:
                v = float(v)
            except ValueError:
                raise ValueError("hours must be a float")
        if v < 0:
            raise ValueError("hours cannot be negative")
        return v

# --- End updated validation models ---

logging.basicConfig(
    filename='validation.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DataValidator:
    def __init__(self, attorneys_file, cases_file, time_entries_file, schema_file="schema.yaml"):
        self.attorneys_file = attorneys_file
        self.cases_file = cases_file
        self.time_entries_file = time_entries_file
        self.attorneys_df = None
        self.cases_df = None
        self.time_entries_df = None
        self.error_details = []  # For collecting error messages

        self.df_name_map = {
            "attorneys": "attorneys_df",
            "pro_bono_cases": "cases_df",
            "time_entries": "time_entries_df"
        }

        # Load schema from external YAML
        try:
            with open(schema_file, 'r') as f:
                self.schema = yaml.safe_load(f)
        except Exception as e:
            msg = f"Failed to load schema file {schema_file}: {e}"
            print(msg)
            self.schema = {}
            self.error_details.append(msg)

    def load_data(self):
        try:
            self.attorneys_df = pd.read_csv(self.attorneys_file)
            self.cases_df = pd.read_csv(self.cases_file)
            self.time_entries_df = pd.read_csv(self.time_entries_file)
            print("Files loaded successfully.")
            logging.info("Files loaded successfully.")
        except Exception as e:
            msg = f"Failed to load files: {e}"
            print(msg)
            logging.error(msg)
            self.error_details.append(msg)

    def check_required_columns(self):
        expected_attorneys = {"attorney_id", "first_name", "last_name", "email", "department", "bar_admission_date"}
        expected_cases = {"case_id", "attorney_id", "title", "status", "start_date", "closed_date"}
        expected_time_entries = {"entry_id", "case_id", "attorney_id", "hours", "date"}

        missing_attorneys = expected_attorneys - set(self.attorneys_df.columns)
        missing_cases = expected_cases - set(self.cases_df.columns)
        missing_time_entries = expected_time_entries - set(self.time_entries_df.columns)

        if missing_attorneys:
            msg = f"Missing columns in attorneys file: {missing_attorneys}"
            print(msg)
            self.error_details.append(msg)
        if missing_cases:
            msg = f"Missing columns in cases file: {missing_cases}"
            print(msg)
            self.error_details.append(msg)
        if missing_time_entries:
            msg = f"Missing columns in time_entries file: {missing_time_entries}"
            print(msg)
            self.error_details.append(msg)
        if not missing_attorneys and not missing_cases and not missing_time_entries:
            msg = "All expected columns are present."
            print(msg)
            self.error_details.append(msg)

    def validate_data_integrity(self):
        # Null check
        print("\n🔎 Checking for null values...")
        print(self.attorneys_df.isnull().sum())
        print(self.cases_df.isnull().sum())
        print(self.time_entries_df.isnull().sum())

        # We won't add null counts to error_details, but you could if you want

        # Duplicate IDs
        if self.attorneys_df['attorney_id'].duplicated().any():
            msg = "Duplicate attorney_id values found in attorneys file"
            print(msg)
            self.error_details.append(msg)
        else:
            msg = "No duplicate attorney_id values."
            print(msg)
            self.error_details.append(msg)

        # Foreign key check
        print("\n🔗 Verifying attorney_id in cases file exists in attorneys file...")
        case_fk = self.schema["pro_bono_cases"]["foreign_keys"]["attorney_id"]
        ref_df_name, ref_col = case_fk.split('.')
        ref_df = getattr(self, self.df_name_map[ref_df_name])
        invalid_attorney_ids_cases = set(self.cases_df['attorney_id']) - set(ref_df[ref_col])
        if invalid_attorney_ids_cases:
            msg = f"Foreign key mismatch: {len(invalid_attorney_ids_cases)} unknown attorney_id(s) found in cases file."
            print(msg)
            self.error_details.append(msg)
            for idx in self.cases_df.index:
                if self.cases_df.at[idx, 'attorney_id'] in invalid_attorney_ids_cases:
                    detail_msg = f"❌ Unknown attorney_id in cases file at row {idx+2}: value = {self.cases_df.at[idx, 'attorney_id']}"
                    print(detail_msg)
                    self.error_details.append(detail_msg)
        else:
            msg = "All attorney_id values in cases file match attorneys file."
            print(msg)
            self.error_details.append(msg)

        print("\n🔗 Verifying case_id and attorney_id in time_entries file exist in cases and attorneys files...")
        te_case_fk = self.schema["time_entries"]["foreign_keys"]["case_id"]
        te_att_fk = self.schema["time_entries"]["foreign_keys"]["attorney_id"]

        te_case_df = getattr(self, self.df_name_map[te_case_fk.split('.')[0]])
        te_att_df = getattr(self, self.df_name_map[te_att_fk.split('.')[0]])

        invalid_case_ids = set(self.time_entries_df['case_id']) - set(te_case_df[te_case_fk.split('.')[1]])
        invalid_attorney_ids_time_entries = set(self.time_entries_df['attorney_id']) - set(te_att_df[te_att_fk.split('.')[1]])
        if invalid_case_ids:
            msg = f"Foreign key mismatch: {len(invalid_case_ids)} unknown case_id(s) found in time_entries file."
            print(msg)
            self.error_details.append(msg)
            for idx in self.time_entries_df.index:
                if self.time_entries_df.at[idx, 'case_id'] in invalid_case_ids:
                    detail_msg = f"❌ Unknown case_id in time_entries file at row {idx+2}: value = {self.time_entries_df.at[idx, 'case_id']}"
                    print(detail_msg)
                    self.error_details.append(detail_msg)
        if invalid_attorney_ids_time_entries:
            msg = f"Foreign key mismatch: {len(invalid_attorney_ids_time_entries)} unknown attorney_id(s) found in time_entries file."
            print(msg)
            self.error_details.append(msg)
            for idx in self.time_entries_df.index:
                if self.time_entries_df.at[idx, 'attorney_id'] in invalid_attorney_ids_time_entries:
                    detail_msg = f"❌ Unknown attorney_id in time_entries file at row {idx+2}: value = {self.time_entries_df.at[idx, 'attorney_id']}"
                    print(detail_msg)
                    self.error_details.append(detail_msg)
        if not invalid_case_ids and not invalid_attorney_ids_time_entries:
            msg = "All case_id and attorney_id values in time_entries file match cases and attorneys files."
            print(msg)
            self.error_details.append(msg)

        self.export_validation_report()

    def validate_formats_and_values(self):
        print("\n🔍 Validating column formats and allowed values...")

        # Email format check
        if 'email' in self.attorneys_df.columns:
            invalid_emails = self.attorneys_df[~self.attorneys_df['email'].str.contains(r"^[\w\.-]+@[\w\.-]+\.\w+$", na=False)]
            if not invalid_emails.empty:
                msg = f"❌ Invalid email format(s) found: {len(invalid_emails)} row(s)"
                print(msg)
                self.error_details.append(msg)
                for i, row in invalid_emails.iterrows():
                    val = row['email']
                    self.error_details.append(f"❌ Invalid email at row {i+2}: value = {val}")
            else:
                msg = "✅ All emails are correctly formatted."
                print(msg)
                self.error_details.append(msg)

        # Row-level Pydantic validation for attorneys_df
        for i, row in self.attorneys_df.iterrows():
            try:
                AttorneyModel(**row.to_dict())
            except ValidationError as e:
                self.error_details.append(f"❌ Row {i+2} failed Pydantic validation:")
                for err in e.errors():
                    self.error_details.append(f"   - {err['loc'][0]}: {err['msg']}")

        # Date format check for bar_admission_date in attorneys_df
        if 'bar_admission_date' in self.attorneys_df.columns:
            parsed_dates = pd.to_datetime(self.attorneys_df['bar_admission_date'], errors='coerce')
            invalid_dates = self.attorneys_df[parsed_dates.isna() & self.attorneys_df['bar_admission_date'].notna()]
            if not invalid_dates.empty:
                msg = f"❌ Invalid date format(s) found in 'bar_admission_date': {len(invalid_dates)} row(s)"
                print(msg)
                self.error_details.append(msg)
                for i, row in invalid_dates.iterrows():
                    val = row['bar_admission_date']
                    self.error_details.append(f"❌ Invalid 'bar_admission_date' at row {i+2}: value = {val}")
            else:
                msg = "✅ All 'bar_admission_date' values are valid or empty."
                print(msg)
                self.error_details.append(msg)

        # Date format check for start_date and closed_date in cases_df
        for date_col in ['start_date', 'closed_date']:
            if date_col in self.cases_df.columns:
                parsed_dates = pd.to_datetime(self.cases_df[date_col], errors='coerce')
                invalid_dates = self.cases_df[parsed_dates.isna() & self.cases_df[date_col].notna()]
                if not invalid_dates.empty:
                    msg = f"❌ Invalid date format(s) found in '{date_col}': {len(invalid_dates)} row(s)"
                    print(msg)
                    self.error_details.append(msg)
                    for i, row in invalid_dates.iterrows():
                        val = row[date_col]
                        self.error_details.append(f"❌ Invalid '{date_col}' at row {i+2}: value = {val}")
                else:
                    msg = f"✅ All '{date_col}' values are valid or empty."
                    print(msg)
                    self.error_details.append(msg)

        # Enum check for status column in cases_df
        if 'status' in self.cases_df.columns:
            allowed_statuses = {"open", "closed", "pending"}
            invalid_statuses = self.cases_df[~self.cases_df['status'].isin(allowed_statuses)]
            if not invalid_statuses.empty:
                msg = f"❌ Invalid status values found: {len(invalid_statuses)} row(s)"
                print(msg)
                self.error_details.append(msg)
                for i, row in invalid_statuses.iterrows():
                    val = row['status']
                    self.error_details.append(f"❌ Invalid status at row {i+2}: value = {val}")
            else:
                msg = "✅ All status values are valid."
                print(msg)
                self.error_details.append(msg)

        # Pydantic row-level validation for cases_df
        for i, row in self.cases_df.iterrows():
            try:
                CaseModel(**row.to_dict())
            except ValidationError as e:
                self.error_details.append(f"❌ Row {i+2} in cases file failed Pydantic validation:")
                for err in e.errors():
                    self.error_details.append(f"   - {err['loc'][0]}: {err['msg']}")

        # Pydantic row-level validation for time_entries_df
        for i, row in self.time_entries_df.iterrows():
            try:
                TimeEntryModel(**row.to_dict())
            except ValidationError as e:
                self.error_details.append(f"❌ Row {i+2} in time_entries file failed Pydantic validation:")
                for err in e.errors():
                    self.error_details.append(f"   - {err['loc'][0]}: {err['msg']}")

    def export_validation_report(self):
        report_file = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(report_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Check", "Result"])

            # Null check summary
            attorney_nulls = self.attorneys_df.isnull().sum().sum()
            case_nulls = self.cases_df.isnull().sum().sum()
            time_entries_nulls = self.time_entries_df.isnull().sum().sum()
            writer.writerow(["Nulls in attorneys file", attorney_nulls])
            writer.writerow(["Nulls in cases file", case_nulls])
            writer.writerow(["Nulls in time_entries file", time_entries_nulls])

            # Duplicates
            attorney_duplicates = self.attorneys_df['attorney_id'].duplicated().sum()
            writer.writerow(["Duplicate attorney_id in attorneys file", attorney_duplicates])

            # Foreign key validation
            invalid_attorney_ids_cases = set(self.cases_df['attorney_id']) - set(self.attorneys_df['attorney_id'])
            invalid_case_ids_time_entries = set(self.time_entries_df['case_id']) - set(self.cases_df['case_id'])
            invalid_attorney_ids_time_entries = set(self.time_entries_df['attorney_id']) - set(self.attorneys_df['attorney_id'])
            writer.writerow(["Invalid attorney_id references in cases file", len(invalid_attorney_ids_cases)])
            writer.writerow(["Invalid case_id references in time_entries file", len(invalid_case_ids_time_entries)])
            writer.writerow(["Invalid attorney_id references in time_entries file", len(invalid_attorney_ids_time_entries)])

            # Add detailed error rows
            writer.writerow([])
            writer.writerow(["Detailed Errors"])
            for error in self.error_details:
                writer.writerow([error])

        logging.info(f"Validation report exported to {report_file}")

        # Write JSON report
        import json
        json_report_file = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        json_data = {
            "summary": {
                "Nulls in attorneys file": int(attorney_nulls),
                "Nulls in cases file": int(case_nulls),
                "Nulls in time_entries file": int(time_entries_nulls),
                "Duplicate attorney_id in attorneys file": int(attorney_duplicates),
                "Invalid attorney_id references in cases file": int(len(invalid_attorney_ids_cases)),
                "Invalid case_id references in time_entries file": int(len(invalid_case_ids_time_entries)),
                "Invalid attorney_id references in time_entries file": int(len(invalid_attorney_ids_time_entries))
            },
            "details": self.error_details
        }
        with open(json_report_file, 'w') as jf:
            json.dump(json_data, jf, indent=2)
        logging.info(f"Validation JSON report exported to {json_report_file}")

    def get_error_details(self):
        if not self.error_details:
            fallback_msg = "✅ No validation errors found."
            logging.info(fallback_msg)
            return fallback_msg
        return "\n".join(self.error_details)

    def run_all(self):
        self.load_data()
        if self.attorneys_df is not None and self.cases_df is not None and self.time_entries_df is not None:
            self.check_required_columns()
            self.validate_data_integrity()
            self.validate_formats_and_values()