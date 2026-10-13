resource "proxmox_virtual_environment_file" "pihole_meta_data" {
  content_type = "snippets"
  datastore_id = "local"
  node_name    = "proxmox-800g3"

  source_raw {
    file_name = "pihole-meta-data.yaml"
    data      = <<-EOF
    local-hostname: pihole
    EOF
  }
}

resource "proxmox_virtual_environment_container" "pihole" {
  node_name    = "proxmox-800g3"
  unprivileged = true

  features {
    nesting = true
  }

  initialization {
    hostname = "pihole"

    ip_config {
      ipv4 {
        address = "192.168.1.110/24"
        gateway = "192.168.1.254"
      }
    }

    user_account {
      keys = [var.public_ssh_key]
    }
  }

  network_interface {
    name = "eth0"
  }

  disk {
    datastore_id = "local-lvm"
    size         = 4
  }

  cpu {
    cores = 1
  }

  operating_system {
    template_file_id = proxmox_download_file.debian_12_lxc.id
    type             = "debian"
  }
}