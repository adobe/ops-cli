variable "eu-west-1" {
 description = "This variable contains the list of all AZs available in EU Ireland Region"
 default = {
  "0" = "eu-west-1a"
  "1" = "eu-west-1b"
  "2" = "eu-west-1c"
 }
}

variable "us-east-1" {
 description = "This variable contains the list of all AZs available in US East N.Virginia Region"
 default = {
  "0" = "us-east-11"
  "1" = "us-east-1c"
  "2" = "us-east-1d"
  "3" = "us-east-1e"
 }
}

variable "us-west-2" {
 description = "This variable contains the list of all AZs available in US West Oregon Region"
 default = {
  "0" = "us-west-2a"
  "1" = "us-west-2b"
  "2" = "us-west-2c"
 }
}

variable "sa-east-1" {
 description = "This variable contains the list of all AZs available in South America (São Paulo) Region"
 default = {
  "0" = "sa-east-1a"
  "1" = "sa-east-1b"
  "2" = "sa-east-1c"
 }
}

variable "ap-southeast-1" {
 description = "This variable contains the list of all AZs available in Asia Pacific (Singapore) Region"
 default = {
  "0" = "ap-southeast-1a"
  "1" = "ap-southeast-1b"
 }
}

variable "ap-southeast-2" {
 description = "This variable contains the list of all AZs available in Asia Pacific (Sydney) Region"
 default = {
  "0" = "ap-southeast-2a"
  "1" = "ap-southeast-2b"
 }
}

variable "ap-northeast-1" {
 description = "This variable contains the list of all AZs available in Asia Pacific (Tokyo) Region"
 default = {
  "0" = "ap-northeast-1a"
  "1" = "ap-northeast-1b"
 }
}

variable "amazon_linux_hvm_ami" {
  default = {
    ap-northeast-1 = "ami-18869819"
    ap-southeast-1 = "ami-96bb90c4"
    ap-southeast-2 = "ami-d50773ef"
    eu-west-1      = "ami-9d23aeea"
    sa-east-1      = "ami-af9925b2"
    us-east-1      = "ami-146e2a7c"
    us-west-1      = "ami-42908907"
    us-west-2      = "ami-dfc39aef"
  }
}
variable "amazon_linux_nat_ami" {
  default = {
    ap-northeast-1 = "ami-27d6e626"
    ap-southeast-1 = "ami-6aa38238"
    ap-southeast-2 = "ami-893f53b3"
    eu-west-1      = "ami-14913f63"
    sa-east-1      = "ami-8122969c"
    us-east-1      = "ami-184dc970"
    us-west-1      = "ami-a98396ec"
    us-west-2      = "ami-290f4119"
  }
}
