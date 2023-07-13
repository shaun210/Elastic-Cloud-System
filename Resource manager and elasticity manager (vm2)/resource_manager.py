from flask import Flask, jsonify, request, render_template
import pycurl
import json
import subprocess
from io import BytesIO
import asyncio
import requests
import aiohttp
from threading import Thread
import time

cURL = pycurl.Curl()
proxy_ip = '10.140.17.122'
light_proxy_ip = 'http://10.140.17.122:5000'
medium_proxy_ip = 'http://10.140.17.122:6000'
heavy_proxy_ip = 'http://10.140.17.122:7000'
light_port_counter = 5001
medium_port_counter = 6001
heavy_port_counter = 7001

app = Flask(__name__)

node_list_light = []
node_list_medium = []
node_list_heavy = []
request_list =[]

em_cURL = pycurl.Curl()
usage_light = [0, 0, 0]
usage_medium = [0, 0, 0]
usage_heavy = [0, 0, 0]
elasticity_light = [0, 0, 0]
elasticity_medium = [0, 0, 0]
elasticity_heavy = [0, 0, 0]
threshold_light = [-1, 101]
threshold_medium = [-1, 101]
threshold_heavy = [-1, 101]
elastic_name_counter = 0


@app.route('/dash')
def homepage():
    global node_list_light
    global node_list_medium
    global node_list_heavy
    global usage_light
    global usage_medium
    global usage_heavy
    print("in /dash: light " + str( node_list_light))
    #get for heavy
    return render_template("dashboard.html",  nodes_light  = node_list_light, nodes_medium = node_list_medium, 
                           nodes_heavy = node_list_heavy, request_lists = request_list, usage_lights = usage_light,
                           usage_mediums = usage_medium, usage_heavys = usage_heavy)

## CLIENT ENDPOINTS ##

@app.route('/cloud/init')
async def cloud_init():
    response = ""
    cURL.setopt(cURL.URL, light_proxy_ip + '/init')
    response += cURL.perform_rs()
    cURL.setopt(cURL.URL, medium_proxy_ip + '/init')
    response += cURL.perform_rs()
    cURL.setopt(cURL.URL, heavy_proxy_ip + '/init')
    response += cURL.perform_rs()
    return jsonify({'response': response})

@app.route('/cloud/register/<pod_name>/<node_name>')
def cloud_register(pod_name, node_name):
    global light_port_counter
    global medium_port_counter
    global heavy_port_counter
    response = ""
    if pod_name.upper() == "LIGHT":
        cURL.setopt(cURL.URL, light_proxy_ip + '/register/' + str(node_name) + '/' + str(light_port_counter))
        response = cURL.perform_rs()
        light_port_counter = light_port_counter + 1
    elif pod_name.upper() == "MEDIUM":
        cURL.setopt(cURL.URL, medium_proxy_ip + '/register/' + str(node_name) + '/' + str(medium_port_counter))
        response = cURL.perform_rs()
        medium_port_counter = medium_port_counter + 1
    elif pod_name.upper() == "HEAVY":
        cURL.setopt(cURL.URL, heavy_proxy_ip + '/register/' + str(node_name) + '/' + str(heavy_port_counter))
        response = cURL.perform_rs()
        heavy_port_counter = heavy_port_counter + 1
    else:
        response = "Invalid POD ID!\n"
    return response
            
@app.route('/cloud/remove/<pod_name>/<node_name>')
def cloud_rm(pod_name, node_name):
    buffer = bytearray()
    if pod_name.upper() == "LIGHT":
        cURL.setopt(cURL.URL, light_proxy_ip + '/remove/' + str(node_name))
        servergroup = "lightservers"
    elif pod_name.upper() == "MEDIUM":
        cURL.setopt(cURL.URL, medium_proxy_ip + '/remove/' + str(node_name))
        servergroup = "mediumservers"
    elif pod_name.upper() == "HEAVY":
        cURL.setopt(cURL.URL, heavy_proxy_ip + '/remove/' + str(node_name))
        servergroup = "heavyservers"        
    else:
        return str("Invalid POD ID!\n")
    cURL.setopt(cURL.WRITEFUNCTION, buffer.extend)
    cURL.perform()

    if cURL.getinfo(cURL.RESPONSE_CODE) == 200:
        response_dictionary = json.loads(buffer.decode())
        if response_dictionary['status'] == 201:
            disable_command = str("echo 'experimental-mode on; set server " + servergroup + "/'" + node_name + " state maint " + "| sudo socat stdio /var/run/haproxy.sock")
            subprocess.run(disable_command, shell = True, check = True)
            command = str("echo 'experimental-mode on; del server " + servergroup + "/'" + node_name + " |sudo socat stdio /var/run/haproxy.sock")
            subprocess.run(command, shell = True, check = True)
        return response_dictionary
    return str(cURL.getinfo(cURL.RESPONSE_CODE) + "\n")

