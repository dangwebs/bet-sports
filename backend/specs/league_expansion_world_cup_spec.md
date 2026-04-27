# Spec: Expansión Global de Ligas y Copa del Mundo (Contexto Internacional)

## 1. Visión General
**Objetivo:** Habilitar la totalidad de ligas locales para los países ya soportados en el ecosistema, integrar la **Copa del Mundo (WC)** y evolucionar el motor de ML para que, al evaluar torneos internacionales, fusione el desempeño en la liga doméstica con el historial (si existe) del equipo en dicho torneo internacional.

---

## 2. Definición del Alcance y Ligas a Incorporar

### 2.1. Ligas de Países Habilitados (Segundas/Terceras Divisiones)
Actualmente, el sistema soporta países como Inglaterra, España, Alemania, etc. Se debe asegurar la habilitación operativa de sus divisiones inferiores que ya están mapeadas pero comentadas o parcialmente integradas:
*   **Inglaterra:** `E1` (Championship), `E2` (League One), `E3` (League Two), `E_FA` (FA Cup).
*   **España:** `SP2` (Segunda División), `SP_C` (Copa del Rey).
*   **Alemania:** `D2` (2. Bundesliga).
*   **Italia:** `I2` (Serie B).
*   **Francia:** `F2` (Ligue 2).
*   **Países Bajos:** `N2` (Eerste Divisie).
*   **Bélgica:** `B2` (Challenger Pro League).
*   **Portugal:** `P2` (Liga Portugal 2).

### 2.2. Torneos de Selecciones e Internacionales
*   **Copa del Mundo (World Cup):** Código `WC`.
*   Asegurar el correcto flujo de los torneos actuales: `UCL`, `UEL`, `UECL`, `EURO`, `LIB`, `SUD`.

---

## 3. Arquitectura y Modelo de Datos (Domain)

Para cumplir con el requerimiento de "evaluar resultados de liga local + participación internacional", se necesita refactorizar la forma en que se alimenta el contexto estadístico a los modelos.

### 3.1. Modificación de `entities.py`
Se debe extender `TeamStatistics` para separar o incluir el contexto doméstico vs. internacional.
*   **Atributos a agregar en `TeamStatistics`:**
    *   `domestic_stats`: Objeto anidado o dict con el resumen de la liga local.
    *   `international_stats`: Historial del equipo exclusivamente en competiciones internacionales/mundiales.
*   **Lógica de agregación:** Si un partido es internacional (ej. `league_id == 'WC'`), el `StatisticsService` debe buscar el historial del equipo en su liga local (o fase eliminatoria en caso de selecciones) y sumarlo al historial previo en `WC`.

### 3.2. Actualización de `constants.py`
*   Descomentar y oficializar las ligas en `LEAGUES_METADATA`.
*   Añadir la configuración para la Copa del Mundo:
    ```python
    "WC": {"name": "World Cup", "country": "International"}
    ```
*   Añadir `WC` (y las divisiones inferiores) al array `DEFAULT_LEAGUES` si se desea entrenar por defecto, o manejarlo dinámicamente.

---

## 4. Orígenes de Datos (Infrastructure)

Cada adaptador de datos debe configurarse para soportar la constante `WC` y las ligas sudamericanas. Es vital considerar los hallazgos previos sobre integraciones y limitaciones.

### 4.1. `football_data_org.py`
*   Revisar `COMPETITION_CODE_MAPPING` para confirmar: `"WC": "WC"`.
*   Asegurar que los códigos de las segundas divisiones estén mapeados si el API gratuita los soporta.
*   **⚠️ BLOQUEADOR CRÍTICO (Rate Limit):** Este proveedor tiene un límite de 10 peticiones/minuto. La descarga programada de la fase de grupos y eliminatorias del Mundial debe implementar `asyncio.sleep` o un mecanismo de throttling estricto en el `FootballDataOrgSource` para evitar baneos durante la carga inicial de históricos.

### 4.2. `espn.py`
*   Añadir `WC` a `ESPN_LEAGUE_MAPPING`: `"WC": "fifa.world"`.
*   Verificar que las ligas sudamericanas (`LIB`, `SUD`, `COL1`, `ARG1`, `BRA1`) estén usando los slugs correctos definidos en los hallazgos previos.

### 4.3. `thesportsdb.py`
*   Añadir los IDs internos en `INTERNAL_TO_TSDB` para el mundial.
*   Validar que los IDs de Libertadores y Sudamericana sigan funcionando correctamente para traer fixtures futuros.

