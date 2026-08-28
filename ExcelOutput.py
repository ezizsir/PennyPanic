import csv

def ExcelOutput(data):
    # Data to append
    content = [data]

    # Appending to a CSV file
    with open("MarketData.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(content)