from flask import Flask, jsonify, request
import os
import docker
import pycurl
import sys
from docker.types import LogConfig
import requests
import socket
import ssl

cURL = pycurl.Curl() 

app = Flask(__name__)

rm_url = 'http://10.140.17.123:3000'

pod_type = None # LIGHT, MEDIUM or HEAVY
pod_name = None # LIGHT, MEDIUM or HEAVY
pod_port = None
pod_id = None
pod_node_limit = None # Max number of nodes
pod_cpu_limit = None # CPU allocation per node
pod_mem_limit = None # Memory allocation per node
pod_img = None
pod_log = None
pod_status = None
nodes = {}

##### DOCKER SETUP
docker_host = os.environ.get('DOCKER_HOST')
if docker_host:
    base = docker_host
else:
    base = 'unix://var/run/docker.sock'

lc = LogConfig(type=LogConfig.types.JSON, config={
  'max-size': '1g',
  'labels': 'production_status,geo'
})

# Connect to the Docker daemon
client = docker.DockerClient(base_url = base)
#####


##### Cloud Toolset Helper functions
def create_pod(pod_type):
    global pod_name
    global pod_id
    global pod_node_limit
    global pod_cpu_limit
    global pod_mem_limit
    global pod_img
    global pod_log
    global pod_status
    if pod_type.upper() == "LIGHT":
        pod_name = "LIGHT"
        pod_node_limit = 20
        pod_cpu_limit = 30
        pod_mem_limit = "100m"
        [pod_img, pod_log] = client.images.build(path ='/home/comp598-user/M2/light/', rm = True, dockerfile = '/home/comp598-user/M2/light/DockerFile')
    elif pod_type.upper() == "MEDIUM":
        pod_name = "MEDIUM"
        pod_node_limit = 15
        pod_cpu_limit = 50
        pod_mem_limit = "300m"
        [pod_img, pod_log] = client.images.build(path ='/home/comp598-user/M2/medium/', rm = True, dockerfile = '/home/comp598-user/M2/medium/DockerFile')
    elif pod_type.upper() == "HEAVY":
        pod_name = "HEAVY"
        pod_node_limit = 10
        pod_cpu_limit = 80
        pod_mem_limit = "500m"
        [pod_img, pod_log] = client.images.build(path ='/home/comp598-user/M2/heavy/', rm = True, dockerfile = '/home/comp598-user/M2/heavy/DockerFile')
    else:
        return None
    pod = client.networks.create(pod_name, driver ="bridge")
    pod_id = pod.id
    pod_status = "ONLINE"
    return pod

def get_pod():
    global pod_id
    return client.networks.get(pod_id)

def remove_pod():
    pod = get_pod()
    pod.remove()

def create_node(node_name, port_number):
    global nodes
    global pod_node_limit
    global pod_img
    global pod_name
    if get_node(node_name) != None :
        return [None, str("Node with name " + node_name + " already exists!")]
    if check_port(port_number) == True :
        return [None, str(port_number + " already in use!")]
    if len(nodes) == pod_node_limit:
        return [None, str(pod_node_limit + " nodes already exists!")]
    node = {}
    node['name'] = node_name
    node['port'] = port_number
    node['status'] = "NEW"
    nodes[node_name] = node
    return [node, str("Node with name " + node_name + " created!")]

def get_node(node_name):
    global nodes
    return nodes.get(node_name, None)

def check_port(port_number):
    global nodes
    for node in nodes.values():
        if node['port'] == port_number:
            print("Port in Use")
            return True ## Already in use
    return False

def remove_node(node_name):
    global nodes
    node = nodes[node_name]
    if node == None :
        return [None, str(node_name + " does not exist in pod: " + pod_name)]
    if node['status'] == "ONLINE":
        container = client.containers.get(node_name)
        container.remove(force=True)
        del nodes[node_name]
        return [node, str(node_name + " was online in pod: " + pod_name)]
    del nodes[node_name]
    return [node, str(node_name + " removed in pod: " + pod_name)]

def get_idle_node():
    global nodes
    for node in nodes.values():
        if node['status'] == "NEW":
            return node
    return None

def launch_node(node_name, port_number):
    global pod_port
    global pod_img
    global pod_cpu_limit
    global pod_mem_limit
    global nodes
    global pod_type
    container = client.containers.run(image = pod_img,
                                      cpu_percent  = pod_cpu_limit,
                                      mem_limit = pod_mem_limit,
                                      detach = True,
                                      network = pod_type,
                                      name = node_name,
                                      command = ['python3', 'app.py', node_name],
                                      ports= {str(pod_port) + '/tcp': port_number})
    node = nodes[node_name]
    node['status'] = "ONLINE"
    return node

def get_online_nodes():
    global nodes
    node_names = []
    node_ports = []
    for node in nodes.values():
        if node['status'] == "ONLINE":
            node_names.append(node['name'])
            node_ports.append(node['port'])
    return [node_names, node_ports]

