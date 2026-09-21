resource "proxmox_virtual_environment_file" "k3s_worker_meta_data" {
  content_type = "snippets"
  datastore_id = "local"
  node_name    = "proxmox-800g3"

  source_raw {
    file_name = "k3s-worker-meta-data.yaml"
    data      = <<-EOF
    local-hostname: k3s-worker
    EOF
  }
}

resource "proxmox_virtual_environment_vm" "k3s_worker" {
  name            = "k3s-worker"
  node_name       = "proxmox-800g3"
  stop_on_destroy = true

  clone {
    vm_id = 9000
  }

  cpu {
    cores = 2
    type  = "host"
  }

  memory {
    dedicated = 3072
  }

  disk {
    datastore_id = "local-lvm"
    interface    = "scsi0"
    size         = 20
  }

  network_device {
    bridge = "vmbr0"
  }

  initialization {
    vendor_data_file_id = proxmox_virtual_environment_file.vendor_data_agent.id
    meta_data_file_id   = proxmox_virtual_environment_file.k3s_worker_meta_data.id

    ip_config {
      ipv4 {
        address = "192.168.1.11/24"
        gateway = "192.168.1.1"
      }
    }
    user_account {
      username = "ubuntu"
      keys     = [var.public_ssh_key]
    }
  }

  agent {
    enabled = true

    wait_for_ip {
      disabled = true
    }
  }
}
