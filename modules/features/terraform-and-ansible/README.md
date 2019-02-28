# Example terraform and ansible set-up

## Quick-start

Scan clusters/example.yaml and look over what needs to be changed, especially your public key that you will use to ssh to
hosts and your boto_profile

```
# see the resources that will be created in your aws account
ops clusters/example.yaml terraform plan

# create the resources
# for this example, you will get a cluster with vpc with a bastion box, a nat box, 
# 1 web behind a load balancer and 1 db host
ops clusters/example.yaml terraform apply

# see the inventory
ops clusters/example.yaml inventory

# configure the cluster
ops clusters/example.yaml play ansible/playbooks/site.yaml

# destroy
ops clusters/example.yaml terraform destroy
```
