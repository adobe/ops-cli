1. Run 'terraform plan' for all compositions for a given cluster:
```sh
# generates config and runs terraform
ops config/env=dev/cluster=cluster1 terraform plan
```

2. Run 'terraform apply' for all compositions for a given cluster:
```sh
ops config/env=dev/cluster=cluster1 terraform apply --skip-plan
```

3. Run a single composition:
```sh
ops config/env=dev/cluster=cluster1/composition=network terraform apply --skip-plan
```