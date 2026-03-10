variable "location" {
  description = "Azure region for the platform resources."
  type        = string
  default     = "southcentralus"
}

variable "resource_group_name" {
  description = "Resource group name for Azure infrastructure."
  type        = string
  default     = "rg-market-risk-intelligence"
}

