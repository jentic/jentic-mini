{{- define "common.otel-configmap" -}}
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Release.Name }}-{{ .Chart.Name }}-otel-config
  labels:
    app.kubernetes.io/instance: {{ .Release.Name }}
    app.kubernetes.io/name: {{ .Chart.Name }}
data:
  config.yaml: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318
    processors:
      batch:
        timeout: 5s
        send_batch_size: 1024
    exporters:
      otlp:
        endpoint: {{ .Values.global.observability.otel.endpoint | default "localhost:4317" }}
        tls:
          insecure: {{ .Values.global.observability.otel.tls.insecure | default true }}
    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [batch]
          exporters: [otlp]
        metrics:
          receivers: [otlp]
          processors: [batch]
          exporters: [otlp]
        logs:
          receivers: [otlp]
          processors: [batch]
          exporters: [otlp]
{{- end -}}
