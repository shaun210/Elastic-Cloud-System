Always remove the network using 'docker network prune' and remove all containers on VM 1 before running.

All files for M# can be found under folder M3 on our groups assigned VM too.

To run proxy, run proxy.py followed by the pod name. Three instances (light, medium and heavy required for full functionality)

Every cloud toolset works. (note that you need to enter pod name and not pod id to run, and the pod name are light, medium and heavy).

The way we launch a request is using the cloud toolset interface and type: "launch request <pod_name>" where pod name is either light, heavy or medium.

Medium and heavy app takes some time to return a response(more than 1 min).

to run:
cloud init first, then register and then launch. Dashboard is on: https://10.140.17.123/dash
