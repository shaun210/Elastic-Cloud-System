import pycurl
import sys
import time
import asyncio

cURL = pycurl.Curl()

def cloud_init(url):
    cURL.setopt(cURL.URL, url + '/cloud/init')
    cURL.perform()

def cloud_register(url, command):
    command_list = command.split()
    if len(command_list) == 4:
        cURL.setopt(cURL.URL, url + '/cloud/register/' + command_list[3] + '/' + command_list[2])
        cURL.perform()

def cloud_rm(url, command):
    command_list = command.split()
    if len(command_list) == 4:
        cURL.setopt(cURL.URL, url + '/cloud/remove/' + command_list[3] + '/' + command_list[2])
        cURL.perform()

def cloud_launch(url, command):
    command_list = command.split()
    if len(command_list) == 3:
        cURL.setopt(cURL.URL, url + '/cloud/launch/' + command_list[2])
        cURL.perform()

def cloud_resume_pod(url, command):
    command_list = command.split()
    if len(command_list) == 3:
        cURL.setopt(cURL.URL, url + '/cloud/resume/' + command_list[2])
        cURL.perform()

def cloud_pause_pod(url, command):
    command_list = command.split()
    if len(command_list) == 3:
        cURL.setopt(cURL.URL, url + '/cloud/pause/' + command_list[2])
        cURL.perform()


async def gaga(url,command):
    command_list = command.split()
    


# format: launch request light
def launch_request(url, command):
    command_list = command.split()
    
    if len(command_list) == 3:
        cURL.setopt(cURL.URL, url + '/cloud/launchRequest/' + command_list[2])
        cURL.perform()
        
def elasticity_lower_threshold(url, command):
    command_list = command.split()
    if len(command_list) == 5:
        cURL.setopt(cURL.URL, url + '/cloud/elasticity/threshold/lower/' + command_list[3] + '/' + command_list[4])
        cURL.perform()


def elasticity_upper_threshold(url, command):
    command_list = command.split()
    if len(command_list) == 5:
        cURL.setopt(cURL.URL, url + '/cloud/elasticity/threshold/upper/' + command_list[3] + '/' + command_list[4])
        cURL.perform()


def enable_elasticity(url, command):
    command_list = command.split()
    if len(command_list) == 6:
        cURL.setopt(cURL.URL, url + '/cloud/elasticity/enable/' + command_list[3] + '/' + command_list[4] + '/' + command_list[5])
        cURL.perform()

def disable_elasticity(url, command):
    command_list = command.split()
    if len(command_list) == 4:
        cURL.setopt(cURL.URL, url + '/cloud/elasticity/disable/' + command_list[3])
        cURL.perform()

def main():
    rm_url = sys.argv[1]
    em_url = sys.argv[1]
    while (1):
        command = input('$ ')
        if command == "cloud init":
            cloud_init(rm_url)
        elif command.startswith("cloud register"):
            cloud_register(rm_url, command)
        elif command.startswith("cloud rm"):
            cloud_rm(rm_url, command)
        elif command.startswith("cloud launch"): 
            cloud_launch(rm_url, command)
        elif command.startswith("cloud resume"):
            cloud_resume_pod(rm_url, command)
        elif command.startswith("cloud pause"):
            cloud_pause_pod(rm_url, command)
        elif command.startswith("launch request"):
            launch_request(rm_url, command)
        elif command.startswith("cloud elasticity lower_threshold"):
            elasticity_lower_threshold(em_url, command)
        elif command.startswith("cloud elasticity upper_threshold"):
            elasticity_upper_threshold(em_url, command)
        elif command.startswith("cloud elasticity enable"):
            enable_elasticity(em_url, command)
        elif command.startswith("cloud elasticity disable"):
            disable_elasticity(em_url, command)            
if __name__ == '__main__':
    main()