# Guion de 5:00 (a los 5:00 se corta). Hablan los tres

| Tiempo | Slide | Habla | Qué decir |
|---|---|---|---|
| 0:00 a 0:15 | 1 Portada | Javier | Presentar al equipo y la pregunta "¿va a llover este año?". |
| 0:15 a 0:40 | 2 Don Chepe | Javier | Personaje ilustrativo con una sola cosecha. Si la alerta llega tarde no sirve. El MAGA decide qué municipios alertar. |
| 0:40 a 1:05 | 3 Los datos | Javier | ERA5 de Copernicus, CC-BY 4.0, cifras de la diapositiva y la limpieza (NaN, negativos, archivos descartados). |
| 1:05 a 1:25 | 4 Qué es el SPI | Javier | Un número por celda que compara la lluvia reciente contra lo normal de esa celda. 0 es normal, menor que −1 sequía moderada, menor que −2 extrema. |
| 1:25 a 2:00 | 5 Cómo lo calculamos | Angel | Los cuatro pasos (lluvia diaria, acumulado móvil, gamma por celda, puntaje z) y la fórmula de z. |
| 2:00 a 2:25 | 6 Qué se paraleliza | Angel | Leer la tabla etapa por etapa. Las celdas son independientes, el conteo de días secos es secuencial y por eso pierde en GPU. |
| 2:25 a 2:45 | 7 Cómo medimos | Angel | Misma función con NumPy o CuPy, mediana de 5, calentamiento y synchronize, tres tiempos separados y validación contra SciPy. |
| 2:45 a 3:10 | 8 El resultado | Angel | Speedup del cálculo y porcentaje del tiempo de GPU que es copia. Leer la gráfica (azul CPU, naranja GPU, verde copia). |
| 3:10 a 3:50 | 9 Mover datos pesa | José | Leer y copiar es casi la mitad del tiempo en GPU. Amdahl: lo paralelo se acelera, lo demás no, y el flujo completo mejora menos que el cálculo. |
| 3:50 a 4:30 | 10 Del benchmark al problema real | José | Qué significa para el MAGA. Actualizar un mapa de 40 años a rejilla fina con 12 escalas toma minutos en CPU y bastante menos en GPU. Son estimaciones. |
| 4:30 a 5:00 | 11 Qué cambia para el MAGA | José | Recalcular en una fracción de segundo, prioridad a la logística de datos y límites honestos (pocos meses, sin años secos de validación, sin municipios). |

La diapositiva 12 (fuentes) no se presenta. Cada integrante debe poder responder sobre cualquier parte, el profesor puede preguntarle a cualquiera. Ensayar con cronómetro.
