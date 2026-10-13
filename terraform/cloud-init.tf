resource "proxmox_virtual_environment_file" "vendor_data_agent" {
  content_type = "snippets"
  datastore_id = "local"
  node_name    = "proxmox-800g3"

  source_raw {
    file_name = "vendor-data-agent.yaml"
    data      = <<-EOF
    #cloud-config
    package_update: true
    packages:
      - qemu-guest-agent
    runcmd:
      - systemctl enable --now qemu-guest-agent
    EOF
  }
}

# Shared Debian 12 LXC template, downloaded once from the official Proxmox
# repository. Referenced by every LXC container resource (pihole, vpn).
# Version verified via `pveam available | grep debian-12` on the Proxmox
# host — don't guess this from web search results, the version drifts.
resource "proxmox_download_file" "debian_12_lxc" {
  content_type = "vztmpl"
  datastore_id = "local"
  node_name    = "proxmox-800g3"
  url          = "http://download.proxmox.com/images/system/debian-12-standard_12.12-1_amd64.tar.zst"
}
