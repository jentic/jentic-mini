terraform {
  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
}

resource "helm_release" "service" {
  name             = var.release_name
  chart            = var.chart_path
  namespace        = var.namespace
  create_namespace = var.create_namespace

  dynamic "set" {
    for_each = var.values
    content {
      name  = set.key
      value = set.value
    }
  }
}
