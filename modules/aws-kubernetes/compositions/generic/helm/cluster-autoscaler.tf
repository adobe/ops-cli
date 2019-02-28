resource "helm_release" "cluster-autoscaler" {
    name      = "cluster-autoscaler"
    chart     = "stable/cluster-autoscaler"
    namespace = "kube-system"
    version   = "0.9.0"
    keyring   = ""

    set {
        name = "rbac.create"
        value = true
    }

    set {
        name = "sslCertPath"
        value = "/etc/ssl/certs/ca-bundle.crt"
    }

    set {
        name = "podAnnotations.iam\\.amazonaws\\.com\\/role"
        value = "arn:aws:iam::{{ terraform.kubernetes.aws.account_id }}:role\\/${var.short-region}-${var.environment}-eks-${var.cluster-id}-cluster-autoscaler"
    }

    set {
        name = "autoDiscovery.clusterName"
        value = "${var.short-region}-${var.environment}-eks-${var.cluster-id}"
    }

    set {
        name = "awsRegion"
        value = "${var.region}"
    }
}