@app.route('/cloud/launch/<pod_name>')
def cloud_launch(pod_name):
    buffer = bytearray()
    if pod_name.upper() == "LIGHT":
        cURL.setopt(cURL.URL, light_proxy_ip + '/launch')
        servergroup = "lightservers"
    elif pod_name.upper() == "MEDIUM":
        cURL.setopt(cURL.URL, medium_proxy_ip + '/launch')
        servergroup = "mediumservers"
    elif pod_name.upper() == "HEAVY":
        cURL.setopt(cURL.URL, heavy_proxy_ip + '/launch')
        servergroup = "heavyservers"
    else:
        return str("Invalid POD ID!\n")
    cURL.setopt(cURL.WRITEFUNCTION, buffer.extend)
    cURL.perform()
    if cURL.getinfo(cURL.RESPONSE_CODE) == 200:
        response_dictionary = json.loads(buffer.decode())
        if response_dictionary['response'] == 'No idle node found!':
            return str("No idle node found\n")
        if response_dictionary['response'] == 'Pod paused!':
            return str("Pod is paused\n")
        node_name = response_dictionary['node_name']
        node_port = response_dictionary['node_port']
        node_status = response_dictionary['node_status']
        pod_status = response_dictionary['pod_status']
        if node_status == "ONLINE" and pod_status == "ONLINE":
            command = str("echo 'experimental-mode on; add server " + servergroup +"/" + node_name + " " + proxy_ip + ":" + node_port + "' | sudo socat stdio /var/run/haproxy.sock")
            subprocess.run(command, shell = True, check = True, capture_output=True)
            enable_command = str("echo 'experimental-mode on; set server " + servergroup + "/'" + node_name + ' state ready ' + "|sudo socat stdio /var/run/haproxy.sock")
            subprocess.run(enable_command, shell = True, check = True)
        return response_dictionary
    return str(cURL.getinfo(cURL.RESPONSE_CODE)) + "\n"
    #return response

@app.route('/cloud/resume/<pod_name>')
def cloud_resume(pod_name):
    buffer = bytearray()
    if pod_name.upper() == "LIGHT":
        cURL.setopt(cURL.URL, light_proxy_ip + '/resume')
        servergroup = "lightservers"
    elif pod_name.upper() == "MEDIUM":
        cURL.setopt(cURL.URL, medium_proxy_ip + '/resume')
        servergroup = "mediumservers"
    elif pod_name.upper() == "HEAVY":
        cURL.setopt(cURL.URL, heavy_proxy_ip + '/resume')
        servergroup = "heavyservers"
    else:
        return str("Invalid POD ID!\n")
    cURL.setopt(cURL.WRITEFUNCTION, buffer.extend)
    cURL.perform()
    if cURL.getinfo(cURL.RESPONSE_CODE) == 200:
        response_dictionary = json.loads(buffer.decode())
        node_names = response_dictionary['node_names']
        node_ports = response_dictionary['node_ports']
        for name, port in zip(node_names, node_ports):
            command = str("echo 'experimental-mode on; add server " + servergroup +"/" + name + " " + proxy_ip + ":" + port + "' | sudo socat stdio /var/run/haproxy.sock")
            subprocess.run(command, shell = True, check = True, capture_output=True)
            enable_command = str("echo 'experimental-mode on; set server " + servergroup + "/'" + name + ' state ready ' + "|sudo socat stdio /var/run/haproxy.sock")
            subprocess.run(enable_command, shell = True, check = True)
        return str(pod_name + " now ONLINE\n")
    return str(cURL.getinfo(cURL.RESPONSE_CODE) + "\n")

