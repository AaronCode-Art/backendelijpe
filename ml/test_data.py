"""
Fuente de verdad para el entrenamiento del modelo de Machine Learning del
test vocacional.

Esto es una transcripción fiel de los pesos definidos en
front/src/data/testQuestions.ts (CLUSTERS, CAREER_MAP y las opciones de cada
pregunta con sus pesos por cluster). Si el frontend cambia las preguntas o
los pesos, este archivo debe actualizarse igual para que el modelo entrenado
siga reflejando el mismo criterio vocacional.

Solo se transcriben "value" y "weights" de cada opción (lo único que el
modelo necesita); las etiquetas visibles viven únicamente en el frontend.
"""

CLUSTERS: dict[str, str] = {
    "tec": "Ingeniería y Tecnología",
    "sal": "Ciencias de la Salud",
    "neg": "Negocios y Administración",
    "hum": "Humanidades y Sociales",
    "art": "Artes y Diseño",
    "cie": "Ciencias Básicas",
    "der": "Derecho y Ciencias Políticas",
    "edu": "Educación",
    "amb": "Medio Ambiente y Recursos Naturales",
    "tur": "Turismo y Gastronomía",
}

CAREER_MAP: dict[str, list[str]] = {
    "tec": ["Ingeniería de Sistemas", "Ingeniería Civil", "Ingeniería Industrial", "Ingeniería de Software"],
    "sal": ["Medicina Humana", "Enfermería", "Odontología", "Farmacia y Bioquímica"],
    "neg": ["Administración de Empresas", "Contabilidad", "Economía", "Marketing"],
    "hum": ["Derecho", "Psicología", "Comunicación Social", "Sociología"],
    "art": ["Arquitectura", "Diseño Gráfico", "Artes Escénicas", "Diseño de Interiores"],
    "cie": ["Matemáticas", "Física", "Química", "Biología"],
    "der": ["Derecho y Ciencias Políticas", "Ciencias Políticas", "Relaciones Internacionales"],
    "edu": ["Educación Primaria", "Educación Secundaria", "Psicología Educativa"],
    "amb": ["Ingeniería Ambiental", "Agronomía", "Ingeniería Forestal"],
    "tur": ["Turismo y Hotelería", "Gastronomía", "Gestión Cultural"],
}

