variable "availability_zones_count" {
  description = "The number of availability zones to use."
  type        = number
  default     = 3
}

variable "vpc_cidr" {
  description = "The CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidr_bits" {
  description = "Subnet bits to create a /24 mask."
  type        = number
  default     = 8
}
