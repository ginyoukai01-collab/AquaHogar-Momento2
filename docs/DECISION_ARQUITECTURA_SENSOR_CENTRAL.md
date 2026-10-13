# Decisión de arquitectura: sensor central en la acometida principal

## Contexto

AquaHogar prioriza viabilidad económica, facilidad de instalación y mínima intervención sobre la red hidráulica interna. Por ello, la solución utiliza **un único caudalímetro instalado en la acometida principal del inmueble**.

## Consecuencias de diseño

- El sistema registra el consumo total de agua que entra al hogar.
- No se instalan sensores en grifos, duchas, sanitarios ni otras zonas.
- La base de datos mantiene una relación 1:1 entre hogar y sensor principal.
- La interfaz no atribuye consumo a zonas internas.
- Las anomalías se detectan sobre el consumo global y la línea base histórica del inmueble.
- Una posible fuga se infiere mediante flujo persistente en la entrada general.

## Beneficios

1. Menor costo de adquisición.
2. Instalación más rápida y menos invasiva.
3. Menos dispositivos que configurar y mantener.
4. Una única fuente de verdad para el consumo total.
5. Arquitectura de software y hardware más sencilla para el prototipo académico.

## Limitación aceptada

El sistema no puede determinar automáticamente el punto interno exacto que originó el consumo. Cuando se identifica una anomalía, AquaHogar genera una alerta general y recomienda verificar los posibles puntos de uso o fuga del inmueble.