@app.route('/cloud/pause/<pod_name>')
def cloud_pause(pod_name):
    buffer = bytearray()
    if pod_name.upper() == "LIGHT":
        cURL.setopt(cURL.URL, light_proxy_ip + '/pause')
        servergroup = "lightservers"
    elif pod_name.upper() == "MEDIUM":
        cURL.setopt(cURL.URL, medium_proxy_ip + '/pause')
        servergroup = "mediumservers"
    elif pod_name.upper() == "HEAVY":
        cURL.setopt(cURL.URL, heavy_proxy_ip + '/pause')
        servergroup = "heavyservers"
    else:
        return str("Invalid POD ID!\n")
    cURL.setopt(cURL.WRITEFUNCTION, buffer.extend)
    cURL.perform()
    if cURL.getinfo(cURL.RESPONSE_CODE) == 200:
        response_dictionary = json.loads(buffer.decode())
        node_names = response_dictionary['node_names']
        for name in node_names:
            disable_command = str("echo 'experimental-mode on; set server " + servergroup + "/'" + name + " state maint " + "| sudo socat stdio /var/run/haproxy.sock")
            subprocess.run(disable_command, shell = True, check = True)
            command = str("echo 'experimental-mode on; del server " + servergroup + "/'" + name + " |sudo socat stdio /var/run/haproxy.sock")
            subprocess.run(command, shell = True, check = True)
        return str(pod_name + " now PAUSED\n")
    return str(cURL.getinfo(cURL.RESPONSE_CODE) + "\n")

#### ####

## ELASTICITY MANAGER HELPERS ##

def cloud_elastic_rm(pod_name):
    global node_list_light
    global node_list_medium
    global node_list_heavy
    if pod_name.upper() == "LIGHT":
        if len(node_list_light) > 0:
            node_name = node_list_light[0][0]['name']
            return cloud_rm(pod_name, node_name)
        else:
            return 'Error in light pod node list\n'
    elif pod_name.upper() == "MEDIUM":
        if len(node_list_medium) > 0:
            node_name = node_list_medium[0][0]['name']
            return cloud_rm(pod_name, node_name)
        else:
            return 'Error in medium pod node list\n'
    elif pod_name.upper() == "HEAVY":
        if len(node_list_heavy) > 0:
            node_name = node_list_heavy[0][0]['name']
            return cloud_rm(pod_name, node_name)
        else:
            return 'Error in heavy pod node list\n'      
    else:
        return 'Invalid POD ID!\n'

def cloud_elastic_register(pod_name):
    global elastic_name_counter
    if pod_name.upper() == "LIGHT":
        node_name = str("elastic_" + "light_" + str(elastic_name_counter))
        elastic_name_counter = elastic_name_counter + 1
    elif pod_name.upper() == "MEDIUM":
        node_name = str("elastic_" + "medium_" + str(elastic_name_counter))
        elastic_name_counter = elastic_name_counter + 1
    elif pod_name.upper() == "HEAVY":
        node_name = str("elastic_" + "heavy_" + str(elastic_name_counter))
        elastic_name_counter = elastic_name_counter + 1  
    else:
        return 'Invalid POD ID!\n'
    cloud_register(pod_name, node_name)
    return cloud_launch(pod_name)

#### ####

## ELASTICITY ENDPOINTS##

@app.route('/cloud/elasticity/threshold/lower/<pod_name>/<limit>')
def set_lower_threshold(pod_name, limit):
    global threshold_light
    global threshold_medium
    global threshold_heavy
    value = int(limit)

    if value <= 0 or value >= 100:
        return 'Value should be within 0% to 100%!\n'
    if pod_name.upper() == "LIGHT":
        if value >= threshold_light[1]:
            return 'Value must be lower than upper threshold ' + str(threshold_light[1]) + '\n'
        threshold_light[0] = value
    elif pod_name.upper() == "MEDIUM":
        if value >= threshold_medium[1]:
            return 'Value must be lower than upper threshold ' + str(threshold_medium[1]) + '\n'
        threshold_medium[0] = value
    elif pod_name.upper() == "HEAVY":
        if value >= threshold_heavy[1]:
            return 'Value must be lower than upper threshold ' + str(threshold_heavy[1]) + '\n'
        threshold_heavy[0] = value
    else:
        return 'Invalid pod name!\n'
    return 'Threshold set for ' + str(pod_name) + '\n'

