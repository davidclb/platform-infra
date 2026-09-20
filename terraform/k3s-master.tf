resource "proxmox_virtual_environment_vm" "k3s_master" {
  name      = "k3s-master"
  node_name = "proxmox-800g3"

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
    size         = 30
  }

  network_device {
    bridge = "vmbr0"
  }

  initialization {
    ip_config {
      ipv4 {
        address = "192.168.1.10/24"
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
  }
}
