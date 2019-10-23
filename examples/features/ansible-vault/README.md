## Minimal example to cover usage of vault with ansible playbooks

### Editing vault items

Edit / create your vault files using the `ansible-vault` utility

```
$> ansible-vault edit vault/vault_dev.yaml --vault-password-file password_dev.txt
```

Both `vault/vault_dev.yaml` and `vault/vault_prod.yaml` have a variable called `vault_variable`

```
$> ansible-vault view vault/vault_dev.yaml --vault-password-file password_dev.txt

vault_variable: "A dev value"

$> ansible-vault view vault/vault_prod.yaml --vault-password-file password_prod.txt

vault_variable: "A prod value"
```


## Running with ops

In the example playbook provided, we include the vault file appropriate for the given cluster environment

```
$> ops cluster/dev/dev.yaml play playbook/example.yaml  -- --vault-password-file password_dev.txt

PLAY ***************************************************************************

TASK [setup] *******************************************************************
ok: [localhost]

TASK [debug] *******************************************************************
ok: [localhost] => {
    "env": "dev"
}

TASK [include_vars] ************************************************************
ok: [localhost]

TASK [debug] *******************************************************************
ok: [localhost] => {
    "vault_variable": "A dev value"
}


```