@app.route('/cloud/elasticity/threshold/upper/<pod_name>/<limit>')
def set_upper_threshold(pod_name, limit):
    global threshold_light
    global threshold_medium
    global threshold_heavy
    value = int(limit)

    if value <= 0 or value >= 100:
        return 'Value should be within 0% to 100%!\n'
    if pod_name.upper() == "LIGHT":
        if value <= threshold_light[0]:
            return 'Value must be higher than lower threshold ' + str(threshold_light[0]) + '\n'
        threshold_light[1] = value
    elif pod_name.upper() == "MEDIUM":
        if value <= threshold_medium[0]:
            return 'Value must be higher than lower threshold ' + str(threshold_medium[0]) + '\n'
        threshold_medium[1] = value
    elif pod_name.upper() == "HEAVY":
        if value <= threshold_heavy[0]:
            return 'Value must be higher than lower threshold ' + str(threshold_heavy[0]) + '\n' 
        threshold_heavy[1] = value
    else:
        return 'Invalid pod name!\n'
    return 'Threshold set for ' + str(pod_name) + '\n'

@app.route('/cloud/elasticity/enable/<pod_name>/<min_value>/<max_value>')
def enable_elasticity(pod_name, min_value, max_value):
    global elasticity_light
    global elasticity_medium
    global elasticity_heavy
    min_nodes = int(min_value)
    max_nodes = int(max_value)

    if min_nodes > max_nodes:
        return 'Minimum number of nodes should be higher than maximum\n'
    if min_nodes < 1:
        return 'Minimum number of nodes possible is 1\n'
    if pod_name.upper() == "LIGHT":
        elasticity_light[0] = 1
        elasticity_light[1] = min_nodes
        elasticity_light[2] = max_nodes
    elif pod_name.upper() == "MEDIUM":
        elasticity_medium[0] = 1
        elasticity_medium[1] = min_nodes
        elasticity_medium[2] = max_nodes
    elif pod_name.upper() == "HEAVY":
        elasticity_heavy[0] = 1
        elasticity_heavy[1] = min_nodes
        elasticity_heavy[2] = max_nodes
    else:
        return 'Invalid pod name!\n'
    return 'Enabled ' + str(pod_name) + '\n'

@app.route('/cloud/elasticity/disable/<pod_name>')
def disable_elasticity(pod_name):
    global elasticity_light
    global elasticity_medium
    global elasticity_heavy

    if pod_name.upper() == "LIGHT":
        elasticity_light[0] = 0
        usage_light[1] = "Disabled"
        usage_light[2] = "Disabled"
    elif pod_name.upper() == "MEDIUM":
        elasticity_medium[0] = 0
        usage_medium[1] = "Disabled"
        usage_medium[2] = "Disabled"
    elif pod_name.upper() == "HEAVY":
        elasticity_heavy[0] = 0
        usage_heavy[1] = "Disabled"
        usage_heavy[2] = "Disabled"

    else:
        return 'Invalid pod name!\n'
    return 'Disabled ' + str(pod_name) + '\n'

#### ####

## ELASTICITY MANAGER ##

