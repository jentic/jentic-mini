{{- define "common.metrics-env" -}}
- name: JENTIC__OBSERVABILITY__METRICS__EXPORTER
  value: {{ .Values.global.observability.metrics.exporter | default "otlp" | quote }}
{{- end -}}
