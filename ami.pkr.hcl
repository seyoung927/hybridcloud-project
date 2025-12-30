packer {
  required_plugins {
    amazon = {
      source  = "github.com/hashicorp/amazon"
      version = ">= 1.0.0"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "ap-northeast-2"
}

variable "source_ami" {
  type    = string
  default = "ami-09b7782381e5627d5"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "s3_bucket" {
  type = string
}

variable "efs_id" {
  type = string
  default = "fs-0a8f0e00946e642f7"
}

# DB 관련 변수
variable "db_name" {
  type = string
}
variable "db_user" {
  type = string
}
variable "db_password" {
  type = string
}
variable "db_host" {
  type = string
}

source "amazon-ebs" "connectFit_ami" {
  region                      = var.aws_region
  source_ami                  = var.source_ami
  instance_type               = var.instance_type
  ssh_username                = "ubuntu"
  ami_name                    = "connectFit-django-{{timestamp}}"
  associate_public_ip_address = true
  vpc_id                      = "vpc-030027efb0c13cbf7"
  subnet_id                   = "subnet-0e903e65f414f7882"
  iam_instance_profile        = "connectFit-s3-fullaccess"

  tags = {
    Name = "connectFit-django-ami"
  }
}

build {
  sources = ["source.amazon-ebs.connectFit_ami"]

  provisioner "shell" {
    inline = [
      "echo '[1/9] Updating apt packages...'",
      "sudo apt update -y",
      "sudo apt install -y python3 python3-venv python3-pip nginx curl unzip nfs-common pkg-config libmariadb-dev build-essential",

      "echo '[2/9] Installing AWS CLI v2...'",
      "curl 'https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip' -o '/tmp/awscliv2.zip'",
      "unzip /tmp/awscliv2.zip -d /tmp",
      "sudo /tmp/aws/install",

      "echo '[3/9] Setting up Django app directory...'",
      "sudo mkdir -p /home/ubuntu/django_work/CBt",
      "sudo aws s3 cp s3://${var.s3_bucket}/CB-deploy.zip /home/ubuntu/CB-deploy.zip",
      "cd /home/ubuntu/django_work/CB && sudo unzip /home/ubuntu/CB-deploy.zip -d .",

      "echo '[4/9] Setting up Python venv & dependencies...'",
      "python3 -m venv /home/ubuntu/venv",
      "bash -c 'source /home/ubuntu/venv/bin/activate && pip install --upgrade pip && pip install django gunicorn mysqlclient'",

      "echo '[5/9] Setting permissions for ubuntu user...'",
      "sudo chown -R ubuntu:ubuntu /home/ubuntu/django_work",
      "sudo chmod -R 755 /home/ubuntu/django_work",

      "echo '[6/9] Writing environment variables to /etc/environment...'",
      "sudo tee /etc/environment > /dev/null <<EOF",
      "DB_NAME=${var.db_name}",
      "DB_USER=${var.db_user}",
      "DB_PASSWORD=${var.db_password}",
      "DB_HOST=${var.db_host}",
      "EOF",

      "echo '[7/9] Creating Gunicorn systemd service file...'",
      "sudo tee /etc/systemd/system/gunicorn.service > /dev/null <<EOF",
      "[Unit]",
      "Description=Gunicorn Daemon for Django",
      "After=network.target",
      "",
      "[Service]",
      "User=ubuntu",
      "Group=ubuntu",
      "WorkingDirectory=/home/ubuntu/django_work/CB",
      "Environment=\"PATH=/home/ubuntu/venv/bin\"",
      "EnvironmentFile=/etc/environment",
      "ExecStart=/home/ubuntu/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 CB.wsgi:application",
      "Restart=always",
      "",
      "[Install]",
      "WantedBy=multi-user.target",
      "EOF",

      "echo '[8/9] Creating EFS mount systemd service...'",
      "sudo tee /etc/systemd/system/mount-efs.service > /dev/null <<EOF",
      "[Unit]",
      "Description=Mount EFS on startup",
      "After=network-online.target",
      "Wants=network-online.target",
      "",
      "[Service]",
      "Type=oneshot",
      "ExecStart=/usr/bin/bash -c \"mkdir -p /mnt/efs /home/ubuntu/django_work/CB/media && mount -t nfs4 -o nfsvers=4.1 ${var.efs_id}.efs.ap-northeast-2.amazonaws.com:/ /mnt/efs && mount --bind /mnt/efs /home/ubuntu/django_work/CB/media && chown -R ubuntu:ubuntu /home/ubuntu/django_work/CB/media\"",
      "RemainAfterExit=yes",
      "",
      "[Install]",
      "WantedBy=multi-user.target",
      "EOF",

      "echo '[9/9] Enabling services...'",
      "sudo systemctl daemon-reload",
      "sudo systemctl enable gunicorn",
      "sudo systemctl enable mount-efs",
      "echo 'Build process complete!'"
    ]
  }
}