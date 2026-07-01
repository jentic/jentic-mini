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
    # TODO: configure production cluster credentials
    config_path = "~/.kube/config"
  }
}

locals {
  namespace  = "jentic-prod"
  chart_path = "${path.module}/../../helm/jentic-one"
}

module "registry" {
  source       = "../../modules/service"
  release_name = "jentic-registry"
  chart_path   = local.chart_path
  namespace    = local.namespace

  values = {
    "registry.enabled" = "true"
    "app.enabled"      = "false"
  }
}

module "admin" {
  source       = "../../modules/service"
  release_name = "jentic-admin"
  chart_path   = local.chart_path
  namespace    = local.namespace

  values = {
    "admin.enabled" = "true"
    "app.enabled"   = "false"
  }
}

module "control" {
  source       = "../../modules/service"
  release_name = "jentic-control"
  chart_path   = local.chart_path
  namespace    = local.namespace

  values = {
    "control.enabled" = "true"
    "app.enabled"     = "false"
  }
}

module "broker" {
  source       = "../../modules/service"
  release_name = "jentic-broker"
  chart_path   = local.chart_path
  namespace    = local.namespace

  values = {
    "broker.enabled" = "true"
    "app.enabled"    = "false"
  }
}
