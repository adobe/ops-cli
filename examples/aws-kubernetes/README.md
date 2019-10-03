# Kubernetes

This example allows you to create, manage and explore Kubernetes clusters in Amazon. It uses Terraform and `ops-cli` as the main tools. The example follows the official terraform guide (https://learn.hashicorp.com/terraform/aws/eks-intro) for spinning up an EKS cluster, on which we add a layer of templating in order to make it possible to easily create multiple clusters (eg. in multiple environments). Furthermore, we use the terraform helm provider, in order to install some common services in the Kubernetes cluster (examples include kube2iam, dashboard, metrics etc.)

### Table of Contents  
- [Setup and prerequisites](#setup)  
- [Creating a new Kubernetes cluster with preconfigured services (helm, metrics, kube2iam, dashboard etc.)](#create)
- [Authenticate to a Kubernetes cluster](#authenticate)
- [Frequently asked questions (FAQ)](#faq)  

<a name="setup"/>

### Pre-requisites:

The following software and plugins are required for cluster provisioning:

* [Homebrew](http://brew.sh) - for MacOS/Linux
* ops - https://github.com/adobe/ops-cli#installing
* [Terraform](https://terraform.io/downloads) can be installed via brew or their website
* [AWS IAM Authenticator for Kubernetes](https://github.com/kubernetes-sigs/aws-iam-authenticator)
* kubectl - https://kubernetes.io/docs/tasks/tools/install-kubectl/#install-kubectl
* jq -  https://stedolan.github.io/jq/download

Then:
```sh
git clone https://github.com/adobe/ops-cli.git

cd ops-cli/examples/aws-kubernetes

# For Mac/Linux
./update.sh
```

The above script uses brew to install dependencies (tested only on Mac; linux *might* work as well, given that Homebrew is now available there as well). If you're using a different OS, check through the script to see the required dependencies and install them manually. We accept pull requests, if you'd like to add a script for another OS.

Before you proceed, make sure you have run the `update.sh` script, which is present in this repository. The script will install the `kubectl` tool, the AWS IAM authenticator and other required prerequisites.

### Configure AWS Cli profile
```sh
aws configure --profile my-aws-profile

AWS Access Key ID [None]:
AWS Secret Access Key [None]:
Default region name [None]: us-east-1
```

<a name="create"/>

## Creating a new Kubernetes cluster

Please make sure you have `ops-cli` installed before proceeding (https://github.com/adobe/ops-cli#installing)

At this point you should have the following:
- kubectl installed (via `update.sh`)
- aws iam authenticator installed (via `update.sh`)
- aws profile setup (eg. `my-aws-profile`)
- `ops-cli` installed

### 1. Create a new cluster configuration

In order to create a new Kubernetes cluster, you can make a copy of the cluster yaml definition in the clusters folder and customize it. For example:
```sh
vim clusters/my-kubernetes-cluster.yaml
```
If you wish, change `cluster_id` to something else. This name will be appended in the AWS resource names.

### 3. Create the AWS EKS cluster

This creates the AWS EKS cluster and the worker Auto Scaling Group (ASG). It uses `terraform` via `ops` to make API calls to AWS, which will generate the Kubernetes service.

```sh
ops clusters/my-kubernetes-cluster.yaml terraform --path-name aws-eks plan
ops clusters/my-kubernetes-cluster.yaml terraform --path-name aws-eks apply
```

**Note**: At the time of this writing, it takes up to 15 minutes for AWS to create the Kubernetes resources.

<img width="1123" alt="screenshot 2019-02-02 16 37 57" src="https://user-images.githubusercontent.com/952836/52165392-e8c5a780-2708-11e9-9974-62668534e082.png">

At the end of this step, terraform generates two outputs: 
- a ConfigMap used by worker nodes to authenticate to the K8s master
- The `kube config file` used from your local machine to connect to the Kubernetes cluster. 

### 4. Check that `kubectl` works with the new cluster

The previous step should have generated a `kube config file` for the new Kubernetes cluster. Check that it exists (and that it points to the right cluster).
```sh
export KUBECONFIG=`pwd`/clusters/kubeconfigs/stage-mykubernetescluster.config

kubectl get pods --all-namespaces

# NAMESPACE     NAME                       READY     STATUS    RESTARTS   AGE
# kube-system   coredns-7bcbfc4774-4md27   0/1       Pending   0          9m
# kube-system   coredns-7bcbfc4774-nrd7p   0/1       Pending   0          9m
```
You should see a list of pods. If not, check the [FAQ](#faq) below.

Check that the worker nodes have joined the cluster: 
```sh
export KUBECONFIG=`pwd`/clusters/kubeconfigs/stage-mykubernetescluster.config

kubectl get nodes

# NAME                           STATUS    ROLES     AGE       VERSION
# ip-10-91-56-36.ec2.internal    Ready     <none>    2m        v1.11.5
# ip-10-91-57-197.ec2.internal   Ready     <none>    2m        v1.11.5
```

### 5. Add Kubernetes components (via Helm charts)

This will configure additional services inside the Kubernetes cluster. This includes:
- cluster autoscaler (for the worker nodes)
- metrics (kube-state-metrics + dashboard)
- kube2iam (for AWS IAM association to kubernetes services)
- your own helm charts

#### a. Install Helm (Tiller) inside the Kubernetes cluster
```sh
ops clusters/my-kubernetes-cluster.yaml terraform --path-name helm-init plan
ops clusters/my-kubernetes-cluster.yaml terraform --path-name helm-init apply
```

#### b. Install helm charts
```sh
ops clusters/my-kubernetes-cluster.yaml terraform --path-name helm plan
ops clusters/my-kubernetes-cluster.yaml terraform --path-name helm apply
```

Note that you can easily add helm charts that you want installed in your Kubernetes cluster (eg. prometheus, grafana, splunk, etc.). Just add these in the compositions/generic/helm folder.

At this point you should be up and running!

```sh
$ helm list

# NAME              	REVISION	UPDATED             	STATUS  	CHART                     	APP VERSION	NAMESPACE
# cluster-autoscaler	1       	Feb  2 16:54:16 2019	DEPLOYED	cluster-autoscaler-0.9.0  	1.12.0     	kube-system
# dashboard         	1       	Feb  2 16:54:16 2019	DEPLOYED	kubernetes-dashboard-0.8.0	1.10.0     	kube-system
# kube-state-metrics	1       	Feb  2 16:54:16 2019	DEPLOYED	kube-state-metrics-0.12.1 	1.4.0      	kube-system
# kube2iam          	1       	Feb  2 16:54:16 2019	DEPLOYED	kube2iam-0.9.1            	0.10.0     	kube-system
```

### 6. Cluster decommissioning
To decommission existing cluster terraform destroy commands via ops invocation need to be issued.
It is very important to destroy helm resources before destroying the underlying AWS worker nodes and AWS EKS control plane.
This way external resources created by helm for kubernetes consumption also get destroyed.
```sh
ops clusters/my-kubernetes-cluster.yaml terraform --path-name helm destroy
ops clusters/my-kubernetes-cluster.yaml terraform --path-name aws-eks destroy
``` 

<a name="authenticate"/>

## Authenticate to a Kubernetes cluster

Please make sure to use `my-aws-profile` for the profile name. It is referenced in the EKS cluster configuration file. Or change it in both places.

### Use `kubectl` to manage/explore the Kubernetes cluster

```sh
export KUBECONFIG=`pwd`/clusters/kubeconfigs/stage-mykubernetescluster.config

# check if the kube config works
kubectl get pods --all-namespaces
```
You should see a list of pods. If not, check the [FAQ](#faq) below.

<a name="faq"/>

## Frequently asked questions (FAQ)

#### error: the server doesn't have a resource type "pods"

If you receive the above error when running `kubectl` commands, this means `kubectl` is not able to generate a token for the AWS EKS cluster. Make sure you have the credentials in the `~/.aws/credentials` file
Alternatively, to check if the aws-iam-authenticator is able to generate a token you can run:
```sh
aws-iam-authenticator token -i my-kubernetes-cluster | jq -r .status.token
```
Where `my-kubernetes-cluster` is the name of the AWS EKS cluster.

#### Unable to connect to the server: getting credentials: exec: exec: "aws-iam-authenticator": executable file not found in $PATH

Make sure you have the `aws-iam-authenticator` in the right place and it's executable:
```sh
ls -l /usr/local/bin/aws-iam-authenticator
```

#### error: You must be logged in to the server (Unauthorized)

Try to export the `AWS_PROFILE` env variable, where the AWS account matches the account where the Kubernetes cluster is deployed.
```sh
export AWS_PROFILE=my-aws-profile

kubectl get pods --all-namespaces
```

#### Invalid choice: 'eks', maybe you meant: *es

It's possible that you have an older version of the aws cli (which doesn't have support for the newly added service EKS).
To upgrade it:
```sh
pip install awscli --upgrade
```