### 4.4. `github_dataset.py` (Ligas Sudamericanas)
*   **HALLAZGO CRÍTICO:** El CSV dataset local de GitHub contiene la estructura `LEAGUE_MAPPING` que incluye específicamente `COL1`, `ARG1`, `BRA1`, `LIB`, `SUD`.
*   Asegurar que la data histórica de estas ligas se lea a través de este parser para evitar depender excesivamente de las APIs rate-limited para el "cross-fetch" de historia local.

### 4.5. Normalización de Nombres de Equipos (El Reto Principal)
*   **Problema:** "La mayor dificultad es la normalización de nombres de equipos entre las diversas fuentes para poder cruzar datos locales con internacionales de forma efectiva."
*   **Solución:** El `StatisticsService` y el `MatchAggregatorService` deben utilizar diccionarios de normalización estrictos o fuzzy matching para garantizar que "Boca Juniors" (en ARG1) haga match exacto con "Boca Juniors" (en LIB), independientemente de la fuente (ESPN vs GitHub Dataset).

---

## 5. Fusión de Contextos: Liga Local + Internacional (Feature Extraction)

El requerimiento más complejo: *"para la comparación en torneos internacionales, se debe tener en cuenta los resultados en las ligas locales y si se ha tenido participación en el torneo internacional tomar esa data también"*.

### 5.1. `MatchAggregatorService`
*   Al solicitar partidos históricos para entrenar un torneo internacional (ej. `UCL`, `WC`), el agregador no solo debe traer la historia de `UCL`.
*   **Nuevo flujo:**
    1. Obtener los equipos participantes en el torneo internacional.
    2. Realizar un "cross-fetch" para traer los partidos jugados por estos equipos en sus respectivas **ligas locales** durante la temporada actual o anterior.
    3. Esto requiere que `MatchAggregatorService` pueda resolver la liga local base de un equipo (ej. Real Madrid -> `SP1`).

### 5.2. `StatisticsService`
*   Modificar `calculate_team_statistics` y la generación de caché rodante.
*   Cuando un partido es de una liga de tipo "International", calcular:
    *   **Baseline Performance:** Stats de los últimos N partidos del equipo en TODAS las competiciones (lo que incluye su liga local).
    *   **Tournament Specific Performance:** Stats de los últimos N partidos del equipo solo en `match.league.id` (ej. solo historial en `WC`).
*   Esto asegura que un equipo que domina su liga local pero no tiene historial en el Mundial reciba crédito por su nivel doméstico.

### 5.3. `MLFeatureExtractor` (`ml_feature_extractor.py`)
*   Generar nuevos "features" derivados de la combinación:
    *   `home_domestic_win_rate` / `away_domestic_win_rate`.
    *   `home_intl_experience` / `away_intl_experience` (basado en cantidad de partidos jugados en el torneo).
    *   `home_blended_strength`: Fórmula ponderada (ej. `(domestic_pts_per_game * 0.4) + (intl_pts_per_game * 0.6)` si hay historial, o 100% domestic si no hay historial internacional).

---

## 6. Frontend y UI

### 6.1. `LeagueSelector/constants.ts`
*   El código `"World Cup": "Copa del Mundo"` ya existe, asegurar que se renderice correctamente en la UI agrupado bajo la bandera "🌎".
*   Añadir nombres y traducciones para las segundas divisiones habilitadas (Championship, Segunda División, etc.).
*   Actualizar `COUNTRY_DATA` si es necesario para dar cabida a nuevos continentes.

---

## 7. Plan de Ejecución (Tasks)

Un agente que implemente este spec debe seguir este orden exacto:

1.  **Backend - Domain Constants:** Actualizar `LEAGUES_METADATA` y `DEFAULT_LEAGUES` en `backend/src/core/constants.py` y `backend/src/domain/constants.py`.
2.  **Backend - Infrastructure Adapters:** Modificar `espn.py`, `football_data_org.py`, y `thesportsdb.py` para añadir el soporte de `WC` y el resto de divisiones. Validar los slugs/IDs.
3.  **Backend - Domain Entities:** Añadir soporte en `TeamStatistics` para diferenciar o combinar contexto local e internacional.
4.  **Backend - Statistics & Aggregator:**
    *   Implementar la lógica en `StatisticsService` para hacer tracking combinado.
    *   Ajustar `train_model_optimized.py` para que al entrenar ligas internacionales (UCL, WC) alimente el historial local de los equipos al `StatisticsService`.
5.  **Backend - Feature Extractor:** Añadir los features combinados (`domestic_vs_intl`) en `MLFeatureExtractor`.
6.  **Frontend - Constants:** Actualizar `constants.ts` en el LeagueSelector.
7.  **Pruebas & Validación:** Ejecutar un `dry-run` del pipeline de MLOps apuntando a `WC` o `UCL` y verificar en los logs que los features combinados no generen `NaN` cuando no hay historial internacional.