def elasticity_manager():
    global usage_light
    global usage_medium
    global usage_heavy
    global elasticity_light
    global elasticity_medium
    global elasticity_heavy
    global threshold_light
    global threshold_medium
    global threshold_heavy
    
    while True:
        if elasticity_light[0] == 1: 
            buffer = bytearray()
            em_cURL.setopt(em_cURL.URL, light_proxy_ip + '/usage')
            em_cURL.setopt(em_cURL.WRITEFUNCTION, buffer.extend)
            em_cURL.perform()
            if em_cURL.getinfo(em_cURL.RESPONSE_CODE) == 200:
                s = buffer.decode()
                print("Damn here it is:" + s)
                response_dictionary = json.loads(s)
                print(response_dictionary)
                usage_light[0] = response_dictionary['num_nodes']
                usage_light[1] = response_dictionary['avg_cpu_percent']
                usage_light[2] = response_dictionary['avg_memory_usage']
            if usage_light[1] < threshold_light[0] and usage_light[0] > elasticity_light[1]:
                cloud_elastic_rm("light")
            if usage_light[1] > threshold_light[1] and usage_light[0] < elasticity_light[2]:
                cloud_elastic_register("light")          
        if elasticity_medium[0] == 1: 
            buffer = bytearray()
            em_cURL.setopt(em_cURL.URL, medium_proxy_ip + '/usage')
            em_cURL.setopt(em_cURL.WRITEFUNCTION, buffer.extend)
            em_cURL.perform()
            if em_cURL.getinfo(em_cURL.RESPONSE_CODE) == 200:
                response_dictionary = json.loads(buffer.decode())
                usage_medium[0] = response_dictionary['num_nodes']
                usage_medium[1] = response_dictionary['avg_cpu_percent']
                usage_medium[2] = response_dictionary['avg_memory_usage']
            if usage_medium[1] < threshold_medium[0] and usage_medium[0] > elasticity_medium[1]:
                cloud_elastic_rm("medium")
            if usage_medium[1] > threshold_medium[1] and usage_medium[0] < elasticity_medium[2]:
                cloud_elastic_register("medium")
        if elasticity_heavy[0] == 1: 
            buffer = bytearray()
            em_cURL.setopt(em_cURL.URL, heavy_proxy_ip + '/usage')
            em_cURL.setopt(em_cURL.WRITEFUNCTION, buffer.extend)
            em_cURL.perform()
            if em_cURL.getinfo(em_cURL.RESPONSE_CODE) == 200:
                response_dictionary = json.loads(buffer.decode())
                usage_heavy[0] = response_dictionary['num_nodes']
                usage_heavy[1] = response_dictionary['avg_cpu_percent']
                usage_heavy[2] = response_dictionary['avg_memory_usage']
            if usage_heavy[1] < threshold_heavy[0] and usage_heavy[0] > elasticity_heavy[1]:
                cloud_elastic_rm("heavy")
            if usage_heavy[1] > threshold_heavy[1] and usage_heavy[0] < elasticity_heavy[2]:
                cloud_elastic_register("heavy")
        time.sleep(5)

#### ####

@app.route('/cloud/nodes/list/post/<pod_port>', methods=['POST'])
def update_node_list(pod_port):
    global node_list
    if request.method == 'POST':
        data = request.get_json()
        node_list_temp = data
        if pod_port == '5000': #light
            node_list_light.clear()
            node_list_light.append(node_list_temp)
        if pod_port == '6000': #medium
            node_list_medium.clear()
            node_list_medium.append(node_list_temp)
        if pod_port == '7000': #large
            node_list_heavy.clear()
            node_list_heavy.append(node_list_temp)
        
        return 'OK'


@app.route('/updatePodStatus/<pod_port>', methods=['POST'])
def update_pod_resource_status(pod_port):
    if request.method == 'POST':
        data = request.get_json()
        if (pod_port == '5000'): #light
            usage_light.append(data)
    return 'OK'

@app.route('/cloud/launchRequest/<pod_name>')
def handle_request(pod_name):
    
    pod_name = str(pod_name.upper())
    global request_list
    if pod_name == "LIGHT":
        #NEED TO SEND TO HA PROXY
        backend_url =  "http://10.140.17.123:5000/"
        #NEED TO ADD REQUEST
        temp ={}
        temp['request'] = backend_url
        temp['server_name'] = pod_name
        request_list.append(temp)
        try:
            response = requests.get(backend_url)
        except Exception as e:
            print(f"Exception: {e}")
        return response.text if response else "Error occurred"
    elif pod_name == "MEDIUM":
        #NEED TO SEND TO HA PROXY
        backend_url =  "http://10.140.17.123:6000"
        #NEED TO ADD REQUEST
        temp ={}
        temp['request'] = backend_url
        temp['server_name'] = pod_name
        request_list.append(temp)
        try:
            response = requests.get(backend_url)
        except Exception as e:
            print(f"Exception: {e}")
        return response.text if response else "Error occurred"
    elif pod_name == "HEAVY":
        #NEED TO SEND TO HA PROXY
        backend_url =  "http://10.140.17.123:7000"
        #NEED TO ADD REQUEST
        temp ={}
        temp['request'] = backend_url
        temp['server_name'] = pod_name
        request_list.append(temp)
        try:
            response = requests.get(backend_url)
        except Exception as e:
            print(f"Exception: {e}")
        return response.text if response else "Error occurred"
    
    return 'OK'

if __name__ == "__main__":
    t = Thread(target = elasticity_manager)
    t.start()  
    app.run(use_reloader = True,debug = True, host='0.0.0.0', port = 3000)


