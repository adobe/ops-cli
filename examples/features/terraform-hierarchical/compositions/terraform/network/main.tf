variable "config" {}

module "network" {
  source = "../../../modules/network"
  config = var.config
}
