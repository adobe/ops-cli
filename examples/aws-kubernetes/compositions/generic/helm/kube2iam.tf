resource "helm_release" "kube2iam" {
    name      = "kube2iam"
    chart     = "stable/kube2iam"
    namespace = "kube-system"
    version   = "0.9.1"
    keyring   = ""

    set {
        name = "rbac.create"
        value = true
    }

    set {
        name = "host.iptables"
        value = "true"
    }

    set {
        name = "host.interface"
        value = "eni+"
    }

    set {
        name = "host.ip"
        value = "$(HOST_IP)"
    } 
}
