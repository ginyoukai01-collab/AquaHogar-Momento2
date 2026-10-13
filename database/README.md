# Base de datos de AquaHogar

Motor definitivo: **PostgreSQL**.

## Archivos

- `schema.sql`: DDL oficial de la aplicación (tablas, PK, FK, `CHECK`, `UNIQUE` e índices).
- `dump.sql`: datos de evaluación restaurables.
- `aquahogar.dbml`: modelo para importar en dbdiagram.io.
- `ERD_AquaHogar.mmd`: DER equivalente en Mermaid.js.
- `DER_AquaHogar.svg`: imagen vectorial del DER para el informe.

## Restauración rápida

```bash
createdb aquahogar
psql -d aquahogar -f database/schema.sql
psql -d aquahogar -f database/dump.sql
```

## Credenciales del dump (solo evaluación)

| Rol | Usuario | Contraseña |
|---|---|---|
| Administrador | `admin@aquahogar.demo` | `AquaAdmin2026!` |
| Usuario regular | `usuario@aquahogar.demo` | `AquaUsuario2026!` |

No reutilizar estas claves en producción. Para Render se configuran las credenciales de prueba como variables de entorno.

## Normalización

El modelo cumple como mínimo 3FN:

1. **1FN:** los atributos almacenan valores atómicos; no hay grupos repetidos.
2. **2FN:** todas las tablas usan una PK simple y los atributos dependen de la clave completa.
3. **3FN:** los datos de hogar, usuario, sensor, lectura y alerta están separados según su entidad; no se duplican datos derivados de otra entidad como atributos permanentes de tablas no relacionadas.

La relación `households 1:1 sensors` implementa explícitamente la decisión de hardware: un único caudalímetro instalado en la acometida principal de cada inmueble.
