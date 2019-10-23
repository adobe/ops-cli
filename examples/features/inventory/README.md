Assuming you have instances already running in AWS, you can use `ops` to manage them or, at the very least, you can list them.
The tool leverages an AWS tag that needs to be present on the EC2 instances called `cluster`. 

The following examples lists nodes for the defined AWS profile, that have the tag `cluster` = `mycluster1`. 
Check `my-aws-cluster.yaml` for configuration.

```sh
aws configure --profile aam-npe

AWS Access Key ID [None]:
AWS Secret Access Key [None]:
Default region name [None]: us-east-1
```

```sh
$ ops my-aws-cluster.yaml inventory
```

This will return the list of instances.

You can then SSH to one of the nodes. For instance:
```sh
$ ops my-aws-cluster.yaml ssh mywebapp-1
```
