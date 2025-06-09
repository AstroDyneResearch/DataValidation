import glob
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from validator import DataValidator

class DataValidationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Data Validator")

        self.attorneys_path = tk.StringVar()
        self.cases_path = tk.StringVar()
        self.entries_path = tk.StringVar()
        self.schema_path = tk.StringVar()

        tk.Label(root, text="Attorneys CSV:").grid(row=0, column=0, sticky="e")
        tk.Entry(root, textvariable=self.attorneys_path, width=50).grid(row=0, column=1)
        tk.Button(root, text="Browse", command=self.browse_attorneys).grid(row=0, column=2)

        tk.Label(root, text="Cases CSV:").grid(row=1, column=0, sticky="e")
        tk.Entry(root, textvariable=self.cases_path, width=50).grid(row=1, column=1)
        tk.Button(root, text="Browse", command=self.browse_cases).grid(row=1, column=2)

        tk.Label(root, text="Time Entries CSV:").grid(row=2, column=0, sticky="e")
        tk.Entry(root, textvariable=self.entries_path, width=50).grid(row=2, column=1)
        tk.Button(root, text="Browse", command=self.browse_entries).grid(row=2, column=2)

        tk.Label(root, text="Schema YAML:").grid(row=3, column=0, sticky="e")
        tk.Entry(root, textvariable=self.schema_path, width=50).grid(row=3, column=1)
        tk.Button(root, text="Browse", command=self.browse_schema).grid(row=3, column=2)

        tk.Button(root, text="Run Validation", command=self.run_validation).grid(row=4, column=1, pady=10)

        # Add scrollable output text box at the bottom
        self.output_text = tk.Text(root, wrap="word", height=15, width=80)
        self.output_text.grid(row=5, column=0, columnspan=3, padx=10, pady=10)

    def browse_attorneys(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if path:
            self.attorneys_path.set(path)

    def browse_cases(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if path:
            self.cases_path.set(path)

    def browse_entries(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if path:
            self.entries_path.set(path)

    def browse_schema(self):
        path = filedialog.askopenfilename(filetypes=[("YAML files", "*.yaml;*.yml")])
        if path:
            self.schema_path.set(path)

    def run_validation(self):
        try:
            validator = DataValidator(
                self.attorneys_path.get(),
                self.cases_path.get(),
                self.entries_path.get(),
                schema_file=self.schema_path.get() if self.schema_path.get() else "schema.yaml"
            )
            validator.run_all()
            summary = f"""===============================
📄 Validation Summary
===============================
🧾 Attorneys File: {self.attorneys_path.get()}
⚖️  Cases File:     {self.cases_path.get()}
⏱️  Time Entries:   {self.entries_path.get()}

🔍 Validation Results:
-------------------------------
"""

            # Find the latest validation report
            report_files = sorted(glob.glob("validation_report_*.csv"), reverse=True)
            if report_files:
                latest_report = report_files[0]
                with open(latest_report, "r") as f:
                    summary += f.read()
            else:
                summary += "No validation report found."

            error_details = validator.get_error_details()
            summary += "\n\n===============================\n🧪 Detailed Validation Log\n===============================\n"

            self.output_text.delete(1.0, tk.END)

            for line in summary.splitlines(keepends=True):
                tag = None
                if "✅" in line:
                    tag = "success"
                elif "❌" in line or "Invalid" in line or "Duplicate" in line:
                    tag = "error"
                elif "Nulls" in line and not line.endswith(",0\n") and not line.endswith(",0"):
                    tag = "error"
                elif "Nulls" in line and (line.endswith(",0\n") or line.endswith(",0")):
                    tag = "success"
                self.output_text.insert(tk.END, line, tag if tag else "")

            for line in error_details.splitlines(keepends=True):
                tag = None
                if "✅" in line:
                    tag = "success"
                elif "❌" in line or "Invalid" in line or "Duplicate" in line:
                    tag = "error"
                elif "Nulls" in line and not line.endswith(",0\n") and not line.endswith(",0"):
                    tag = "error"
                elif "Nulls" in line and (line.endswith(",0\n") or line.endswith(",0")):
                    tag = "success"
                self.output_text.insert(tk.END, line, tag if tag else "")

            # Calculate number of lines in the widget
            num_lines = int(self.output_text.index('end-1c').split('.')[0])
            # Define max height to avoid the window growing too large
            max_height = 40
            # Set new height to number of lines or max_height whichever is smaller
            new_height = min(num_lines, max_height)
            self.output_text.config(height=new_height)

            self.output_text.tag_config("success", foreground="green")
            self.output_text.tag_config("error", foreground="red")

            messagebox.showinfo(
                "Validation Complete",
                "Validation completed. See results in the window below and full details in 'validation.log'."
            )
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = DataValidationApp(root)
    root.mainloop()