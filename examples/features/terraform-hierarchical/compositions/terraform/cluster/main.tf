variable "config" {}

module "cluster" {
  source = "../../../modules/cluster"
  config = var.config
}

output "cluster_name" {
  value = var.config.cluster.name
}
