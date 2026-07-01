{{- /*
common.image: render the full image reference for a service pod.

Resolution order for the tag:
  1. .Values.image.tag                 (per-service override in subchart values)
  2. .Values.global.image.tag          (umbrella-wide pin, set by Makefile from pyproject)
  3. .Chart.AppVersion                 (umbrella appVersion if propagated)
  4. "latest"                          (last-resort, prints a warning)

Resolution order for the repository:
  1. .Values.image.repository          (per-service value in subchart values)
  2. printf "%s/%s" .Values.global.image.registry .Chart.Name (when registry is set)
*/ -}}
{{- define "common.image" -}}
{{- $tag := .Values.image.tag | default (default "" .Values.global.image.tag) | default .Chart.AppVersion | default "latest" -}}
{{- $repo := .Values.image.repository -}}
{{- if and (not $repo) .Values.global.image.registry -}}
  {{- $repo = printf "%s/%s" .Values.global.image.registry .Chart.Name -}}
{{- end -}}
{{- if not $repo -}}
  {{- fail "image.repository or global.image.registry must be set" -}}
{{- end -}}
{{- printf "%s:%s" $repo $tag -}}
{{- end -}}
