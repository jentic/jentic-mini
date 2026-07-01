variable "release_name" {
  description = "Helm release name"
  type        = string
}

variable "chart_path" {
  description = "Path to the Helm chart"
  type        = string
}

variable "namespace" {
  description = "Kubernetes namespace"
  type        = string
  default     = "default"
}

variable "values" {
  description = "Helm values to pass to the chart"
  type        = map(any)
  default     = {}
}

variable "create_namespace" {
  description = "Whether to create the namespace if it does not exist"
  type        = bool
  default     = true
}
