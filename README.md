# JF Clientes

Aplicación Streamlit para gestionar clientes, contactos y actividades.

## Ejecutar

```sh
uv sync
uv run streamlit run streamlit_app.py
```

En el primer inicio, los clientes de `clientes.csv` y, si existe, los contactos de
`contactos.csv` se importan a SQLite. Los CSV se conservan intactos. La base se
guarda en `.jf_clientes/clientes.sqlite3`, fuera del control de versiones, con
permisos restringidos en sistemas POSIX.

Para guardar la base en otra ubicación, define `JF_CLIENTES_DB` antes de iniciar
la aplicación. En un despliegue, esa ruta debe apuntar a un volumen persistente:
el disco local de algunos servicios se elimina al reiniciar o volver a desplegar.
SQLite usa transacciones y claves foráneas; no cifra el contenido, así que el
volumen y sus copias de seguridad deben protegerse con los controles del sistema
de alojamiento.
