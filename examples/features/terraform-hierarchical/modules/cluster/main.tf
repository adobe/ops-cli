variable "config" {}

output "cluster_name" {
  value = var.config.cluster.name
}
