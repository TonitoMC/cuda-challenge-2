# Sequía en el Corredor Seco con GPU

Proyecto del curso CC3069 Computación Paralela y Distribuida (UVG), Caso 4, Agricultura y clima.
Autores: Javier España (23361), Angel Esquit (23221) y José Mérida (201105).

## De qué trata

Las familias del Corredor Seco de Guatemala viven de una sola cosecha de maíz y frijol al año. Si la lluvia falla y nadie avisa a tiempo, pierden la cosecha. El MAGA necesita saber qué zonas están recibiendo mucha menos lluvia de lo normal para avisar antes de la siembra o a mitad de temporada.

Para eso calculamos el **SPI** (Standardized Precipitation Index) en cada celda de un mapa de Centroamérica. El SPI compara la lluvia acumulada de los últimos 30 o 90 días con lo que es normal en esa misma celda. Un valor de 0 es normal, menor que −1 es sequía moderada y menor que −2 es sequía extrema.

El cálculo se repite para miles de celdas y cientos de días, y cada celda es independiente de las demás, por lo que es un buen candidato para una GPU. Implementamos la misma tarea en CPU (NumPy y SciPy) y en GPU (CuPy), la validamos y medimos cuánto tiempo gana la GPU y qué parte del tiempo se va en mover datos.

## Cómo se conecta con el problema real

Lo que le importa al MAGA es cuánto tarda **actualizar el mapa completo** cuando llegan datos nuevos, y cuántas definiciones de sequía puede probar (otras escalas, otras resoluciones). Medimos el costo por valor de leer, copiar y calcular, y con eso proyectamos escenarios realistas (40 años de datos, rejilla más fina, varias escalas). Esas proyecciones son estimaciones lineales y están rotuladas así en el informe.

## Resultados principales (12 meses, 28 millones de valores, RTX 4070 SUPER)

| Medida | Valor |
|---|---|
| Cálculo del SPI en CPU | 214 ms |
| Cálculo del SPI en GPU | 44.5 ms |
| Speedup del cálculo | 4.8x |
| Copia host a GPU | 9.3 ms, el 17% del tiempo de cómputo en GPU |
| Lectura de disco más copia, sobre el flujo en GPU | 45% |
| Speedup del flujo completo (lectura, copia y cálculo) | 3.0x |
| Diferencia máxima del SPI entre CPU y GPU | 1.4e-3 |

La GPU acelera bien las etapas paralelas (suma diaria, scan, ajuste gamma), pero el conteo de días secos consecutivos es secuencial en el tiempo y resulta más lento en GPU. Los detalles, el análisis con la Ley de Amdahl y las proyecciones están en el informe.

## Estructura del repositorio

```
informe_final.pdf        informe final
diapositivas.pdf         presentación de 5 minutos
scripts/
  01_download.py         descarga lluvia horaria de ERA5 (copia pública ARCO-ERA5)
  01b_clean.py           limpieza y control de calidad de los datos
  02_spi_benchmark.py    SPI en CPU y GPU, validación y tiempos
  03_plots.py            mapas y gráfica de tiempos
  04_amdahl.py           tiempos por etapa y análisis de Amdahl
docs/                    fuentes del informe (.tex) y de las diapositivas (.html), guion de la presentación
results/                 benchmark.csv, summary.json, amdahl.json, cleaning_report.json y figuras
```

La carpeta `data/` no se incluye (se vuelve a generar con el primer script).

## Cómo correrlo

Requiere Linux con una GPU NVIDIA y CUDA 12.

```bash
python -m venv venv
venv/bin/pip install numpy scipy xarray "zarr>=3" gcsfs cupy-cuda12x matplotlib pandas netCDF4

venv/bin/python -I scripts/01_download.py 2024    # descarga un año de datos (se puede repetir, retoma donde quedó)
venv/bin/python -I scripts/01b_clean.py           # limpieza, deja solo la racha continua de meses
venv/bin/python -I scripts/02_spi_benchmark.py    # SPI y benchmark CPU contra GPU
venv/bin/python -I scripts/03_plots.py            # figuras
venv/bin/python -I scripts/04_amdahl.py           # análisis de Amdahl
```

Los resultados quedan en `results/`.

## Datos

ERA5 hourly data on single levels, variable `total_precipitation`, rejilla de 0,25 grados. Ventana de 7 a 19 N y de 93 a 77 O, 49 por 65 celdas.

- Fuente oficial: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels
- Cita: Hersbach, H. et al. (2023), Copernicus Climate Change Service (C3S) Climate Data Store, doi:10.24381/cds.adbb2d47
- Licencia: CC-BY 4.0
- Se descarga de la copia pública ARCO-ERA5 de Google Cloud (`gs://gcp-public-data-arco-era5`), que no requiere cuenta, porque la API oficial pide una llave personal.

## Método y simplificaciones

Lluvia horaria, a diaria en mm, luego acumulados móviles de 30 y 90 días con suma prefija. Por celda se ajusta una gamma con la aproximación cerrada de Thom, se combina con la probabilidad de ventanas sin lluvia y se convierte a puntaje z con la inversa de la normal.

- La gamma se ajusta con todas las ventanas de cada celda y no por mes del calendario, como exige el SPI estándar.
- Solo se usan 12 meses continuos, así que los mapas ilustran el método y no son hallazgos de sequía.
- No hay agregación por municipio (falta el shapefile) ni validación contra años secos documentados.
- La prueba de 10 veces más datos usa la rejilla replicada y solo sirve para tiempos. Las proyecciones a 40 años y a rejilla fina son estimaciones lineales.
- Los tiempos de lectura de disco se midieron con la caché caliente.

## Uso de IA

El código y el borrador del informe se hicieron con ayuda de Claude Code (Anthropic). Los integrantes revisaron los resultados y pueden explicar cada parte.
