variable "proxmox_endpoint" {
  type        = string
  description = "Proxmox VE API endpoint, e.g. https://192.168.1.91:8006/"
}

variable "proxmox_api_token" {
  type        = string
  description = "Proxmox API token, format user@realm!tokenid=secret"
  sensitive   = true
}

variable "public_ssh_key" {
  type        = string
  description = "SSH public key injected into VMs via cloud-init"
}