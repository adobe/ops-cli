resource "helm_release" "kube-state-metrics" {
    name      = "kube-state-metrics"
    chart     = "stable/kube-state-metrics"
    namespace = "kube-system"
    version   = "0.12.1"
    keyring   = ""

    set {
        name = "rbac.create"
        value = true
    }
}