# Cada pregunta: (id, tipo, [(value, {cluster: peso, ...}), ...])
# tipo "multi" -> el usuario puede elegir 1 a N opciones; "single"/"scale" -> exactamente 1.
QUESTIONS: list[tuple[int, str, list[tuple[str, dict[str, int]]]]] = [
    (1, "multi", [
        ("prog", {"tec": 3, "cie": 1}), ("read", {"hum": 3, "cie": 1, "der": 1}),
        ("art", {"art": 3, "tec": 1}), ("sport", {"sal": 2, "edu": 1}),
        ("cook", {"tur": 3, "neg": 1}), ("build", {"tec": 3, "art": 1}),
    ]),
    (2, "single", [
        ("tech_content", {"tec": 3, "cie": 1}), ("news", {"hum": 3, "der": 2}),
        ("art_content", {"art": 3, "hum": 1}), ("science", {"cie": 3, "amb": 2}),
        ("biz_content", {"neg": 3, "tec": 1}), ("health", {"sal": 3, "edu": 1}),
        ("travel", {"tur": 3, "hum": 1}),
    ]),
    (3, "single", [
        ("dev_tech", {"tec": 4, "cie": 2}), ("heal", {"sal": 4, "cie": 2}),
        ("biz", {"neg": 4, "der": 1}), ("justice", {"der": 4, "hum": 2}),
        ("create", {"art": 4, "hum": 2}), ("teach", {"edu": 4, "hum": 2}),
        ("env", {"amb": 4, "cie": 2}),
    ]),
    (4, "multi", [
        ("math", {"tec": 3, "cie": 3}), ("chem", {"cie": 3, "sal": 2, "amb": 1}),
        ("history", {"hum": 3, "der": 1}), ("lit", {"hum": 3, "art": 1, "edu": 1}),
        ("arts", {"art": 3, "hum": 1}), ("pe", {"sal": 2, "edu": 1}),
        ("econ", {"neg": 3, "tec": 2}),
    ]),
    (5, "single", [
        ("logic", {"tec": 3, "cie": 2}), ("fair", {"der": 3, "hum": 2}),
        ("people", {"sal": 3, "edu": 2}), ("creative", {"art": 3, "neg": 1}),
        ("data", {"neg": 3, "tec": 2}),
    ]),
    (6, "single", [
        ("launch_tech", {"tec": 3, "neg": 2}), ("save_life", {"sal": 4, "edu": 1}),
        ("win_case", {"der": 4, "hum": 1}), ("exhibit", {"art": 4, "hum": 1}),
        ("open_biz", {"neg": 3, "tur": 2}), ("teach_impact", {"edu": 4, "hum": 2}),
        ("restore", {"amb": 4, "cie": 2}),
    ]),
    (7, "single", [
        ("python", {"tec": 4, "cie": 1}), ("autocad", {"art": 3, "tec": 2}),
        ("adobe", {"art": 4, "neg": 1}), ("excel", {"neg": 4, "tec": 1}),
        ("music", {"art": 4, "hum": 1}), ("lang", {"hum": 3, "neg": 2, "tur": 2}),
    ]),
    (8, "scale", [
        ("1", {"hum": 1, "art": 1, "edu": 1}), ("2", {"hum": 1, "neg": 1}),
        ("3", {"neg": 1, "tec": 1}), ("4", {"tec": 2, "cie": 2}), ("5", {"tec": 3, "cie": 3}),
    ]),
    (9, "multi", [
        ("logic_skill", {"tec": 3, "cie": 2, "neg": 1}), ("comm", {"hum": 3, "edu": 2, "der": 1}),
        ("empathy", {"sal": 3, "edu": 3, "hum": 1}), ("visual", {"art": 4, "tec": 1}),
        ("organize", {"neg": 3, "tec": 1, "der": 1}), ("lead", {"neg": 3, "der": 2, "edu": 1}),
    ]),
    (10, "single", [
        ("designer", {"tec": 3, "art": 1}), ("leader", {"neg": 3, "der": 1}),
        ("researcher", {"cie": 3, "hum": 1}), ("presenter", {"hum": 3, "art": 1, "neg": 1}),
        ("carer", {"sal": 2, "edu": 3}), ("executor", {"neg": 2, "tec": 2}),
    ]),
    (11, "scale", [
        ("1", {"art": 1, "edu": 1}), ("2", {"hum": 1, "edu": 1}),
        ("3", {"neg": 1, "sal": 1}), ("4", {"tec": 2, "neg": 2, "der": 1}),
        ("5", {"der": 3, "neg": 2, "tec": 2}),
    ]),
    (12, "scale", [
        ("1", {"hum": 2, "tur": 1}), ("2", {"edu": 1, "sal": 1}),
        ("3", {"neg": 1, "hum": 1}), ("4", {"tec": 2, "neg": 2}), ("5", {"tec": 4, "cie": 2}),
    ]),
    (13, "scale", [
        ("1", {"tec": 1, "cie": 1}), ("2", {"tec": 1, "cie": 1}),
        ("3", {"neg": 1, "sal": 1}), ("4", {"hum": 2, "edu": 2, "neg": 1}),
        ("5", {"der": 3, "edu": 3, "hum": 2}),
    ]),
    (14, "scale", [
        ("1", {"tec": 2, "cie": 2}), ("2", {"tec": 1, "cie": 1}),
        ("3", {"neg": 1, "tec": 1}), ("4", {"edu": 2, "hum": 2, "neg": 1}),
        ("5", {"sal": 3, "edu": 3, "hum": 2}),
    ]),
    (15, "single", [
        ("startup", {"tec": 3, "neg": 1}), ("hospital", {"sal": 4}),
        ("corp", {"neg": 3, "der": 1}), ("studio", {"art": 2, "der": 2, "neg": 1}),
        ("govt", {"der": 3, "edu": 2, "hum": 1}), ("ngo", {"hum": 3, "edu": 2, "amb": 1}),
        ("field", {"amb": 3, "cie": 3}), ("own_biz", {"neg": 3, "tur": 2}),
    ]),
    (16, "single", [
        ("tech_prob", {"tec": 4, "cie": 2}), ("care_people", {"sal": 4, "edu": 2}),
        ("strategy", {"neg": 4, "der": 2}), ("create_art", {"art": 4, "hum": 1}),
        ("analyze", {"cie": 4, "tec": 2}), ("teach_job", {"edu": 4, "hum": 2}),
        ("manage", {"neg": 3, "tec": 1}), ("negotiate", {"der": 3, "neg": 2}),
    ]),
    (17, "multi", [
        ("salary", {"neg": 2, "tec": 2, "der": 1}), ("impact", {"sal": 2, "edu": 2, "hum": 2}),
        ("autonomy", {"art": 3, "neg": 1}), ("stability", {"edu": 2, "der": 2, "neg": 1}),
        ("travel_work", {"tur": 3, "hum": 1}), ("growth", {"tec": 2, "cie": 2, "neg": 1}),
    ]),
    (18, "scale", [
        ("1", {"tec": 3, "cie": 3}), ("2", {"tec": 2, "cie": 1}),
        ("3", {"neg": 2, "art": 1}), ("4", {"neg": 2, "edu": 1, "hum": 1}),
        ("5", {"sal": 3, "edu": 3, "hum": 2}),
    ]),
    (19, "single", [
        ("short_proj", {"tec": 2, "neg": 2}), ("long_proj", {"tec": 2, "cie": 2, "der": 1}),
        ("ongoing", {"edu": 3, "sal": 3}), ("varied", {"art": 3, "tur": 2}),
    ]),
    (20, "single", [
        ("money", {"neg": 3, "tec": 2, "der": 1}), ("prestige", {"der": 2, "neg": 2, "sal": 1}),
        ("help", {"sal": 4, "edu": 3}), ("legacy", {"art": 4, "hum": 2}),
        ("discover", {"cie": 4, "tec": 2}), ("justice_val", {"der": 4, "hum": 3}),
        ("innovate", {"tec": 3, "art": 2, "neg": 1}),
    ]),
    (21, "scale", [
        ("1", {"neg": 2, "der": 1}), ("2", {"tec": 1, "neg": 1}),
        ("3", {"tec": 1, "sal": 1}), ("4", {"edu": 2, "hum": 1, "art": 1}),
        ("5", {"edu": 2, "hum": 2, "tur": 2}),
    ]),
    (22, "scale", [
        ("1", {"neg": 1, "tec": 1}), ("2", {"neg": 1}),
        ("3", {"cie": 1, "sal": 1}), ("4", {"amb": 2, "cie": 2}), ("5", {"amb": 4, "cie": 2}),
    ]),
    (23, "single", [
        ("income", {"neg": 3, "tec": 2, "der": 2}), ("expert", {"cie": 3, "tec": 2, "sal": 2}),
        ("community", {"edu": 3, "hum": 3, "sal": 2}), ("own_success", {"neg": 4, "tur": 2}),
        ("lasting_work", {"art": 4, "hum": 2}), ("freedom", {"neg": 2, "art": 2, "tur": 2}),
    ]),
    (24, "scale", [
        ("1", {"neg": 2, "der": 2}), ("2", {"neg": 1, "tec": 1}),
        ("3", {"neg": 1, "tec": 1}), ("4", {"sal": 2, "edu": 2}), ("5", {"sal": 3, "edu": 3, "hum": 2}),
    ]),
    (25, "single", [
        ("reading", {"hum": 3, "der": 2, "cie": 1}), ("visual", {"art": 2, "tec": 1, "neg": 1}),
        ("practical", {"tec": 3, "sal": 2, "tur": 2}), ("debate", {"der": 3, "hum": 2, "edu": 1}),
        ("experiment", {"cie": 3, "tec": 2}), ("exercises", {"tec": 2, "cie": 2, "neg": 1}),
    ]),
    (26, "single", [
        ("3yr", {"neg": 2, "tec": 1, "tur": 2}), ("5yr", {"tec": 2, "neg": 2, "hum": 2}),
        ("7yr", {"sal": 3, "der": 3, "art": 2}), ("7plus", {"sal": 4, "cie": 4, "der": 2}),
    ]),
    (27, "scale", [
        ("1", {"hum": 3, "der": 2, "cie": 2}), ("2", {"hum": 2, "cie": 1}),
        ("3", {"neg": 2, "edu": 1}), ("4", {"sal": 2, "tec": 2}), ("5", {"sal": 3, "tec": 3, "tur": 3}),
    ]),
    (28, "single", [
        ("grades", {"der": 2, "neg": 1, "hum": 1}), ("curiosity", {"cie": 3, "tec": 2, "hum": 2}),
        ("apply", {"sal": 3, "tec": 2, "tur": 2}), ("future_job", {"neg": 3, "tec": 1}),
        ("change_world", {"hum": 3, "amb": 3, "edu": 2}),
    ]),
    # 29-33 y 35 son de contexto (presupuesto, becas, región, situación, seguridad) sin peso vocacional -> features neutras
    (29, "single", [("free", {}), ("low", {}), ("mid_low", {}), ("mid", {}), ("high", {})]),
    (30, "single", [("beca_yes", {}), ("beca_maybe", {}), ("beca_no", {}), ("beca_unknown", {})]),
    (31, "single", [("lima", {}), ("arequipa", {}), ("trujillo", {}), ("cusco", {}), ("piura", {}), ("other_region", {}), ("anywhere", {})]),
    (32, "single", [("work_yes", {}), ("work_maybe", {}), ("work_no", {})]),
    (33, "single", [("5to", {}), ("egresado_sin_uni", {}), ("traslado", {}), ("padre", {})]),
    (34, "single", [
        ("prev_tec", {"tec": 1, "cie": 1}), ("prev_sal", {"sal": 1}),
        ("prev_hum", {"hum": 1, "der": 1}), ("prev_art", {"art": 1}),
        ("prev_neg", {"neg": 1}), ("no_prev", {}),
    ]),
    (35, "scale", [("1", {}), ("2", {}), ("3", {}), ("4", {}), ("5", {})]),
    (36, "single", [
        ("sal_low", {"edu": 2, "hum": 1}), ("sal_mid", {"neg": 1, "sal": 1, "hum": 1}),
        ("sal_high", {"tec": 2, "neg": 2, "der": 1}), ("sal_vhigh", {"der": 3, "neg": 3, "tec": 2}),
    ]),
    (37, "scale", [
        ("1", {"edu": 1, "neg": 1}), ("2", {"hum": 1, "sal": 1}),
        ("3", {"tec": 1, "neg": 1}), ("4", {"tec": 2, "neg": 2}), ("5", {"tec": 3, "der": 2, "cie": 2}),
    ]),
    (38, "single", [
        ("roi_fast", {"neg": 2, "tec": 2}), ("roi_mid", {"tec": 1, "neg": 1, "sal": 1}),
        ("roi_long", {"sal": 2, "der": 2}), ("roi_none", {"edu": 3, "hum": 3, "art": 2, "amb": 2}),
    ]),
    # Preguntas premium IA (101-105)
    (101, "single", [
        ("theory_first", {"cie": 3, "der": 2, "hum": 2}), ("trial_error", {"tec": 3, "neg": 2, "tur": 2}),
        ("ask_mentor", {"edu": 2, "sal": 2, "neg": 1}), ("decompose", {"tec": 3, "cie": 3}),
        ("purpose_first", {"neg": 3, "sal": 2}),
    ]),
    (102, "single", [
        ("tech_solver", {"tec": 4, "cie": 2}), ("empathetic", {"sal": 4, "edu": 3}),
        ("persuasive", {"der": 4, "neg": 3}), ("creative_rep", {"art": 4, "neg": 2}),
        ("analyzer", {"cie": 4, "tec": 2}), ("executor_rep", {"neg": 3, "tec": 2}),
    ]),
    (103, "single", [
        ("digital_culture", {"tec": 3, "art": 1}), ("arts_culture", {"art": 4, "hum": 3}),
        ("family_culture", {"edu": 3, "sal": 2}), ("nature_culture", {"amb": 4, "hum": 2}),
        ("entrepreneur_culture", {"neg": 4, "tec": 1}), ("social_culture", {"der": 4, "hum": 3}),
    ]),
    (104, "multi", [
        ("tech_gap", {"tec": 2, "edu": 3}), ("corruption", {"der": 4, "hum": 2}),
        ("health_pub", {"sal": 4, "hum": 1}), ("env_destruct", {"amb": 4, "der": 2}),
        ("jobs", {"neg": 3, "edu": 2}), ("culture_loss", {"hum": 4, "art": 2}),
    ]),
    (105, "single", [
        ("product_leader", {"neg": 3, "tec": 3}), ("nat_specialist", {"sal": 3, "der": 2, "cie": 2}),
        ("students_lead", {"edu": 5, "hum": 2}), ("eco_saved", {"amb": 5, "cie": 2}),
        ("art_museum", {"art": 5, "hum": 2}), ("law_change", {"der": 5, "hum": 3}),
        ("built", {"tec": 3, "art": 3}),
    ]),
]
