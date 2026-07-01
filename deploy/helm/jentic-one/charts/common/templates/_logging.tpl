{{- define "common.logging-env" -}}
- name: LOG_FORMAT
  value: {{ .Values.global.observability.logging.format | default "json" | quote }}
- name: LOG_LEVEL
  value: {{ .Values.global.observability.logging.level | default "info" | quote }}
- name: OTEL_SERVICE_NAME
  value: {{ printf "%s-%s" .Release.Name .Chart.Name | quote }}
{{- end -}}
