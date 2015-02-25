import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

def plot(stats):
    for name, values in stats.iteritems():
        # the histogram of the data
        n, bins, patches = plt.hist(values["values"], 30, normed=1, facecolor='green', alpha=0.75)

        # add a 'best fit' line
        #y = mlab.gammapdf( bins, mu, sigma)
        #l = plt.plot(bins, y, 'r--', linewidth=1)

        plt.xlabel(name)
        plt.ylabel('Probability')

        plt.grid(True)

        plt.show()

def resplot(ep):
    times = [datetime(1,1,1) + timedelta(0,int(t*60)) for t in ep.times]
    demand = ep.demand_at_times
    #print(times)
    plt.plot(ep.times,demand)
    #plt.gcf().autofmt_xdate()
    plt.show()

def printstats(stats):
    print('-------------')
    for name, value in stats.iteritems():
        print('------------- ', name , ' -------------')
        print('min: ', value["min"])
        print('max: ', value["max"])
        print('avg: ', value["avg"])

def describe(cars):
    # Initialise    
    stats={}
    for name in cars[0].parameters:
        stats[name] = {}
        stats[name].setdefault("min",float("inf"))
        stats[name].setdefault("max",0.0)
        stats[name].setdefault("avg",0.0)
        stats[name]["values"] = []

    def __stats(car):
        i = 0
        for name, value in car.parameters.iteritems():
            stats[name]["min"] = min(stats[name]["min"], value)
            stats[name]["max"] = max(stats[name]["max"], value)
            stats[name]["avg"] = stats[name]["avg"] + value / float(len(cars))
            stats[name]["values"].append(value)

    map(lambda c: __stats(c), cars)
    return(stats)
