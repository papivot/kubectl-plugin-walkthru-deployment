#!/usr/local/bin/python3

from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os, json, datetime,time, subprocess, pprint, sys

name=str(sys.argv[1])
namespace=str(sys.argv[2])

#namespace = 'vmware-system-tmc'
#name = 'policy-sync-extension'
podnamelist = []
secretsvollist = []
cmsvollist = []
secretkeyreflist = []
cmkeyreflist = []
crbnamelist = []
crnamelist = []

config.load_kube_config()
#config.load_incluster_config()
api_instance  = client.AppsV1Api()
api_instance1 = client.CoreV1Api() 
api_instance2 = client.RbacAuthorizationV1Api()

print('Deployment: {} in Namespace: {}'.format(name,namespace)) 

###########################
###  GET DEPLOYMENT DETAILS
###########################
try:
    mydeployment = api_instance.read_namespaced_deployment(name, namespace)
except ApiException as e:
    print("Exception when calling AppsV1Api->read_namespaced_deployment: %s\n" % e)
deploymentuid = mydeployment.metadata.uid

###########################
###  GET REPLICASET DETAILS AND FILTER OUR RS
###########################
try:
    replicasets = api_instance.list_namespaced_replica_set(namespace, watch=False)
except ApiException as e:
    print("Exception when calling AppsV1Api->list_namespaced_replica_set: %s\n" % e)

rslists = replicasets.items
myreplicasets = list(filter(lambda x: x.metadata.owner_references[0].uid == deploymentuid , rslists))
if len(myreplicasets) != 1:
    sys.exit('Exception getting unique Replicaset. Exiting')
else:
    rsuid = myreplicasets[0].metadata.uid
    rsname = myreplicasets[0].metadata.name

###########################
###  GET PODS DETAILS AND FILTER OUR PODS
###########################
try:
    pods = api_instance1.list_namespaced_pod(namespace, watch=False)
except ApiException as e:
    print("Exception when calling CoreV1Api->list_namespaced_pod_template: %s\n" % e)

podslist = pods.items
mypods = list(filter(lambda x: x.metadata.owner_references[0].uid == rsuid , podslist))
if len(mypods) < 1:
    sys.exit('Exception getting Pods. Exiting')
### APPEND POD NAMES IN A LIST
for x in mypods:
    podnamelist.append(x.metadata.name)
    
###########################
###  GET SERVICEACCOUNTNAME FROM THE DEPLOYMENT
###########################
sa = mydeployment.spec.template.spec.service_account_name
try:
    mysa = api_instance1.read_namespaced_service_account(sa, namespace)
except ApiException as e:
    print("Exception when calling CoreV1Api->read_namespaced_service_account: %s\n" % e)

###########################
###  GET CLUSTERROLEBINDINGS AND FILTER OUR CRB. 
###########################
try:
    crbs = api_instance2.list_cluster_role_binding(watch=False)
except ApiException as e:
    print("Exception when calling RbacAuthorizationV1Api->list_cluster_role_binding: %s\n" % e)

crblists = crbs.items
mycrbs1 = list(filter(lambda x: x.subjects is not None, crblists))
mycrbs  = list(filter(lambda x: (x.subjects[0].namespace == namespace and x.subjects[0].name == mysa.metadata.name), mycrbs1))

if len(mycrbs) >= 1:
    for x in mycrbs:
        crbnamelist.append(x.metadata.name)
        crnamelist.append(x.role_ref.name)
#    try:
#        mycr = api_instance2.read_cluster_role(cr)
#    except ApiException as e:
#        print("Exception when calling RbacAuthorizationV1Api->read_cluster_role: %s\n" % e)
else:
    sys.exit('Exception getting unique CRB. Exiting')

###########################
###  GET ENDPOINTS FOR NAMESPACE AND FILTER BY POD
###########################
try:
    endpoints = api_instance1.list_namespaced_endpoints(namespace, watch=False)
