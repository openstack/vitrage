=====================
Kubernetes Datasource
=====================

This document describes how to configure kubernetes datasource properly.
Note that currently we support only Kubernetes on top of Nova (k8s nodes must be nova.instance)

Datasource configuration
------------------------


Step 1
_______

In order to access k8s cluster the following files should be copied from k8s master and stored in the same machine as vitrage :
  * kubeconfig - kubernetes cluster config file is called kubeconfig.
  * certificate-authority (ca.pem)
  * client-certificate (kubectl.pem)
  * client-key (kubectl-key.pem)



Kubeconfig example  ::


	apiVersion: v1
	kind: Config
	clusters:
	- cluster:
		certificate-authority: /home/k8s/ca.pem
		server: https://<IP>:<Port>
	  name: bcmt-kubernetes
	contexts:
	- context:
		cluster: bcmt-kubernetes
		namespace: kube-system
		user: kubelet
	  name: kubelet-context
	current-context: kubelet-context
	preferences: {}
	users:
	- name: kubelet
	  user:
		client-certificate: /home/k8s/kubectl.pem
		client-key: /home/k8s/kubectl-key.pem



keys location (.pem) is usually at ``/etc/kubernetes/ssl``

kubeconfig is usually at ``$HOME/.kube/config``

Make sure to place the files in the same path as written in kubeconfig file.
for example ``ca.pem`` at ``/home/k8s/ca.pem``



Better option is to create a new user + corresponding SSL keys

This requires new SSL keys and some basic understanding in kubernetes (config new user credentials and rules).
this might be more complicated than the first approach.


Step 2
_______

In ``/etc/vitrage/vitrage.conf``:

Set the location for kubeconfig file:

[kubernetes]

config_file = /home/k8s/kubeconfig


Add kubernetes to the list of active datasources:

[datasources]

types = nova.host,nova.instance,nova.zone,aodh,static,cinder.volume,neutron.network,neutron.port,kubernetes



