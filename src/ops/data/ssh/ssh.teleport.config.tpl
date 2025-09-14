# teleport.cfg
Host *
    ProxyCommand "/usr/local/bin/tsh" proxy ssh --cluster=teleport-prod --proxy=teleport.adobe.net:443 %r@%n:%p
    UserKnownHostsFile /dev/null
    StrictHostKeyChecking no
    ControlMaster auto
    ControlPersist 600s
    User {ssh_username}
    Port 22