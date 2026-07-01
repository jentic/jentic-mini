output "release_name" {
  description = "Helm release name"
  value       = helm_release.service.name
}

output "namespace" {
  description = "Kubernetes namespace of the release"
  value       = helm_release.service.namespace
}

output "status" {
  description = "Status of the Helm release"
  value       = helm_release.service.status
}
