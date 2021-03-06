# -*- coding: utf-8 -*-
"""
Created on Sun Apr 29 17:05:07 2018

@author: Kariza
"""
import pandas as pd
import numpy as np
import math
import pymysql
from sklearn.cluster import KMeans
import math
import json
import sys
from sklearn.cluster import KMeans
from sklearn import metrics
from scipy.spatial.distance import cdist
import numpy as np
import matplotlib.pyplot as plt
##Get latest data for each sensor
#def queryLastData(sensorId):
#    carId = 1
#     #connect to mysql
#    conn = pymysql.connect(host='localhost', 
#                        port=3306, 
#                        user='VCare_dev', 
#                        passwd='!12qwaszx?', 
#                        db='VCareDB')
#    cur = conn.cursor()
#    #get data mileage from database
#    sql = "SELECT time, value value FROM carSensor WHERE carId = " + str(carId) + " AND sensorId = " + str(sensorId) + " ORDER BY id DESC LIMIT 1"
#    cur.execute(sql)
#    #convert object to data
#    result = []
#    for row in cur:
#        result = row
#        
#    conn.commit()
#    cur.close()
#    conn.close()
#    
#    return float(result[1])

def clear_zero_out(df):
    drop_index = [df.index[idx] for idx in range(df.shape[0]) if df.iloc[idx] == 0]
    for index in drop_index:
        df = df.drop(labels=[index])
    return df

#For creating kmeans model
def anomaly_knn_model(df, n_cluster):
    print(type(df))
    df = clear_zero_out(df)
    print(type(df))
    kmeans = KMeans(n_clusters=n_cluster, random_state=0).fit(df.values.reshape(-1,1))
    #clean zero
    
    
    # separate data to each label
    kmean_dict = {}
    for idx in range(len(kmeans.labels_)):
        label = kmeans.labels_[idx]
        if label not in kmean_dict.keys():
            kmean_dict[label] = {}
            kmean_dict[label]['data'] = [df[idx]]
            
        else:
            kmean_dict[label]['data'].append(df[idx])
    
    for idx in kmean_dict.keys():
        kmean_dict[idx]['center'] = kmeans.cluster_centers_[idx][0]
        
    for idx in kmean_dict.keys():
        sum_square = 0
        for data in kmean_dict[idx]['data']:
            sum_square += ((data - kmean_dict[idx]['center']) ** 2)
        error = math.sqrt(sum_square/len(kmean_dict[idx]['data']))
        kmean_dict[idx]['error'] = error
        kmean_dict[idx]['min_bound'] = np.array(kmean_dict[idx]['data']).mean() - error
        kmean_dict[idx]['max_bound'] = np.array(kmean_dict[idx]['data']).mean() + error
        print("mean",np.array(kmean_dict[idx]['data']).mean())
        print("error",kmean_dict[idx]['error'])
        print("min_bound",kmean_dict[idx]['min_bound'])
        print("max_bound",kmean_dict[idx]['max_bound'])
        print("-----------")
    
    return [kmeans, kmean_dict]

def detect_knn_anomaly(kmean_dict, kmeans, new_data):
    predict_label = kmeans.predict([[new_data]])[0]
    print(predict_label)
    if new_data > kmean_dict[predict_label]['max_bound']:
        return 1
    elif new_data < kmean_dict[predict_label]['min_bound']:
        return 1
    return 0


def detect_rulebase_anomaly(data, sensor_name):
    if sensor_name == 'fuel':
        if data < 15:
            return 1
        return 0
    elif sensor_name == 'mileage':
        if data % 10000 == 9800:
            return 1
        return 0
    elif sensor_name == 'voltage':
        if data <= 12:
            return 1
        return 0
    elif sensor_name == 'speed':
        if data > 120:
            return 1
        return 0  

def elbow_plot(data, col):
    data = np.array(data)
    # create new plot and data
    X = data.reshape(len(data), 1)
     
    # k means determine k
    distortions = []
    K = range(1,10)
    for k in K:
        kmeanModel = KMeans(n_clusters=k).fit(X)
        kmeanModel.fit(X)
        distortions.append(sum(np.min(cdist(X, kmeanModel.cluster_centers_, 'euclidean'), axis=1)) / X.shape[0])
     
    # Plot the elbow
    plt.plot(K, distortions, 'bx-')
    plt.xlabel('number of clusters')
    plt.ylabel('Distortion')
    plt.title('The Elbow Method showing the optimal k for ' + col)
    plt.show()
    

#    
def main():
    df_car = pd.read_csv("./df_car.csv", index_col = 'convertTime')    
    n_cluster_dict = {
                'load': 4,
                'temp': 4,
                'rpm': 4
            }
#    df_car = pd.read_csv("/home/ubuntu/www/rest_api/routes/df_car.csv", index_col = 'convertTime')
    anomaly_dict = {
                    0: "normal",
                    1: "anomaly max",
                    2: "anomaly min",
                    3: "low fuel",
                    4: "need to get maintenance",
                    5: "low battery",
                    6: "Too fast!!",
                   }    
    
    kmean_sensor_list = {
                            4: 'load',
                            5: 'temp',
                            12: 'rpm',
                        }
    rule_based_sensor_list = {
                                13: 'speed',
                                47: 'fuel',
                                49: 'mileage',
                                66: 'voltage',
                            }
    
#    print("----- plotting elbow")
#    for sensor_id in kmean_sensor_list:
#        data = np.array(clear_zero_out(df_car[kmean_sensor_list[4]]).values)
#        elbow_plot(data,kmean_sensor_list[sensor_id])
#        
    
    status = {}
    data = 2327
    #detect anomaly by kmean
    for sensor_id in kmean_sensor_list:
#        data = queryLastData(sensor_id)
        sensor_name = kmean_sensor_list[sensor_id]
        n_cluster = n_cluster_dict[sensor_name]
        print("------------", sensor_name, "---------")
        kmean_result = anomaly_knn_model(df_car[sensor_name], n_cluster)
#        print(kmean_result)
        
        kmeans = kmean_result[0]
        kmean_dict = kmean_result[1]
        anomaly = detect_knn_anomaly(kmean_dict, kmeans, data)
        status[sensor_name] = anomaly
           
    #detect anomaly by rule base
    for sensor_id in rule_based_sensor_list:
#        data = queryLastData(sensor_id)
        sensor_name = rule_based_sensor_list[sensor_id]
        print("------------", sensor_name, "---------")
        anomaly = detect_rulebase_anomaly(data, sensor_name)
        status[sensor_name] = anomaly
    
    #Send out data
    data_out = '{"status":200, "response":[{"load":"'+ str(status['load']) + '"},{"temp":"'+ str(status['temp']) + '"},{"rpm":"'+ str(status['rpm']) + '"},{"voltage":"'+ str(status['voltage']) + '"},{"speed":"'+ str(status['speed']) + '"},{"fuel":"'+ str(status['fuel']) + '"},{"mileage":"' + str(status['mileage']) + '"}]}'
    data_out = json.dumps(json.loads(data_out))
    print(data_out)
    
    sys.stdout.flush()
    
 # Start process
if __name__ == '__main__':
    main()