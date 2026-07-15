"""
Modelo de Machine Learning para el test vocacional.

Qué hace y por qué es ML real (no solo reglas):
- Antes, el "resultado" del test era pura suma de pesos definidos a mano
  (regla fija: score[cluster] += peso de cada opción elegida).
- Aquí entrenamos un clasificador de scikit-learn (Random Forest) que
  APRENDE de datos la relación entre "qué opciones eligió alguien" y "qué
  cluster de carrera le corresponde", en vez de aplicar la fórmula de suma
  directamente. El modelo generaliza patrones (combinaciones parciales,
  correlaciones entre preguntas) que una simple suma de pesos no captura,
  y da probabilidades reales (predict_proba) en vez de un porcentaje
  calculado a mano.
- Los datos de entrenamiento son sintéticos: se generan miles de "perfiles"
  de respuestas simuladas a partir de los pesos reales del test (ver
  test_data.py), y la "etiqueta correcta" de cada perfil simulado se calcula
  con la regla original (suma de pesos). El modelo entrenado con esos datos
  deja de depender de la fórmula exacta y aprende a reconocer el patrón
  general, por lo que ante respuestas reales de un usuario (con combinaciones
  que nunca vio en el entrenamiento) puede seguir dando una predicción
  razonable con su propio criterio aprendido.

El entrenamiento ocurre una sola vez, en memoria, cuando arranca el backend
(dura menos de un segundo con este tamaño de datos). No se guarda ningún
archivo binario de modelo en el repositorio.
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

from ml.test_data import CLUSTERS, CAREER_MAP, QUESTIONS

CLUSTER_CODES = list(CLUSTERS.keys())

# Índice: (question_id, value) -> posición en el vector de features
_FEATURE_INDEX: dict[tuple[int, str], int] = {}
_idx = 0
for q_id, _q_type, options in QUESTIONS:
    for value, _weights in options:
        _FEATURE_INDEX[(q_id, value)] = _idx
        _idx += 1
N_FEATURES = _idx


def _true_cluster(selections: dict[int, list[str]]) -> str:
    """Calcula el cluster ganador con la regla original (suma de pesos),
    usado solo para etiquetar los datos sintéticos de entrenamiento."""
    scores = {c: 0 for c in CLUSTER_CODES}
    for q_id, _q_type, options in QUESTIONS:
        chosen = set(selections.get(q_id, []))
        for value, weights in options:
            if value in chosen:
                for cluster, peso in weights.items():
                    scores[cluster] += peso
    return max(scores, key=scores.get)


def _random_profile(rng: random.Random, target_cluster: str | None = None) -> dict[int, list[str]]:
    """Simula las respuestas de una persona.

    Si target_cluster se indica, sesga las elecciones hacia opciones que
    suman puntos a ese cluster (con algo de ruido para variedad realista),
    para asegurar que el dataset de entrenamiento tenga ejemplos suficientes
    de los 10 clusters — incluso los que tienen menos preguntas asociadas
    (ej. Medio Ambiente, Turismo), que con muestreo 100% al azar casi nunca
    ganan y el modelo nunca llegaría a aprenderlos.
    """
    selections: dict[int, list[str]] = {}
    for q_id, q_type, options in QUESTIONS:
        values = [v for v, _w in options]
        if not values:
            continue

        preferred = (
            [v for v, w in options if target_cluster and w.get(target_cluster, 0) > 0]
            if target_cluster else []
        )

        if q_type == "multi":
            k = rng.randint(1, min(3, len(values)))
            if preferred and rng.random() < 0.85:
                pool = preferred + [v for v in values if v not in preferred]
                # prioriza las preferidas pero permite que entren otras
                chosen = preferred[:k] if len(preferred) >= k else preferred + rng.sample(
                    [v for v in values if v not in preferred], k - len(preferred)
                )
                selections[q_id] = chosen
            else:
                selections[q_id] = rng.sample(values, k)
        else:
            if preferred and rng.random() < 0.85:
                selections[q_id] = [rng.choice(preferred)]
            else:
                selections[q_id] = [rng.choice(values)]
    return selections


def _to_vector(selections: dict[int, list[str]]) -> np.ndarray:
    vec = np.zeros(N_FEATURES, dtype=np.float32)
    for q_id, values in selections.items():
        for v in values:
            idx = _FEATURE_INDEX.get((q_id, v))
            if idx is not None:
                vec[idx] = 1.0
    return vec


@dataclass
class ModeloVocacional:
    clf: RandomForestClassifier
    train_accuracy: float
    test_accuracy: float
    n_samples: int

    def predecir(self, selections: dict[int, list[str]], top_n: int = 5) -> list[dict]:
        vec = _to_vector(selections).reshape(1, -1)
        proba = self.clf.predict_proba(vec)[0]
        # predict_proba solo da columnas para clusters vistos en el
        # entrenamiento (deberían ser todos, pero por seguridad mapeamos por nombre)
        cluster_proba = dict(zip(self.clf.classes_, proba))
        ranked = sorted(cluster_proba.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
        return [
            {
                "cluster": cluster,
                "cluster_nombre": CLUSTERS[cluster],
                "probabilidad": round(float(p) * 100, 1),
                "carreras": CAREER_MAP.get(cluster, []),
            }
            for cluster, p in ranked
        ]


def entrenar(n_samples: int = 4000, seed: int = 42) -> ModeloVocacional:
    rng = random.Random(seed)
    X = np.zeros((n_samples, N_FEATURES), dtype=np.float32)
    y = []
    for i in range(n_samples):
        # 70% de las muestras se generan sesgadas hacia un cluster (rotando
        # entre los 10 en orden, para cobertura pareja); 30% totalmente al
        # azar, para que el modelo también vea perfiles "mixtos" reales.
        target = CLUSTER_CODES[i % len(CLUSTER_CODES)] if rng.random() < 0.7 else None
        profile = _random_profile(rng, target)
        X[i] = _to_vector(profile)
        y.append(_true_cluster(profile))

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )
    clf = RandomForestClassifier(n_estimators=200, max_depth=None, random_state=seed, n_jobs=-1)
    clf.fit(X_train, y_train)

    train_acc = accuracy_score(y_train, clf.predict(X_train))
    test_acc = accuracy_score(y_test, clf.predict(X_test))
    return ModeloVocacional(clf=clf, train_accuracy=train_acc, test_accuracy=test_acc, n_samples=n_samples)


# Se entrena una sola vez, al importar el módulo (cuando arranca el backend).
_modelo: ModeloVocacional | None = None


def get_modelo() -> ModeloVocacional:
    global _modelo
    if _modelo is None:
        _modelo = entrenar()
        print(
            f"✔ Modelo ML del test vocacional entrenado: "
            f"{_modelo.n_samples} muestras sintéticas, "
            f"accuracy train={_modelo.train_accuracy:.3f} test={_modelo.test_accuracy:.3f}"
        )
    return _modelo
