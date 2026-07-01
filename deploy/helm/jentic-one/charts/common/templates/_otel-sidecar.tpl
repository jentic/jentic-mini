{{- define "common.otel-sidecar" -}}
- name: otel-collector
  image: {{ .Values.global.observability.otel.image | default "otel/opentelemetry-collector-contrib:latest" }}
  args:
    - "--config=/etc/otel/config.yaml"
  ports:
    - containerPort: 4317
      name: otlp-grpc
      protocol: TCP
    - containerPort: 4318
      name: otlp-http
      protocol: TCP
  env:
    - name: OTEL_EXPORTER_OTLP_ENDPOINT
      value: {{ .Values.global.observability.otel.endpoint | quote }}
    - name: OTEL_SAMPLING_RATIO
      value: {{ .Values.global.observability.otel.samplingRatio | default "1.0" | quote }}
  volumeMounts:
    - name: otel-config
      mountPath: /etc/otel
  resources:
    requests:
      cpu: 50m
      memory: 64Mi
    limits:
      cpu: 200m
      memory: 128Mi
{{- end -}}

{{- define "common.otel-config-volume" -}}
- name: otel-config
  configMap:
    name: {{ .Release.Name }}-{{ .Chart.Name }}-otel-config
{{- end -}}