def get_paused_nodes():
    global nodes
    node_names = []
    node_ports = []
    for node in nodes.values():
        if node['status'] == "PAUSED":
            node_names.append(node['name'])
            node_ports.append(node['port'])
    return [node_names, node_ports]
######

##### Cloud Toolset Endpoints
@app.route('/init')
def cloud_init():
    if request.method == 'GET':
        global pod_type
        pod = create_pod(pod_type)
        if pod == None:
            response = "Failed"
        else:
            response = "Success"
        return jsonify({'response': response, 'pod_type': pod_type})

@app.route('/register/<node_name>/<port_number>')
def cloud_register(node_name, port_number):
    if request.method == 'GET':
        # Check if pod exists
        pod = get_pod()
        if pod == None:
            response = "No network/pod exists"
            return jsonify({'response': response, 'status': 500})
        # Attempt to create node
        [node, response] = create_node(node_name, port_number)
        if node == None:
            return jsonify({'response': response, 'status': 500})
        reload_node_page()
        return jsonify({'response': response, 'status': 200})

@app.route('/remove/<node_name>')
def cloud_remove(node_name):
    if request.method == 'GET':
        [node, response] = remove_node(node_name)
        if node == None:
            return jsonify({'response': response, 'status': 500})
        if node['status'] == "ONLINE":
            reload_node_page()
            return jsonify({'response': response, 'status': 201})
        reload_node_page()
        return jsonify({'response': response, 'status': 200})

@app.route('/launch')
def cloud_launch():
    global pod_status
    node = get_idle_node()
    if node == None:
        response = "No idle node found!"
        return jsonify({'response': response})
    if pod_status == "PAUSED":
        response = "Pod paused!"
        return jsonify({'response': response})
    launch_node(node['name'], node['port'])
    response = "Node launched!"
    reload_node_page()
    return jsonify({'response': response, 'node_name': node['name'], 'node_port': node['port'], 'node_status': node['status'], 'pod_status': pod_status})

@app.route('/resume')
def cloud_resume():
    global pod_status
    global nodes
    [node_names, node_ports] = [[], []]
    if pod_status == "PAUSED":
        pod_status = "ONLINE"
        [node_names, node_ports] = get_paused_nodes()
        for node_name in node_names:
            nodes[node_name]['status'] = "ONLINE"
    reload_node_page()
    return jsonify({'node_names': node_names, 'node_ports': node_ports})

@app.route('/pause')
def cloud_pause():
    global pod_status
    global nodes
    [node_names, node_ports] = [[], []]
    if pod_status == "ONLINE":
        pod_status = "PAUSED"
        [node_names, node_ports] = get_online_nodes()
        for node_name in node_names:
            nodes[node_name]['status'] = "PAUSED"
    reload_node_page()
    return jsonify({'node_names': node_names, 'node_ports': node_ports})

#####

##### Monitoring helper functions

# method to reload node page on website
def reload_node_page():
    list1 = build_all_node_list()
    response = requests.post(rm_url + '/cloud/nodes/list/post/' + str(pod_port), json = list1)
    return response.text

def build_all_node_list():
    global nodes
    list_result = []
    for node_name in nodes:    
        n = nodes[node_name]
        list_result.append(n)
    return list_result

#####

##### Monitoring endpoints

#####

@app.route('/usage')
def cloud_check_containers():
    network = get_pod()
    print(network)
    total_memory_usage = 0
    total_cpu_percent = 0
    num_containers = 0
    containers = network.containers
    for container in containers:
        print(container)
        stats = container.stats(stream=False)
        # Get the CPU usage percentage
        cpu_percent = 0.0
        cpu_delta = float(stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage'])
        system_delta = float(stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage'])
        if cpu_delta > 0.0 and system_delta > 0.0:
            cpu_percent = (cpu_delta / system_delta) * float(stats['cpu_stats']['online_cpus']) * 100
        total_cpu_percent += cpu_percent
        memory_usage = stats['memory_stats']['usage']
        total_memory_usage += memory_usage
        num_containers += 1
    if num_containers > 0:
        avg_cpu_percent = total_cpu_percent / num_containers
        avg_memory_usage = total_memory_usage / num_containers
        resp ={}
        resp['avg_cpu_percent'] = avg_cpu_percent
        resp['avg_memory_usage'] = avg_memory_usage/1000000 #convert to MB
        resp['num_nodes'] = num_containers  
        return jsonify(resp)
    else:
        print("No containers found in the network.")
        
    return 'OK'

if __name__ == '__main__':
    pod_type = sys.argv[1]
    pod_type = pod_type.upper()
    if pod_type == "LIGHT":
        pod_port = 5000
    elif pod_type == "MEDIUM":
        pod_port = 6000
    elif pod_type == "HEAVY":
        pod_port = 7000
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port = pod_port)
