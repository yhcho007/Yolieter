import os
import openpyxl

def check_excel_size(filename):
    """Checks the size of an Excel file in bytes.

    Args:
        filename (str): The name of the Excel file.

    Returns:
        int: The size of the file in bytes, or -1 if the file does not exist.
    """
    if os.path.exists(filename):
        return os.path.getsize(filename)
    else:
        return -1

# Example usage:
filename = "my_excel_file.xlsx"

# Create a new workbook or load an existing one
try:
    workbook = openpyxl.load_workbook(filename)
except FileNotFoundError:
    workbook = openpyxl.Workbook()

sheet = workbook.active
sheet['A1'] = "Data 1"
sheet['B1'] = "Data 2"

workbook.save(filename)
size_after_write = check_excel_size(filename)

print(f"File size after writing: {size_after_write} bytes")

# Add more data
sheet.append(["More Data 1", "More Data 2"])

workbook.save(filename)
size_after_append = check_excel_size(filename)

print(f"File size after appending: {size_after_append} bytes")

workbook.close()