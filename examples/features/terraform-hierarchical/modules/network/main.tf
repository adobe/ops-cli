variable "config" {}

locals {
  env     = var.config["env"]
  region  = var.config["region"]["location"]
  project = var.config["project"]["prefix"]
}

#resource "aws_s3_bucket" "bucket" {
#  bucket = "${local.env}-${local.region}-${local.project}-test-bucket"
#  acl    = "private"

#  tags = {
#    Name        = "My bucket"
#    Environment = "na"
#  }
#}