# Qué hacer mañana — Utrecht Beslist

Estado al cerrar el **30 de julio de 2026**. Último commit: `763469c`.
Todo lo de hoy está en `main` y desplegado en
<https://utrecht-voor-iedereen.github.io/utrecht-beslist>.

---

## Lo único que requiere una decisión tuya

**¿Debe la web publicar solo acuerdos, o también las cartas y memos del
ayuntamiento?**

Al arreglar un bug en la resolución de adjuntos, el filtro pasó de dejar 75
documentos a 122. Hay **93 sin procesar** que el cron empezará a publicar a 12
por pasada, unos 8 días.

Ayer te dije que la opción "solo decisiones" dejaría entrar unos 10. **Me
equivoqué.** Al medirlo:

| Opción | Expedientes nuevos | Resultado |
| :--- | ---: | :--- |
| Dejarlo entrar todo | 93 | La portada pasa de 17 a ~105, en su mayoría cartas |
| Solo acuerdos | 5 | Y esos 5 son listas de `Toezeggingen/moties`, poco útiles |

Y el dato que decide:

```
Raadsvoorstel en la ventana de ORI: 28
de esos, ya publicados:             28
Raadsvoorstel sin publicar:          0
```

**La web ya está completa para lo que promete.** Los 17 expedientes cubren
todas las propuestas y acuerdos del 16 de junio al 9 de julio. Los 93 restantes
son `Raadsbrief` (40), memos, actas de B&W y listas — material de acompañamiento,
ni una sola propuesta.

### Recomendación

**No ampliar el alcance.** El subtítulo dice *"Gemeenteraad in begrijpelijke
taal"* y la web responde *"¿qué decidió el pleno?"*. Cuarenta cartas del tipo
*"Raadsbrief Verloop avond na WK voetbalwedstrijd Marokko-Canada"* enterrarían
las decisiones sin añadir nada a esa pregunta.

Si estás de acuerdo, hay que **restringir el filtro** — si no, el cron las
publica solo por existir. En `scripts/source_ori.py`, `filter_documents()`:
añadir que el documento sea un `Raadsvoorstel`, una `motie`, un `amendement`, o
un `Report` con `classification == "Raadsbesluit"`.

Si prefieres ampliar, no hay que tocar nada: el cron lo hará solo.

Tercera vía si dudas: publicarlas pero separadas, con su propia sección o
etiqueta, para que no compitan con los acuerdos en la portada.

---

## Pendientes pequeños

### 1. Un batch de traducción sin procesar

`translation-tasks/batch-01.md` — 2 documentos (`7947062`, `7947093`, que son el
mismo expediente). Se desbloquearon al arreglar el bug del adjunto único.

```bash
cd ~/utrecht-beslist
# pegas batch-01.md en la otra IA, guardas translation-tasks/batch-01.json
python -m scripts.import_summaries --dry-run
python -m scripts.import_summaries
python -m scripts.build_site
```

Después quedará **1 sola entrada** escrita desde el título: `7947092`
(*Benoeming Wethouders*). Cero adjuntos en ORI y sin expediente hermano — no
tiene arreglo salvo buscarla a mano en el portal del ayuntamiento.

### 2. La alarma de obsolescencia va a saltar

Hoy el documento más reciente de ORI tiene 21 días y el umbral es 21, así que
**mañana el cron escribirá un `CRITICAL` en el log**:

```
STALE: the newest document is 22 days old (threshold 21)...
```

**Es correcto, no es un fallo que arreglar.** El documento más nuevo de todo el
índice de Utrecht es del 9 de julio, y no se ha recolectado nada desde el 12.
Puede ser el receso estival del ayuntamiento (los consistorios neerlandeses
paran unas seis semanas) o que el recolector de ORI se haya parado. La API no
los distingue.

Para comprobarlo mañana: mira la agenda del pleno en
<https://utrecht.bestuurlijkeinformatie.nl/> y compárala con la fecha más nueva
en ORI. Si el pleno ha sesionado y ORI no lo tiene, el problema es de ORI.

---

## Qué pasará solo, sin que hagas nada

El cron corre **de lunes a sábado a las 05:47 UTC**
(`.github/workflows/daily.yml`). En cada pasada:

1. Resume como mucho **12** documentos nuevos (tope `MAX_NEW_PER_RUN`), los más
   recientes primero. Es un límite de presupuesto: Groq da 100.000 tokens al día
   y los 93 pendientes valen unos 159.000.
2. Rellena las traducciones que falten (`translate_missing`).
3. Reconstruye la web y hace push.

Los resúmenes que produzca serán de **Groq, no del modelo externo** — peores que
los 25 que hiciste a mano, aunque ya escritos desde el PDF real y no desde el
título.

Si decides restringir el filtro, hazlo **antes de las 05:47 UTC** o publicará
otras 12 cartas.

---

## Dónde está todo

| Qué | Dónde |
| :--- | :--- |
| Filtro de qué se publica | `scripts/source_ori.py` → `filter_documents()` |
| Tope por pasada | `scripts/pipeline.py` → `MAX_NEW_PER_RUN` |
| Umbral de obsolescencia | `scripts/pipeline.py` → `ANOMALY_THRESHOLD_DAYS` |
| Consolidación de expedientes | `scripts/build_site.py` → `consolidate()` |
| Textos de interfaz, 8 idiomas | `scripts/i18n.py` |
| Traspaso a IA externa | `translation-tasks/README.md` |

### Comandos

```bash
cd ~/utrecht-beslist

python -m scripts.build_site                    # reconstruir docs/
python -m scripts.backfill_sources --dry-run    # refrescar datos de ORI
python -m scripts.translate_missing --recheck   # rellenar idiomas
python -m scripts.export_for_external_ai        # generar batches nuevos
python -m scripts.import_summaries --dry-run    # validar respuestas

.venv/bin/python -m ruff check .
.venv/bin/python -m mypy scripts --explicit-package-bases --ignore-missing-imports
PYTHONPATH=. .venv/bin/python -m pytest tests/
```

Los `--dry-run` no escriben nada. Úsalos siempre primero.

---

## Estado actual

- **29 registros de ORI → 17 expedientes** publicados, con 12 redirecciones
  desde las direcciones retiradas.
- **25 de 29** escritos desde el documento real; 4 desde el título, de los
  cuales 3 se arreglan con el batch pendiente.
- **8 idiomas completos**: 0 campos vacíos, 0 restos de inglés.
- **7 cifras económicas**, todas verificadas contra su PDF. 15 entradas en
  blanco porque el documento no da importe.
- **Accesibilidad**: 74 targets por debajo de 44px → 2, y los 2 están
  justificados (honeypot de 1×1 y un enlace exento por WCAG 2.2).
- Ruff, mypy y 9 tests en verde. El rebuild deja el árbol limpio.

### Lo que no he tocado

- Los barrios siguen casi todos en `Overig`. **Lo comprobé y es correcto**: solo
  2 registros (el mismo expediente) mencionan un barrio sin etiquetar, y es de
  pasada en un informe presupuestario. Son expedientes de toda la ciudad.
- `IMPECCABLE_AUDIT.md` lleva una nota de que está superado. No lo borré porque
  es el informe de otra herramienta.
- `scripts/force_resummarize.py` marca todas las entradas como degradadas para
  forzar el re-resumen. Con 93 pendientes reventaría el presupuesto de tokens.
  No lo ejecutes sin bajar antes `MAX_NEW_PER_RUN`.
