import numpy as np
import csv
import itertools


orderid = itertools.count()

with open("market_data.csv", 'w', newline='') as csvfile:
    csvwriter = csv.writer(csvfile)
    header_string = ["Time", "Instrument", "Operation", "OrderId", "Side",
                     "Volume", "Price", "Lifespan"]
    csvwriter.writerow(header_string)
    csvwriter.writerow([0.0, 0, "Insert", next(orderid), "B", 1, 99, "G"])
    csvwriter.writerow([0.0, 0, "Insert", next(orderid), "A", 1, 101, "G"])
    for time in np.arange(0.0, 600, 0.25):
        orderid1 = next(orderid)
        orderid2 = next(orderid)
        csvwriter.writerow([time, 1, "Insert", orderid1, "B", 9, 101, "G"])
        csvwriter.writerow([time, 1, "Insert", orderid2, "A", 9, 99, "G"])
        csvwriter.writerow([time + 0.2, 1, "Cancel", orderid1, "", "", "", "G"])
        csvwriter.writerow([time + 0.2, 1, "Cancel", orderid2, "", "", "", "G"])

    csvfile.close()
