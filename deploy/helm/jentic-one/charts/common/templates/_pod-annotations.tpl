{{- /*
common.pod-annotations renders the contents of a subchart's `podAnnotations`
value as a YAML map suitable for `template.metadata.annotations`. Used by
each surface's Deployment so that overlays (e.g. local-prom-app.yaml) can
add scrape annotations without each subchart open-coding the block.

Renders nothing when `.Values.podAnnotations` is empty/unset, so the chart
behaves identically to before for deployments that don't need annotations.
*/ -}}
{{- define "common.pod-annotations" -}}
{{- with .Values.podAnnotations }}
annotations:
{{ toYaml . | indent 2 }}
{{- end }}
{{- end -}}
