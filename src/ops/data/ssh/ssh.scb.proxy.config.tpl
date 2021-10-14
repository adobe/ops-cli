Host *
    ForwardAgent           yes
    SendEnv                LANG LC_*
    ServerAliveCountMax    2
    ServerAliveInterval    30
    StrictHostKeyChecking  no
    TCPKeepAlive           yes

Host *--*
    ForwardAgent           yes
    LogLevel               QUIET
    ProxyCommand           /usr/bin/nc -X 5 -x 127.0.0.1:{scb_proxy_port} $(echo %h | sed -e 's/.*--//g') %p
    SendEnv                LANG LC_*
    ServerAliveCountMax    2
    ServerAliveInterval    30
    StrictHostKeyChecking  no
    TCPKeepAlive           yes
