# Guion de 5:00 (a los 5:00 se corta). Hablan los tres

| Tiempo | Slide | Habla | Qué decir |
|---|---|---|---|
| 0:00 a 0:15 | 1 Portada | Javier | Presentar al equipo y la pregunta "¿va a llover este año?". |
| 0:15 a 0:40 | 2 Don Chepe | Javier | Personaje ilustrativo con una sola cosecha. Si la alerta tarda horas o días llega tarde. El MAGA decide qué municipios alertar. |
| 0:40 a 1:10 | 3 Los datos | Javier | ERA5 de Copernicus, CC-BY 4.0, cifras de la diapositiva. Limpieza (NaN, negativos, archivos descartados). Dejar el gancho de los minutos que tomó descargar. |
| 1:10 a 1:40 | 4 Qué es el SPI | Javier | Un número por celda que compara la lluvia reciente contra lo normal de esa celda. 0 es normal, menor que −1 es sequía moderada, menor que −2 extrema. |
| 1:40 a 2:15 | 5 Cómo lo calculamos | Angel | Los cuatro pasos (lluvia diaria, acumulado móvil, gamma por celda, puntaje z) y la fórmula de z. |
| 2:15 a 2:45 | 6 Qué se paraleliza | Angel | Leer la tabla etapa por etapa. Las celdas son independientes, el conteo de días secos es secuencial y por eso pierde en GPU. |
| 2:45 a 3:10 | 7 Cómo medimos | Angel | Misma función con NumPy o CuPy, mediana de 5, calentamiento y synchronize, tres tiempos separados y validación contra SciPy. |
| 3:10 a 3:40 | 8 El resultado | José | Speedup del cálculo y porcentaje del tiempo de GPU que es copia. Leer la gráfica (azul CPU, naranja GPU, verde copia). |
| 3:40 a 4:20 | 9 Cuello de botella | José | Traer los datos tarda miles de veces más que calcular. Amdahl: lo paralelo se acelera, lo serial no, y el flujo completo queda en 1×. |
| 4:20 a 5:00 | 10 Qué cambia para el MAGA | José | Recalcular el mapa en milisegundos, prioridad a la logística de datos y límites honestos (pocos meses, sin años secos de validación, sin municipios). |

La diapositiva 11 (fuentes) no se presenta. Cada integrante debe poder responder sobre cualquier parte, el profesor puede preguntarle a cualquiera. Ensayar con cronómetro.