except ApiException as e:
    print("Exception when calling CoreV1Api->list_namespaced_endpoints: %s\n" % e)

endpointslist = endpoints.items
endpoints1  = list(filter(lambda x: x.subsets is not None, endpointslist))
myendpoints = list(filter(lambda x: x.subsets[0].addresses[0].target_ref.name in podnamelist, endpoints1))
if len(myendpoints) > 1:
    sys.exit('Exception getting EndPoints. Exiting')
if len(myendpoints) == 1:
    ###  GET SERVICE BASED ON ENDPOINT NAME AND NAMESPACE (DO ERROR HADLING)
    try:
        myservice = api_instance1.read_namespaced_service(myendpoints[0].metadata.name, namespace)  
    except ApiException as e:
        print("Exception when calling CoreV1Api->read_namespaced_service: %s\n" % e)

###########################
###  GET SECRETS AND CM MOUNTED AS VOLUMES
###########################
mtdvolumes = mydeployment.spec.template.spec.volumes 
if mtdvolumes is not None:
    mysecretsvol = list(filter(lambda x: x.secret is not None, mtdvolumes))
    mycmsvol = list(filter(lambda x: x.config_map is not None, mtdvolumes))
    if len(mysecretsvol) > 0:
        for x in mysecretsvol:
            if x.secret.secret_name not in secretsvollist:
                secretsvollist.append(x.secret.secret_name)
    if len(mycmsvol) > 0:
        for y in mycmsvol:
            if y.config_map.name not in cmsvollist:
                cmsvollist.append(y.config_map.name)

###########################
###  GET SECRETS AND CM KEY REFERENCE
###########################
containers = mydeployment.spec.template.spec.containers
for container in containers:
    envs = container.env
    if envs is not None:
        refkeys = list(filter(lambda x: x.value_from is not None, envs))
        mysecretkeyref = list(filter(lambda x: x.value_from.secret_key_ref is not None, refkeys)) 
        mycmkeyref = list(filter(lambda x: x.value_from.config_map_key_ref is not None, refkeys))
        if len(mysecretkeyref) > 0:
            for x in mysecretkeyref:
                if x.value_from.secret_key_ref.name not in secretkeyreflist:
                    secretkeyreflist.append(x.value_from.secret_key_ref.name)   
        if len(mycmkeyref) > 0:
            for x in mycmkeyref:
                if x.value_from.config_map_key_ref.name not in cmkeyreflist:
                    cmkeyreflist.append(x.value_from.config_map_key_ref.name)

###########################
### OUPUT RESULTS 
###########################

print('\n')
print('ACTION \t\tOBJECT_TYPE\t\tNAME')
print('creates\t\treplicaset\t\t{}'.format(rsname)) 
print('creates\t\tpods\t\t\t{}'.format(" ".join(podnamelist)))
if len(secretsvollist) > 0: 
    print('mounts\t\tsecrets as vol\t\t{}'.format(" ".join(secretsvollist)))
if len(secretkeyreflist) > 0:
    print('referencs\tsecrets\t\t\t{}'.format(" ".join(secretkeyreflist)))
if len(cmsvollist) > 0:
    print('mounts\t\tconfigmap as vol\t{}'.format(" ".join(cmsvollist)))
if len(cmkeyreflist) > 0: 
    print('references\tconfigmap\t\t{}'.format(" ".join(cmkeyreflist))) 
print('references\tserviceaccount\t\t{}'.format(sa)) 
print('references\tsa secret\t\t{}'.format(mysa.secrets[0].name))
if len(crbnamelist) > 0:
    print('references\tclusterrolebinding\t{}'.format(" ".join(crbnamelist)))
if len(crnamelist) > 0:
    print('references\tclusterrole\t\t{}'.format(" ".join(crnamelist)))
if len(myendpoints) == 1:
    print('leverages\tservice\t\t\t{}'.format(myendpoints[0].metadata.name)) 
    print('leverages\tendpoint\t\t{}'.format(myendpoints[0].metadata.name)) 