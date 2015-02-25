import simpy
from simpy import Resource
from util import *
import numpy as np

# Some simulation parameters, distribuitions, etc.

# Distribution of time people spend at work
# [m] gaussian (mean,stddev)
work_time=(9*60,90)

# Distribution of time when people start work, mean=k*phi
# [m] gamma (k,phi)
start_work_at=(8.0,8.0*60.0/8.0)

# Distribution of distance to work, mean=k*phi
# [km] gamma (k,phi)
work_distance=(1.5,3.0/1.5)

# Stddev of travel speed distribution
speed_stddev=1.2

# Battery Controller

# Input power to battery controller
# [kw] gaussian (mean,stddev)
continuous_input_power=(5.0,2.0)

# Battery capacity, mean=k*phi
# [kwh] gamma (k,phi)
battery_capacity=(8.6,25.0/8.6)

# Mean trip speed - simple linear relationship
# with distance clamping the values to some min/max
def mean_travel_speed(distance):
    speed = 35.0/15.0 * distance
    if speed<6.0:
        return 6.0
    elif speed>35.0:
        return 35.0
    else:
         return speed

def range_for_capacity(capacity):
    return (130.0/25 * capacity)

def timestring(mins):
    secs = timedelta(0,int(mins*60))
    d = datetime(1,1,1) + secs
    return("%d:%d:%d" % (d.hour, d.minute, d.second))
    
class EnergyProvider:
    def __init__(self):
        self.times=[]
        self.demand_at_times=[]
        self.demand=0

    def __add_demand(self,env,demand):
        self.times.append(env.now)
        self.demand_at_times.append(self.demand)
        
    def start_charging(self,env,power):
        self.demand += power
        self.__add_demand(env,self.demand)
        
    def stop_charging(self,env,power):
        self.demand -= power
        self.__add_demand(env,self.demand)

class BatteryController:
    def __init__(self, env, energy_provider):
        self.env=env
        self.action = env.process(self.run(env))
        self.activate = env.event()
        self.energy_provider = energy_provider
        self.parameters={}

        power = 2.0
        while power <= 2.0:
            power = np.random.normal(continuous_input_power[0],scale=continuous_input_power[1])
        self.parameters["Continuous input power [kw]"] = power
        
    def charge_by(self,capacity):
        self.capacity = capacity
        
    def run(self,env):
        while True:
            p = self.parameters["Continuous input power [kw]"]
            yield self.activate
            self.energy_provider.start_charging(env, p)

            # Intelligent charging behavior here
            yield self.env.timeout(60 * self.capacity / p)
            self.energy_provider.stop_charging(env, p)

        
class REVCar(object):
    
    def __init__(self, env, battery_controller):
        self.env = env
        # Start the run process everytime an instance is created.
        dist = np.random.gamma(work_distance[0],scale=work_distance[1])
        battery = np.random.gamma(battery_capacity[0],battery_capacity[1])
        self.parameters={}
        self.parameters["Distance to workplace [km]"]             = dist
        self.parameters["Avg. travel speed [km/h]"]               = np.random.normal(mean_travel_speed(dist), speed_stddev)
        self.parameters["Time at work [min]"]                     = np.random.normal(work_time[0],work_time[1])
        self.parameters["Battery capacity [kwh]"]                 = battery
        self.parameters["Work start time [min] - since midnight"] = np.random.gamma(start_work_at[0],start_work_at[1])
        self.parameters["Range [km]"]                             = range_for_capacity(battery)
        self.parameters["Travel time to work [min]"]              = self.parameters["Distance to workplace [km]"] / self.parameters["Avg. travel speed [km/h]"]  * 60
        self.battery_charge_state = battery
        self.action = env.process(self.run(env))
        self.bat_ctrl = battery_controller

        self.pcs = publicChargingStation
        
        # Guard against cars with not enough range

    def __print__(self):
        for name,value in self.parameters.iteritems():
            print (name, ': ', value)
            
    def __energy_consumed(self,kms_travelled):
        return self.parameters["Battery capacity [kwh]"] / self.parameters["Range [km]"] * kms_travelled
        
    def run(self,env):
        dist = self.parameters["Distance to workplace [km]"]
        travel_speed = self.parameters["Avg. travel speed [km/h]"]
        travel_time  =  self.parameters["Travel time to work [min]"]
        battery_capacity = self.parameters["Battery capacity [kwh]"]

        # 1) Wait until departure to work
        if self.parameters["Work start time [min] - since midnight"] <= 0:
            print("Work start time [min] - since midnight", self.parameters["Work start time [min] - since midnight"])
            
        yield env.timeout(self.parameters["Work start time [min] - since midnight"])


        # 2) Travel to work
        if travel_time <= 0:
            print("travel_time", travel_time)
        yield env.timeout(travel_time)
        self.battery_charge_state -= self.__energy_consumed(dist)
        request = None
        # 3) If charge station is available, charge in charging station
        if  publicChargingStation.count < publicChargingStation.capacity:
            request = publicChargingStation.request()
            yield request
            self.charge(self.battery_charge_state, battery_capacity)
            
        # 4) Work...
        # TODO: Should be able to interrupt charging...
        yield env.timeout(self.parameters["Time at work [min]"])
        if (request):
            publicChargingStation.release(request)
        
        # 4) Travel home after work
        if travel_time <= 0:
            print("travel_time", travel_time)
        yield env.timeout(travel_time)
        self.battery_charge_state -= self.__energy_consumed(dist)
        self.charge(self.battery_charge_state, battery_capacity)
        
    # Always charge to capacity    
    def charge(self, charge, capacity):
        self.bat_ctrl.charge_by(capacity - charge)
        self.bat_ctrl.activate.succeed()
        self.bat_ctrl.activate = env.event()
        self.battery_charge_state=capacity
        
def sane(car):
    parameters = car.parameters
    if ((parameters["Distance to workplace [km]"] < 0.5) or
        (parameters["Distance to workplace [km]"] > 100.0) or
        (parameters["Work start time [min] - since midnight"] < 0.1*60.0) or
        (parameters["Work start time [min] - since midnight"] > 24*60-1) or
        (parameters["Avg. travel speed [km/h]"] < 0.5)   or
        (parameters["Avg. travel speed [km/h]"] > 50.0)    or
        (parameters["Time at work [min]"]  < 0.5*60)   or
        (parameters["Time at work [min]"]  > 15.0*60)    or
        (parameters["Battery capacity [kwh]"]   < 5.0)     or
        (parameters["Battery capacity [kwh]"]   > 100.0)   or
        ((2 * parameters["Distance to workplace [km]"]) >  parameters["Range [km]"])):
        return(False)
    return(True)
    
n_cars=30000
env = simpy.Environment()

n_stations=200
globalEnergyGiant = EnergyProvider()
# Charging stations
publicChargingStation = Resource(env,capacity=n_stations)

cars=[]
i = 0

while i < n_cars:
    bat_ctrl = BatteryController(env, globalEnergyGiant)
    car = REVCar(env, bat_ctrl)
    
    if sane(car):
        cars.append(car)
        i += 1

stats = describe(cars)
        
env.run(60*24-1)

#plot(stats)
#printstats(stats)
resplot(globalEnergyGiant)
    
