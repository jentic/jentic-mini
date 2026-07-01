terraform {
  required_version = ">= 1.5"

  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
}

provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
  }
}

locals {
  namespace  = "jentic-dev"
  chart_path = "${path.module}/../../helm/jentic-one"
}

module "app" {
  source       = "../../modules/service"
  release_name = "jentic-app"
  chart_path   = local.chart_path
  namespace    = local.namespace

  values = {
    "app.enabled"    = "true"
    "broker.enabled" = "true"
  }
}
