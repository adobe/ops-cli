resource "helm_release" "dashboard" {
    name      = "dashboard"
    chart     = "stable/kubernetes-dashboard"
    namespace = "kube-system"
    version   = "0.8.0"
    keyring   = ""

    set {
        name = "rbac.create"
        value = true
    }
}

resource "kubernetes_service" "dashboard" {
  metadata {
    name = "${var.short-region}-${var.environment}-eks-${var.cluster-id}-cluster-dashboard"
    namespace = "kube-system"
  }
  spec {
    selector {
      app = "kubernetes-dashboard"
    }
    load_balancer_source_ranges = ["${var.allowed_cidrs}"]
    port {
      port = 443
      target_port = 8443
    }

    type = "LoadBalancer"
  }
}
