# kubectl deployment walkthru plugin

**Requirements -**

* Working kubeconfig file  
* jq installed
* Works with bash and zsh. 

Validated on Mac. More testing needed on Linux.

**HOW-TO**

1. Clone the repo.

> `git clone https://github.com/papivot/kubectl-plugin-walkthru-deployment.git`

2. Copy the *kubectl-walkthru* to your PATH as *kubectl-walkthru*. E.g.

> `cp kubectl-walkthru /usr/local/bin/kubectl-walkthru`

3. Execute the plugin *kubectl walkthru [deployment_name] [namespace]* E.g.

> `kubectl walkthru metrics-server kube-system`

Currently the plugin reports on 

1. Deployment
2. Replicasets
3. PODS
4. Serviceaccount
5. Serciceaccount secret
6. Clusterrolebinding
7. Clusterrole
8. Comfigmaps as reference or mounted as volumes
9. Secrets as reference or mounted as volumes
10. Endpoints
11. Services. 
