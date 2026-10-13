# Arquitectura final - AquaHogar

```mermaid
flowchart LR
  A[Red publica de agua] --> B[Acometida principal]
  B --> C[Caudalimetro unico]
  C --> D[ESP32]
  D -->|Wi-Fi / HTTPS JSON| E[API Flask]
  U[Usuario web] -->|HTTPS| F[Frontend HTML CSS JS]
  F --> E
  E --> G[(PostgreSQL)]
  E --> H[Servicio de analisis]
  H --> I[Alertas y recomendaciones]
  G --> E
  E --> F
```

## Principios

- Un solo punto físico de medición por inmueble.
- Backend como única capa que escribe/consulta PostgreSQL.
- Claves y credenciales fuera del código mediante variables de entorno.
- Alertas basadas en línea base de consumo y flujo persistente.
- El sistema detecta anomalías generales; no localiza automáticamente el punto interno de una fuga.
