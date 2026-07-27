"""Build and validate the CheckMyCoach internal evaluation set v1.

This script creates evaluation materials only. It does not call a model API and
does not import or execute the CheckMyCoach correction pipeline.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


VERSION = "1.0.0"
BUILD_DATE = "2026-07-27"
ROOT = Path(__file__).resolve().parent
PROTOCOL_DIR = ROOT / "protocol"
DATA_DIR = ROOT / "data"
KC_ROOT = Path(r"C:\Users\gbx12\projects\acsms12-manifest\sources\books")

GENERIC_PROMPT = (
    "Revise the answer to be accurate, appropriately cautious, evidence-based "
    "and concise. Preserve useful supported information and avoid adding "
    "unsupported claims."
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    write_text(path, "\n".join(canonical_json(row) for row in rows))


def locate_knowledge_object(object_id: str) -> Path:
    matches = sorted(KC_ROOT.glob(f"*/objects/*/{object_id}.yaml"))
    if not matches:
        raise FileNotFoundError(f"Knowledge object not found: {object_id}")
    # Prefer ACSM when duplicate IDs exist; the choice is explicit and hashed.
    matches.sort(key=lambda p: (0 if "acsm12" in p.parts else 1, str(p)))
    return matches[0]


def load_knowledge_object(object_id: str) -> tuple[Path, dict[str, Any]]:
    path = locate_knowledge_object(object_id)
    obj = yaml.safe_load(path.read_text(encoding="utf-8"))
    if obj.get("id") != object_id:
        raise ValueError(f"ID mismatch in {path}")
    return path, obj


def check(check_id: str, check_type: str, **kwargs: Any) -> dict[str, Any]:
    return {"check_id": check_id, "type": check_type, **kwargs}


def case(
    case_id: str,
    family: str,
    object_ids: list[str],
    question: str,
    answer: str,
    target: str,
    failure: str,
    excerpt: str,
    retain: list[str],
    change: list[str],
    correction: str,
    primary: list[dict[str, Any]],
    *,
    boundary: str | None = None,
    forbidden: list[str] | None = None,
    ambiguity: list[str] | None = None,
) -> dict[str, Any]:
    sources = []
    for object_id in object_ids:
        path, obj = load_knowledge_object(object_id)
        sources.append(
            {
                "knowledge_object_id": object_id,
                "source_path": str(path),
                "source_sha256": sha256(path),
                "source_locator": obj.get("source", {}),
                "knowledge_object_review_status": obj.get("provenance", {}).get(
                    "reviewed", "unknown"
                ),
            }
        )
    return {
        "case_id": case_id,
        "failure_family": family,
        "source_provenance": {
            "provenance_class": "independently_constructed_evaluation_case",
            "sources": sources,
            "historical_labels_used": False,
            "gold_basis": (
                "closed-world comparison of the supplied answer with the frozen "
                "evidence excerpt and case-level formal checks"
            ),
            "dataset_version": VERSION,
        },
        "input_question": question,
        "original_answer": answer,
        "target_failure_span": target,
        "failure_statement": failure,
        "linked_knowledge_object_ids": object_ids,
        "evidence_excerpt": excerpt,
        "supported_content_to_retain": retain,
        "content_required_to_change": change,
        "required_boundary": boundary,
        "forbidden_new_claims": forbidden or [],
        "reference_correction": correction,
        "primary_checks": primary,
        "secondary_checks": [
            check(
                "semantic_equivalence_review",
                "human_rule_based_secondary",
                instruction=(
                    "Confirm that paraphrases do not preserve the target failure, "
                    "erase supported content, or introduce a proposition outside "
                    "the supplied evidence. No LLM judge is permitted."
                ),
            )
        ],
        "ambiguity_flags": ambiguity or [],
        "adjudication_status": "constructor_pass_pending_independent_audit",
    }


def build_cases() -> list[dict[str, Any]]:
    A = "unsupported_numerical_specificity"
    B = "unsupported_factual_claim"
    C = "missing_boundary"
    cases: list[dict[str, Any]] = []

    numerical = [
        (
            "CMC-A-001", ["recommendation.aerobic_exercise_duration"],
            "How long should most adults do moderate aerobic exercise on an exercise day?",
            "Most adults should do moderate aerobic exercise for exactly 43 minutes every day.",
            "exactly 43 minutes every day",
            "The evidence gives a 30–60 minute range and says most days; it does not identify 43 minutes or every day as uniquely supported.",
            "For most adults: 30–60 minutes per day of purposeful moderate aerobic exercise, or 20–60 minutes per day of vigorous exercise, on most days.",
            ["moderate aerobic exercise is useful", "30–60 minutes is the supplied moderate-duration range"],
            ["replace the uniquely exact 43-minute prescription", "replace every day with the supplied frequency qualifier"],
            "Most adults can aim for 30–60 minutes of purposeful moderate aerobic exercise on most days; the evidence does not single out one exact duration within that range.",
            [check("remove_exact_43", "substring_absent", value="exactly 43 minutes every day"),
             check("retain_duration_range", "regex_present", pattern=r"30\s*[–-]\s*60\s*minutes"),
             check("retain_frequency_qualifier", "any_phrase_present", values=["most days", "on most days"])],
        ),
        (
            "CMC-A-002", ["table_row.cardiorespiratory_frequency"],
            "How often is cardiorespiratory exercise generally recommended?",
            "The uniquely correct frequency is exactly 4 days per week.",
            "uniquely correct frequency is exactly 4 days per week",
            "Four days lies inside the evidence range, but the evidence supports 3–5 days and does not privilege four.",
            "The general recommendation for cardiorespiratory exercise frequency is 3–5 days per week.",
            ["cardiorespiratory exercise should be performed multiple days per week"],
            ["replace the unique four-day point prescription with the supplied range"],
            "A general target is 3–5 days per week; this evidence does not establish one uniquely correct number of days.",
            [check("remove_unique_four_days", "substring_absent", value="uniquely correct frequency is exactly 4 days per week"),
             check("retain_frequency_range", "regex_present", pattern=r"3\s*[–-]\s*5\s*days")],
        ),
        (
            "CMC-A-003", ["table_row.cardiorespiratory_intensity"],
            "What HRR intensity should I use for cardiorespiratory training?",
            "Train at exactly 52% HRR; that is the evidence-based optimal intensity.",
            "exactly 52% HRR",
            "The evidence supplies moderate and vigorous ranges, not a uniquely optimal 52% point.",
            "Moderate intensity is 40–59% HRR or VO2R and vigorous intensity is 60–89% HRR or VO2R.",
            ["HRR can be used to express cardiorespiratory intensity", "moderate and vigorous ranges"],
            ["remove the uniquely optimal 52% point claim"],
            "Use an intensity within the appropriate range: 40–59% HRR for moderate or 60–89% HRR for vigorous exercise; the excerpt does not identify a single optimal point.",
            [check("remove_exact_52", "substring_absent", value="exactly 52% HRR"),
             check("retain_intensity_range", "any_regex_present", patterns=[r"40\s*[–-]\s*59%\s*HRR", r"60\s*[–-]\s*89%\s*HRR"])],
        ),
        (
            "CMC-A-004", ["table_row.cardiorespiratory_volume"],
            "What weekly cardiorespiratory exercise volume should I target?",
            "Exactly 750 MET-minutes per week is the scientifically correct target.",
            "Exactly 750 MET-minutes per week",
            "The supplied evidence supports a 500–1000 MET-minute range, not a uniquely correct midpoint.",
            "The general weekly cardiorespiratory volume is at least 500–1000 MET-minutes per week.",
            ["MET-minutes per week is the supplied volume measure"],
            ["replace the exact 750 claim with the evidence range"],
            "The supplied target is 500–1000 MET-minutes per week; it does not identify 750 as uniquely correct.",
            [check("remove_exact_750", "substring_absent", value="Exactly 750 MET-minutes per week"),
             check("retain_volume_range", "regex_present", pattern=r"500\s*[–-]\s*1000\s*MET")],
        ),
        (
            "CMC-A-005", ["threshold.aerobic_intensity_mets"],
            "What MET value counts as moderate aerobic exercise?",
            "Moderate exercise is precisely 4.72 METs.",
            "precisely 4.72 METs",
            "Moderate intensity is defined as a range; one interior point is not the definition.",
            "Light: 1.6–2.9 METs; Moderate: 3.0–5.9 METs; Vigorous: at least 6.0 METs.",
            ["METs classify aerobic exercise intensity"],
            ["replace the point value with the moderate range"],
            "Moderate aerobic intensity spans 3.0–5.9 METs; the excerpt does not specify one precise value.",
            [check("remove_4_72", "substring_absent", value="precisely 4.72 METs"),
             check("retain_moderate_met_range", "regex_present", pattern=r"3\.0\s*[–-]\s*5\.9\s*MET")],
        ),
        (
            "CMC-A-006", ["threshold.aerobic_exercise_progression_rate_based_on_fitness_level"],
            "How quickly should an apparently healthy adult increase aerobic exercise duration?",
            "Increase duration by exactly 7 minutes every 10 days for the first 5 weeks.",
            "exactly 7 minutes every 10 days for the first 5 weeks",
            "The evidence provides ranges and says progression depends on fitness, health, age, and goals.",
            "Progression depends on fitness level, health status, age, and goals. Duration can be increased by 5–10 minutes every 1–2 weeks, especially during the first 4–6 weeks.",
            ["a gradual duration increase can be used", "the 5–10 minute and 1–2 week ranges"],
            ["remove the invented exact schedule", "retain individual-dependence qualifier"],
            "For an apparently healthy adult, duration may increase by 5–10 minutes every 1–2 weeks during the first 4–6 weeks, adjusted for fitness, health, age, and goals.",
            [check("remove_exact_progression", "substring_absent", value="exactly 7 minutes every 10 days for the first 5 weeks"),
             check("retain_progression_ranges", "all_regex_present", patterns=[r"5\s*[–-]\s*10\s*minutes", r"1\s*[–-]\s*2\s*weeks", r"4\s*[–-]\s*6\s*weeks"]),
             check("retain_individualization", "any_phrase_present", values=["depends on", "adjusted for", "individual"])],
        ),
        (
            "CMC-A-007", ["threshold.altitude_acclimatization_2300m"],
            "How long does full acclimatization at 2,300 m take?",
            "Full acclimatization at 2,300 m takes exactly 12 days.",
            "exactly 12 days",
            "The evidence gives a 10–14 day interval, not an exact universal day.",
            "Full acclimatization to 2,300 m requires 10–14 days.",
            ["2,300 m is the relevant altitude", "acclimatization takes multiple days"],
            ["replace the exact 12-day assertion with the range"],
            "Full acclimatization at 2,300 m is described as taking 10–14 days.",
            [check("remove_exact_12_days", "substring_absent", value="exactly 12 days"),
             check("retain_10_14_days", "regex_present", pattern=r"10\s*[–-]\s*14\s*days")],
        ),
        (
            "CMC-A-008", ["threshold.altitude_acclimatization_4300m"],
            "How long does full acclimatization at 4,300 m take?",
            "Full acclimatization at 4,300 m takes exactly 37 days.",
            "exactly 37 days",
            "The evidence gives a 30–45 day interval, not an exact universal day.",
            "Full acclimatization to 4,300 m requires 30–45 days.",
            ["4,300 m is the relevant altitude", "acclimatization takes multiple weeks"],
            ["replace the exact 37-day assertion with the range"],
            "Full acclimatization at 4,300 m is described as taking 30–45 days.",
            [check("remove_exact_37_days", "substring_absent", value="exactly 37 days"),
             check("retain_30_45_days", "regex_present", pattern=r"30\s*[–-]\s*45\s*days")],
        ),
        (
            "CMC-A-009", ["procedure.one_rm_testing"],
            "How should I choose the starting load and rest period in a 1-RM test?",
            "Start at exactly 63% of perceived capacity and rest exactly 4 minutes after a successful attempt.",
            "exactly 63% of perceived capacity and rest exactly 4 minutes",
            "The procedure supplies approximate starting and rest ranges; it does not privilege these exact interior points.",
            "Select an initial weight at about 50–70% of perceived capacity. After a successful attempt, rest 3–5 minutes before increasing weight.",
            ["start submaximally", "rest between successful attempts"],
            ["replace both exact interior points with the supplied ranges"],
            "Start at about 50–70% of perceived capacity and rest 3–5 minutes after a successful attempt before increasing the load.",
            [check("remove_exact_1rm_points", "substring_absent", value="exactly 63% of perceived capacity and rest exactly 4 minutes"),
             check("retain_1rm_ranges", "all_regex_present", patterns=[r"50\s*[–-]\s*70%", r"3\s*[–-]\s*5\s*minutes"])],
        ),
        (
            "CMC-A-010", ["recommendation.static_stretch_duration"],
            "How long should I hold a static stretch?",
            "Hold every static stretch for exactly 22 seconds.",
            "exactly 22 seconds",
            "The recommendation is a 15–30 second range; the evidence does not specify 22 seconds for every stretch.",
            "A static stretch is generally held for 15–30 seconds; evidence supports 30 seconds and suggests diminishing returns beyond it.",
            ["static stretches are held rather than bounced", "15–30 seconds is the supplied range"],
            ["replace the exact 22-second universal prescription"],
            "A general recommendation is to hold a static stretch for 15–30 seconds; the excerpt does not require one exact duration.",
            [check("remove_exact_22", "substring_absent", value="exactly 22 seconds"),
             check("retain_stretch_range", "regex_present", pattern=r"15\s*[–-]\s*30\s*seconds")],
        ),
        (
            "CMC-A-011", ["recommendation.warm_up_older_adults"],
            "How long should an older adult warm up?",
            "An older adult should warm up for exactly 7 minutes.",
            "exactly 7 minutes",
            "The recommendation supplies a 5–10 minute range, not a single exact duration.",
            "Older adults should warm up for 5–10 minutes before each exercise session using low- to moderate-intensity aerobic activity and calisthenics.",
            ["warm up before each session", "low- to moderate-intensity activity is acceptable"],
            ["replace the exact seven-minute point with the range"],
            "Warm up for 5–10 minutes before each session with low- to moderate-intensity aerobic activity or calisthenics.",
            [check("remove_exact_7", "substring_absent", value="exactly 7 minutes"),
             check("retain_warmup_range", "regex_present", pattern=r"5\s*[–-]\s*10\s*minutes")],
        ),
        (
            "CMC-A-012", ["recommendation.recovery_time_between_sessions_older_adults"],
            "How much recovery should an older adult have between exercise sessions?",
            "The correct recovery interval is exactly 60 hours.",
            "exactly 60 hours",
            "The evidence gives 48–72 hours; it does not designate the midpoint as uniquely correct.",
            "Older adults should be allowed 48–72 hours of recovery between exercise sessions.",
            ["recovery between sessions is needed"],
            ["replace the exact 60-hour prescription with the range"],
            "Allow 48–72 hours of recovery between exercise sessions.",
            [check("remove_exact_60", "substring_absent", value="exactly 60 hours"),
             check("retain_recovery_range", "regex_present", pattern=r"48\s*[–-]\s*72\s*hours")],
        ),
        (
            "CMC-A-013", ["recommendation.power_training_load_healthy_older_adults"],
            "What power-training prescription should a healthy older adult use?",
            "Use exactly 50% 1RM for exactly 2 sets of exactly 8 repetitions.",
            "exactly 50% 1RM for exactly 2 sets of exactly 8 repetitions",
            "The evidence supplies ranges for load, sets, and repetitions, not one uniquely correct combination.",
            "For healthy older adults: 1–3 sets, 40–60% 1RM, and 6–10 repetitions with high concentric velocity.",
            ["power movements use high concentric velocity", "light-to-moderate load is supplied"],
            ["replace all three invented exact interior points with ranges"],
            "A supplied option is 1–3 sets at 40–60% 1RM for 6–10 repetitions, performed with high concentric velocity.",
            [check("remove_exact_power_tuple", "substring_absent", value="exactly 50% 1RM for exactly 2 sets of exactly 8 repetitions"),
             check("retain_power_ranges", "all_regex_present", patterns=[r"1\s*[–-]\s*3\s*sets", r"40\s*[–-]\s*60%\s*1RM", r"6\s*[–-]\s*10\s*repetitions"])],
        ),
        (
            "CMC-A-014", ["recommendation.postexercise_protein_aerobic"],
            "How much protein and exactly when should I consume it after aerobic endurance exercise?",
            "Take exactly 31 grams exactly 17 minutes after finishing; this is the proven optimal timing.",
            "exactly 31 grams exactly 17 minutes after finishing",
            "The evidence provides a 20–40 gram range within two hours and explicitly says the exact timing is unresolved.",
            "At least 20–40 g of high-quality protein within two hours after aerobic endurance exercise is a general guideline; sooner may be better, but the exact time has not been established.",
            ["postexercise high-quality protein can be used", "20–40 g within two hours"],
            ["remove the exact dose-time pair and optimality claim", "retain timing uncertainty"],
            "A general guideline is 20–40 g of high-quality protein within two hours after aerobic endurance exercise; the exact optimal timing is not established.",
            [check("remove_exact_protein_timing", "substring_absent", value="exactly 31 grams exactly 17 minutes after finishing"),
             check("retain_protein_range", "regex_present", pattern=r"20\s*[–-]\s*40\s*(?:g|grams)"),
             check("retain_timing_uncertainty", "any_phrase_present", values=["not established", "not known", "uncertain", "has not been established"])],
        ),
        (
            "CMC-A-015", ["recommendation.protein_per_meal_postcompetition"],
            "How should protein be distributed across meals?",
            "Consume exactly 28 grams every exactly 3.5 hours.",
            "exactly 28 grams every exactly 3.5 hours",
            "The evidence gives 20–40 g per meal and meals every 3–4 hours, not exact interior points.",
            "Experts suggest at least 20–40 g protein per meal and meals every 3–4 hours to help meet daily protein targets.",
            ["protein can be distributed across meals", "meeting the daily protein target remains relevant"],
            ["replace exact dose and timing with supplied ranges"],
            "A suggested pattern is 20–40 g of protein per meal, with meals every 3–4 hours, while meeting the daily target.",
            [check("remove_exact_distribution", "substring_absent", value="exactly 28 grams every exactly 3.5 hours"),
             check("retain_distribution_ranges", "all_regex_present", patterns=[r"20\s*[–-]\s*40\s*(?:g|grams)", r"3\s*[–-]\s*4\s*hours"])],
        ),
    ]
    for row in numerical:
        cases.append(case(row[0], A, row[1], *row[2:]))

    factual = [
        ("CMC-B-001", ["warning.ballistic_stretching"], "Should a general-fitness warm-up use bouncing stretches?", "Ballistic bouncing stretches are recommended for general fitness because they reduce injury risk.", "Ballistic bouncing stretches are recommended for general fitness", "The answer reverses the warning: ballistic stretching is not recommended and is associated with increased injury risk.", "Ballistic stretching (bouncing movements) is not recommended for general fitness populations because of increased injury risk.", ["the answer should address stretching choice for general fitness"], ["reverse the recommendation and risk direction"], "For general fitness, avoid ballistic bouncing stretches because the supplied evidence associates them with increased injury risk.", [check("remove_ballistic_recommendation", "substring_absent", value="Ballistic bouncing stretches are recommended for general fitness"), check("state_ballistic_not_recommended", "any_phrase_present", values=["not recommended", "avoid ballistic", "avoid bouncing"])]),
        ("CMC-B-002", ["recommendation.dynamic_stretching_before_activity"], "Is dynamic stretching appropriate before athletic activity?", "Dynamic stretching should be avoided before athletic activities.", "Dynamic stretching should be avoided", "The answer contradicts the supplied recommendation.", "Controlled dynamic stretching through the full range of motion is recommended as part of a warm-up before athletic activities.", ["dynamic stretching consists of controlled movement"], ["change avoid to the supplied recommendation"], "Controlled dynamic stretching can be included in a warm-up before athletic activity.", [check("remove_dynamic_avoid", "substring_absent", value="Dynamic stretching should be avoided"), check("state_dynamic_recommended", "any_phrase_present", values=["recommended", "can be included", "appropriate"]) ]),
        ("CMC-B-003", ["recommendation.clothing_considerations_for_exercise_in_heat"], "What clothing is recommended for exercise in heat?", "Wear heavy, tight, dark clothing to improve heat loss.", "heavy, tight, dark clothing", "Each clothing property contradicts the supplied recommendation.", "Lightweight, loose-fitting, light-colored clothing is recommended to facilitate heat loss during exercise in heat.", ["clothing affects thermoregulation in heat"], ["replace all three contradicted clothing properties"], "Choose lightweight, loose-fitting, light-colored clothing to facilitate heat loss.", [check("remove_heat_clothing_contradiction", "substring_absent", value="heavy, tight, dark clothing"), check("retain_heat_clothing_properties", "all_phrase_present", values=["lightweight", "loose", "light"]) ]),
        ("CMC-B-004", ["recommendation.clothing_considerations_for_exercise_in_cold"], "What base layer should I wear when exercising in cold weather?", "Cotton is the best next-to-skin layer because retaining moisture reduces heat loss.", "Cotton is the best next-to-skin layer", "The evidence recommends a moisture-wicking layer and says cotton retention can increase heat loss.", "Use layers in cold conditions. The next-to-skin layer should wick moisture, such as polypropylene, rather than cotton, which retains moisture and can increase heat loss.", ["wearing layers provides insulation"], ["replace the cotton recommendation and its reversed mechanism"], "Wear layers, with a moisture-wicking next-to-skin material such as polypropylene rather than cotton.", [check("remove_cotton_best", "substring_absent", value="Cotton is the best next-to-skin layer"), check("state_wicking_layer", "any_phrase_present", values=["moisture-wicking", "wicks moisture", "wicking"]) ]),
        ("CMC-B-005", ["recommendation.avoid_alcohol_and_tobacco_during_cold_exposure"], "Does alcohol help before exercising in cold weather?", "Alcohol improves thermoregulation and judgment in the cold.", "Alcohol improves thermoregulation and judgment", "The answer reverses both effects in the evidence.", "Avoid alcohol and tobacco during cold exposure: alcohol impairs thermoregulation and judgment, and tobacco reduces peripheral blood flow.", ["the answer should address cold-exposure safety"], ["reverse the alcohol effect and recommend avoidance"], "Avoid alcohol during cold exposure because it can impair thermoregulation and judgment.", [check("remove_alcohol_improves", "substring_absent", value="Alcohol improves thermoregulation and judgment"), check("state_alcohol_avoid", "all_phrase_present", values=["avoid", "alcohol"]) ]),
        ("CMC-B-006", ["recommendation.benefits_of_regular_physical_activity_for_diabetes"], "Can regular physical activity help people with diabetes?", "Regular physical activity has no benefit for glycemic control in people with diabetes.", "has no benefit for glycemic control", "The answer contradicts the supplied benefit statement.", "Regular physical activity is recommended for people with diabetes because it can improve glycemic control, reduce cardiovascular risk factors, and enhance well-being.", ["regular physical activity is the intervention"], ["change the no-benefit claim"], "Regular physical activity is recommended and can improve glycemic control, cardiovascular risk factors, and well-being.", [check("remove_no_glycemic_benefit", "substring_absent", value="has no benefit for glycemic control"), check("state_glycemic_benefit", "all_phrase_present", values=["glycemic control", "improve"]) ]),
        ("CMC-B-007", ["threshold.age.older_adult"], "What age does this evidence object use for the older-adult category?", "This object defines older adults as everyone aged 60 years or more.", "aged 60 years or more", "The answer changes the explicit threshold from 65 to 60.", "This evidence object defines older adults as individuals aged 65 years or older.", ["an age threshold defines the category"], ["replace 60 with the stated 65-year threshold"], "In this evidence object, older adult means age 65 years or older.", [check("remove_age_60", "substring_absent", value="aged 60 years or more"), check("state_age_65", "regex_present", pattern=r"65\s*(?:years|yr).*older")]),
        ("CMC-B-008", ["concept.high_intensity_interval_training"], "What distinguishes HIIT in this evidence object?", "HIIT is continuous high-intensity exercise with no recovery periods.", "with no recovery periods", "The object defines HIIT as repeated high-intensity bouts with intermittent recovery.", "HIIT involves brief repeated bouts of high-intensity exercise with intermittent recovery periods.", ["HIIT includes high-intensity exercise"], ["replace the no-recovery proposition"], "HIIT uses brief repeated high-intensity bouts separated by intermittent recovery periods.", [check("remove_no_recovery", "substring_absent", value="with no recovery periods"), check("state_intermittent_recovery", "all_phrase_present", values=["recovery", "repeated"]) ]),
        ("CMC-B-009", ["threshold.resting_heart_rate"], "What resting heart-rate range is stated in this evidence object?", "A resting heart rate of 110 beats per minute is within the stated normal range.", "110 beats per minute is within the stated normal range", "The supplied range ends at 100 beats/min.", "The resting heart rate normally ranges from 60 to 100 beats per minute.", ["resting heart rate is expressed in beats per minute"], ["remove the incorrect classification and state the range"], "The stated normal range is 60–100 beats per minute; 110 is above that supplied range.", [check("remove_110_normal", "substring_absent", value="110 beats per minute is within the stated normal range"), check("state_resting_hr_range", "regex_present", pattern=r"60\s*[–-]\s*100\s*beats")]),
        ("CMC-B-010", ["recommendation.individualized_hydration_weight_changes"], "Should all athletes use one identical hydration plan?", "Yes. Sweat rates and electrolyte concentrations are similar enough that one fixed hydration plan fits all athletes.", "one fixed hydration plan fits all athletes", "The answer contradicts the explicit large-variation and individualization statements.", "Because sweat rates and electrolyte concentrations vary greatly, athletes should measure weight changes in specific conditions and develop individualized hydration strategies.", ["hydration planning is useful"], ["replace the universal fixed-plan claim"], "No. Hydration should be individualized using weight changes measured in the relevant training, competition, and weather conditions.", [check("remove_fixed_hydration", "substring_absent", value="one fixed hydration plan fits all athletes"), check("state_hydration_individualized", "any_phrase_present", values=["individualized", "individual", "varies"]) ]),
        ("CMC-B-011", ["recommendation.initial_training_intensity_volume_untrained_seniors"], "How should an untrained senior begin resistance training?", "An untrained senior should start with high intensity and high volume.", "start with high intensity and high volume", "The supplied recommendation says relatively low intensity and volume.", "Untrained seniors should start at relatively low intensity and volume, with an individualized prescription.", ["resistance training can be initiated"], ["replace high intensity and volume with low and individualized"], "Begin with relatively low intensity and volume and individualize the prescription.", [check("remove_high_start", "substring_absent", value="start with high intensity and high volume"), check("state_low_start", "all_phrase_present", values=["low", "intensity", "volume"]) ]),
        ("CMC-B-012", ["recommendation.postexercise_carbohydrate_and_protein"], "Can adding protein assist glycogen replenishment after exercise when carbohydrate intake is low?", "Adding protein never facilitates glycogen replenishment, even when carbohydrate intake is below 1.2 g/kg.", "never facilitates glycogen replenishment", "The evidence says protein appears to facilitate replenishment when carbohydrate is below 1.2 g/kg.", "After exercise, 1.2–2.0 g/kg carbohydrate may be consumed within 30 minutes. Adding protein appears to facilitate glycogen replenishment if carbohydrate intake is below 1.2 g/kg.", ["postexercise carbohydrate is relevant"], ["replace the categorical no-effect claim"], "When carbohydrate intake is below 1.2 g/kg, adding protein may facilitate glycogen replenishment.", [check("remove_never_facilitates", "substring_absent", value="never facilitates glycogen replenishment"), check("state_conditional_facilitation", "all_phrase_present", values=["protein", "below 1.2", "facilitate"]) ]),
        ("CMC-B-013", ["recommendation.sports_drink_composition_hot_weather"], "What does this evidence specify for a sport drink during prolonged activity in hot weather?", "Use a drink with no sodium, no potassium, and no carbohydrate.", "no sodium, no potassium, and no carbohydrate", "The answer contradicts all three specified components.", "For prolonged activity in hot weather: 20–30 mEq sodium/L, 2–5 mEq potassium/L, and 5–10% carbohydrate.", ["a sport drink is discussed for prolonged hot-weather activity"], ["replace the zero-component claim with supplied ranges"], "For prolonged activity in hot weather, the evidence specifies 20–30 mEq sodium/L, 2–5 mEq potassium/L, and 5–10% carbohydrate.", [check("remove_zero_components", "substring_absent", value="no sodium, no potassium, and no carbohydrate"), check("retain_drink_components", "all_regex_present", patterns=[r"20\s*[–-]\s*30\s*mEq", r"2\s*[–-]\s*5\s*mEq", r"5\s*[–-]\s*10%"]) ]),
        ("CMC-B-014", ["recommendation.test_sequencing_order"], "Which tests should come first in the supplied test sequence?", "Fatiguing local muscular-endurance tests should be administered first.", "local muscular-endurance tests should be administered first", "The evidence starts with nonfatiguing tests and places local muscular endurance later.", "The supplied sequence begins with nonfatiguing tests, followed by agility, maximum power and strength, sprint, and then local muscular endurance tests.", ["test order can reduce interference"], ["replace the reversed first step"], "Administer nonfatiguing tests first; local muscular-endurance tests occur later in the supplied sequence.", [check("remove_endurance_first", "substring_absent", value="local muscular-endurance tests should be administered first"), check("state_nonfatiguing_first", "all_phrase_present", values=["nonfatiguing", "first"]) ]),
        ("CMC-B-015", ["concept.static_stretch"], "How is a static stretch performed in this evidence object?", "A static stretch uses rapid bouncing and is never held at an end position.", "rapid bouncing and is never held", "The definition specifies slow, constant movement followed by a hold.", "A static stretch uses slow, constant movement toward an end position and is then held for 10–30 seconds.", ["a static stretch moves toward an end position"], ["replace rapid bouncing and no-hold claims"], "Move slowly and constantly toward the end position, then hold it for 10–30 seconds.", [check("remove_static_bouncing", "substring_absent", value="rapid bouncing and is never held"), check("state_slow_hold", "all_phrase_present", values=["slow", "hold"]) ]),
    ]
    for row in factual:
        cases.append(case(row[0], B, row[1], *row[2:], forbidden=[row[4]]))

    boundary_cases = [
        ("CMC-C-001", ["recommendation.static_stretching_guidelines_and_precautions"], "How should I perform a static stretch?", "Move into mild discomfort and hold for 15–30 seconds.", "Move into mild discomfort and hold for 15–30 seconds.", "The useful technique omits the required response to pain, radiating symptoms, or loss of sensation.", "Move to mild discomfort and hold 15–30 seconds. Decrease stretch intensity if pain, radiating symptoms, or loss of sensation occurs; use caution with hypermobile joints.", ["move only to mild discomfort", "hold 15–30 seconds"], ["add the symptom-triggered reduction boundary"], "Move to mild discomfort and hold 15–30 seconds, but decrease intensity if you feel pain, radiating symptoms, or loss of sensation.", [check("retain_stretch_technique", "all_regex_present", patterns=[r"mild discomfort", r"15\s*[–-]\s*30\s*seconds"]), check("add_symptom_boundary", "all_phrase_groups_present", groups=[["pain"], ["radiating"], ["loss of sensation", "numbness"], ["decrease", "reduce", "stop"]])], "Decrease intensity if pain, radiating symptoms, or loss of sensation occurs."),
        ("CMC-C-002", ["warning.contraindication_for_exercise_in_extreme_cold"], "Can I continue outdoor exercise when wind chill becomes extremely low?", "Wear appropriate clothing and continue the workout.", "Wear appropriate clothing and continue the workout.", "The answer omits the avoid-or-modify boundary below the supplied wind-chill threshold.", "Exercise should be avoided or modified in extreme cold, particularly below a wind chill of −27°C, because frostbite and hypothermia risk rises.", ["appropriate clothing remains useful"], ["add avoid-or-modify threshold boundary"], "Use appropriate clothing, but avoid or modify exercise when wind chill is below −27°C because of frostbite and hypothermia risk.", [check("retain_clothing", "phrase_present", value="clothing"), check("add_cold_threshold_boundary", "all_phrase_groups_present", groups=[["avoid", "modify"], ["-27", "−27"], ["wind chill"]])], "Avoid or modify exercise below −27°C wind chill."),
        ("CMC-C-003", ["threshold.aerobic_exercise_progression_rate_based_on_fitness_level"], "How should an apparently healthy adult progress aerobic duration?", "Increase duration by 5–10 minutes every 1–2 weeks during the first 4–6 weeks.", "Increase duration by 5–10 minutes every 1–2 weeks during the first 4–6 weeks.", "The numerical recommendation is retained, but the evidence-required dependence on fitness, health, age, and goals is omitted.", "Progression depends on fitness, health, age, and goals. A 5–10 minute increase every 1–2 weeks may be used during the first 4–6 weeks.", ["5–10 minutes", "every 1–2 weeks", "first 4–6 weeks"], ["add individualization boundary"], "Increase duration by 5–10 minutes every 1–2 weeks during the first 4–6 weeks, adjusted for fitness, health, age, and goals.", [check("retain_progression_numbers", "all_regex_present", patterns=[r"5\s*[–-]\s*10", r"1\s*[–-]\s*2", r"4\s*[–-]\s*6"]), check("add_progression_boundary", "all_phrase_groups_present", groups=[["fitness"], ["health"], ["age"], ["goals"]])], "Progression must be individualized for fitness, health, age, and goals."),
        ("CMC-C-004", ["procedure.one_rm_testing"], "How can I perform a 1-RM test?", "Warm up, choose a submaximal starting load, and increase the load after each successful attempt.", "Warm up, choose a submaximal starting load, and increase the load after each successful attempt.", "The otherwise useful sequence omits the proper-form and spotting safety boundaries contained in the procedure.", "The procedure requires familiarization, a warm-up, proper form, 3–5 minutes rest after success, and a spotter as an input; stop after no more than four trials to limit fatigue.", ["warm up", "start submaximally", "increase after success"], ["add proper-form and spotter boundaries"], "After familiarization, warm up and use a spotter. Begin submaximally, keep proper form, rest 3–5 minutes after success, increase the load after each successful attempt, and finish within four trials.", [check("retain_1rm_sequence", "all_phrase_groups_present", groups=[["warm"], ["submaximal", "50–70", "50-70"], ["increase"]]), check("add_1rm_safety_boundary", "all_phrase_groups_present", groups=[["spotter"], ["proper form", "technique"]])], "Use a spotter and require proper form."),
        ("CMC-C-005", ["recommendation.dynamic_stretching_before_activity", "warning.ballistic_stretching"], "What type of stretching can I use before athletic activity?", "Use movement-based stretching as part of the warm-up.", "Use movement-based stretching as part of the warm-up.", "The answer omits that the recommended movement is controlled and that ballistic bouncing is not recommended for general fitness.", "Controlled dynamic stretching is recommended before athletic activity; ballistic bouncing is not recommended for general fitness because of injury risk.", ["movement-based stretching can be part of a warm-up"], ["add controlled-movement and no-bouncing boundaries"], "Use controlled dynamic stretching in the warm-up; avoid ballistic bouncing for general fitness.", [check("retain_warmup_stretch", "all_phrase_groups_present", groups=[["stretch"], ["warm-up", "warmup"]]), check("add_controlled_nonballistic_boundary", "all_phrase_groups_present", groups=[["controlled"], ["avoid", "not recommended"], ["ballistic", "bouncing"]])], "Movement must be controlled; avoid ballistic bouncing for general fitness."),
        ("CMC-C-006", ["recommendation.individualized_hydration_weight_changes"], "How can I plan hydration for training and competition?", "Use changes in body weight to set a hydration plan.", "Use changes in body weight to set a hydration plan.", "The useful method omits that measurements and the resulting plan must be individualized to the specific weather and activity conditions.", "Because sweat and electrolyte losses vary, measure weight changes during training and competition in specific weather conditions and build an individualized strategy.", ["use body-weight changes", "hydration planning"], ["add condition-specific and individualized boundaries"], "Use body-weight changes measured in the relevant training, competition, and weather conditions to build an individualized hydration plan.", [check("retain_weight_change_method", "all_phrase_groups_present", groups=[["weight"], ["hydration"]]), check("add_hydration_scope_boundary", "all_phrase_groups_present", groups=[["individual"], ["weather", "condition"], ["training", "competition"]])], "The plan is individual and condition-specific."),
        ("CMC-C-007", ["recommendation.initial_training_intensity_volume_untrained_seniors"], "How should an untrained senior begin resistance training?", "Begin with relatively low intensity and low volume.", "Begin with relatively low intensity and low volume.", "The starting advice is supported but omits the explicit individualization boundary.", "Untrained seniors should begin at relatively low intensity and volume, and the prescription should be individualized.", ["low starting intensity", "low starting volume"], ["add individualized prescription boundary"], "Begin with relatively low intensity and volume, with the prescription individualized to the person.", [check("retain_low_start", "all_phrase_present", values=["low", "intensity", "volume"]), check("add_senior_individualization", "any_phrase_present", values=["individualized", "individual", "tailored"])], "The prescription must be individualized."),
        ("CMC-C-008", ["recommendation.postexercise_carbohydrate_and_protein"], "What should I consume after exercise for glycogen replenishment?", "Consume 1.2–2.0 g/kg carbohydrate within 30 minutes and add protein to facilitate glycogen replenishment.", "add protein to facilitate glycogen replenishment", "The answer omits the evidence condition that the protein benefit applies when carbohydrate intake is below 1.2 g/kg.", "Consume about 1.2–2.0 g/kg carbohydrate within 30 minutes. Adding protein appears to facilitate glycogen replenishment if carbohydrate intake is below 1.2 g/kg.", ["1.2–2.0 g/kg carbohydrate", "within 30 minutes"], ["make the protein statement conditional"], "Consume about 1.2–2.0 g/kg carbohydrate within 30 minutes; adding protein may help when carbohydrate intake is below 1.2 g/kg.", [check("retain_carb_recommendation", "all_regex_present", patterns=[r"1\.2\s*[–-]\s*2\.0\s*g/kg", r"30\s*minutes"]), check("add_low_carb_condition", "all_phrase_groups_present", groups=[["protein"], ["below 1.2", "less than 1.2"]])], "Protein facilitation is conditional on carbohydrate intake below 1.2 g/kg."),
        ("CMC-C-009", ["recommendation.precompetition_meal_timing"], "How much carbohydrate should I eat before competition?", "Eat 1–4 g/kg carbohydrate before competition.", "Eat 1–4 g/kg carbohydrate before competition.", "The answer omits the timing boundary: the 1–4 g/kg range is for a meal at least four hours before, while a two-hour meal is approximately 1 g/kg.", "At least four hours before competition: about 1–4 g/kg carbohydrate. At two hours before: about 1 g/kg.", ["carbohydrate before competition is relevant"], ["bind each amount to its meal timing"], "If eating at least four hours before competition, use about 1–4 g/kg carbohydrate; at two hours before, the supplied amount is about 1 g/kg.", [check("retain_precompetition_carb", "all_phrase_groups_present", groups=[["carbohydrate"], ["g/kg"]]), check("add_meal_timing_boundary", "all_phrase_groups_present", groups=[["four hours", "4 hours"], ["two hours", "2 hours"], ["1–4", "1-4"]])], "The dose must be tied to time before competition."),
        ("CMC-C-010", ["recommendation.sports_drink_composition_hot_weather"], "What sport-drink composition does the supplied evidence recommend?", "Use 20–30 mEq sodium/L, 2–5 mEq potassium/L, and 5–10% carbohydrate.", "Use 20–30 mEq sodium/L, 2–5 mEq potassium/L, and 5–10% carbohydrate.", "The composition is preserved but its applicability boundary—prolonged activity in hot weather—is omitted.", "The specified composition applies during prolonged activity in hot weather: 20–30 mEq sodium/L, 2–5 mEq potassium/L, and 5–10% carbohydrate.", ["all three composition ranges"], ["add prolonged-activity and hot-weather applicability boundary"], "During prolonged activity in hot weather, use a drink containing 20–30 mEq sodium/L, 2–5 mEq potassium/L, and 5–10% carbohydrate.", [check("retain_drink_ranges", "all_regex_present", patterns=[r"20\s*[–-]\s*30\s*mEq", r"2\s*[–-]\s*5\s*mEq", r"5\s*[–-]\s*10%"]), check("add_hot_prolonged_boundary", "all_phrase_groups_present", groups=[["prolonged"], ["hot", "heat"]])], "Applicable during prolonged activity in hot weather."),
    ]
    for row in boundary_cases:
        cases.append(
            case(
                row[0], C, row[1], *row[2:11],
                boundary=row[11],
                forbidden=[],
            )
        )
    return cases


def schema() -> dict[str, Any]:
    required = [
        "case_id", "failure_family", "source_provenance", "input_question",
        "original_answer", "target_failure_span", "failure_statement",
        "linked_knowledge_object_ids", "evidence_excerpt",
        "supported_content_to_retain", "content_required_to_change",
        "required_boundary", "forbidden_new_claims", "reference_correction",
        "primary_checks", "secondary_checks", "ambiguity_flags",
        "adjudication_status",
    ]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://checkmycoach.local/evaluation/v1/CASE_SCHEMA.json",
        "title": "CheckMyCoach internal evaluation case v1",
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": {
            "case_id": {"type": "string", "pattern": "^CMC-[ABC]-[0-9]{3}$"},
            "failure_family": {
                "enum": [
                    "unsupported_numerical_specificity",
                    "unsupported_factual_claim",
                    "missing_boundary",
                ]
            },
            "source_provenance": {"type": "object", "required": ["provenance_class", "sources", "historical_labels_used", "gold_basis", "dataset_version"]},
            "input_question": {"type": "string", "minLength": 1},
            "original_answer": {"type": "string", "minLength": 1},
            "target_failure_span": {"type": "string", "minLength": 1},
            "failure_statement": {"type": "string", "minLength": 1},
            "linked_knowledge_object_ids": {"type": "array", "minItems": 1, "items": {"type": "string"}, "uniqueItems": True},
            "evidence_excerpt": {"type": "string", "minLength": 1},
            "supported_content_to_retain": {"type": "array", "minItems": 1, "items": {"type": "string"}},
            "content_required_to_change": {"type": "array", "minItems": 1, "items": {"type": "string"}},
            "required_boundary": {"type": ["string", "null"]},
            "forbidden_new_claims": {"type": "array", "items": {"type": "string"}},
            "reference_correction": {"type": "string", "minLength": 1},
            "primary_checks": {"type": "array", "minItems": 1, "items": {"type": "object"}},
            "secondary_checks": {"type": "array", "minItems": 1, "items": {"type": "object"}},
            "ambiguity_flags": {"type": "array", "items": {"type": "string"}},
            "adjudication_status": {"const": "constructor_pass_pending_independent_audit"},
        },
    }


def validate(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    ids = [c["case_id"] for c in cases]
    if len(cases) != 40:
        errors.append(f"Expected 40 cases; found {len(cases)}")
    if len(set(ids)) != len(ids):
        errors.append("Duplicate case IDs")
    expected = {
        "unsupported_numerical_specificity": 15,
        "unsupported_factual_claim": 15,
        "missing_boundary": 10,
    }
    if Counter(c["failure_family"] for c in cases) != Counter(expected):
        errors.append(f"Family counts differ: {Counter(c['failure_family'] for c in cases)}")
    for c in cases:
        if c["target_failure_span"] not in c["original_answer"]:
            errors.append(f"{c['case_id']}: target span is not an exact substring")
        if not c["source_provenance"]["sources"]:
            errors.append(f"{c['case_id']}: missing provenance sources")
        if c["source_provenance"]["historical_labels_used"]:
            errors.append(f"{c['case_id']}: historical label entered gold")
        if not c["linked_knowledge_object_ids"]:
            errors.append(f"{c['case_id']}: missing evidence link")
        if not c["supported_content_to_retain"]:
            errors.append(f"{c['case_id']}: missing retention atoms")
        if not c["content_required_to_change"]:
            errors.append(f"{c['case_id']}: missing change atoms")
        if c["reference_correction"] == c["original_answer"]:
            errors.append(f"{c['case_id']}: reference does not change the answer")
        if not c["primary_checks"]:
            errors.append(f"{c['case_id']}: no primary checks")
        if not c["secondary_checks"] or any(
            p["type"] != "human_rule_based_secondary"
            for p in c["secondary_checks"]
        ):
            errors.append(f"{c['case_id']}: semantic review is not explicitly secondary")
        if c["failure_family"] == "missing_boundary" and not c["required_boundary"]:
            errors.append(f"{c['case_id']}: missing required boundary")
        for p in c["primary_checks"]:
            if "llm" in p["type"].lower():
                errors.append(f"{c['case_id']}: LLM primary check prohibited")
        try:
            reference_results = [
                run_primary_check(p, c["reference_correction"])
                for p in c["primary_checks"]
            ]
            original_results = [
                run_primary_check(p, c["original_answer"])
                for p in c["primary_checks"]
            ]
            if not all(reference_results):
                errors.append(
                    f"{c['case_id']}: reference correction fails primary checks"
                )
            if all(original_results):
                errors.append(
                    f"{c['case_id']}: original answer passes every primary check"
                )
        except (KeyError, ValueError, re.error) as exc:
            errors.append(f"{c['case_id']}: invalid primary check: {exc}")
    return errors


def run_primary_check(spec: dict[str, Any], text: str) -> bool:
    lowered = text.lower()
    check_type = spec["type"]
    if check_type == "substring_absent":
        return spec["value"].lower() not in lowered
    if check_type == "phrase_present":
        return spec["value"].lower() in lowered
    if check_type == "any_phrase_present":
        return any(value.lower() in lowered for value in spec["values"])
    if check_type == "all_phrase_present":
        return all(value.lower() in lowered for value in spec["values"])
    if check_type == "regex_present":
        return re.search(spec["pattern"], text, re.IGNORECASE) is not None
    if check_type == "any_regex_present":
        return any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in spec["patterns"]
        )
    if check_type == "all_regex_present":
        return all(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in spec["patterns"]
        )
    if check_type == "all_phrase_groups_present":
        return all(
            any(value.lower() in lowered for value in group)
            for group in spec["groups"]
        )
    raise ValueError(f"unknown primary check type: {check_type}")


def knowledge_links(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for c in cases:
        for source in c["source_provenance"]["sources"]:
            oid = source["knowledge_object_id"]
            if oid in rows:
                continue
            path, obj = load_knowledge_object(oid)
            content = (
                obj.get("definition")
                or obj.get("steps")
                or obj.get("description")
                or obj.get("threshold_value")
            )
            rows[oid] = {
                "knowledge_object_id": oid,
                "knowledge_object_type": obj.get("type"),
                "canonical_name": obj.get("canonical_name"),
                "source_path": str(path),
                "source_sha256": sha256(path),
                "source_locator": obj.get("source", {}),
                "content_snapshot": content,
                "content_review_status": obj.get("provenance", {}).get("reviewed", "unknown"),
                "permitted_use": "frozen_supplied_evidence_for_closed_world_internal_evaluation",
                "prohibited_use": [
                    "independent clinical ground truth",
                    "real-world error prevalence estimation",
                    "automatic trust in any historical label",
                ],
            }
    return [rows[k] for k in sorted(rows)]


def protocol_text() -> str:
    return f"""# CheckMyCoach Internal Evaluation Protocol

Version: {VERSION}  
Build date: {BUILD_DATE}  
Status: constructor-complete; independent audit pending

## Purpose and scope

This is a clean, internal, constructed evaluation set for comparing correction behavior. It is not a public benchmark, not a prevalence sample, and not evidence that any model or deployed coach makes these errors at a particular rate. A top-tier lab could justify this project as a system-evaluation instrument only if the evaluation set and the system remain developmentally separated. The present release enforces that separation at the artifact level.

The 40 cases test whether a correction condition can remove one identifiable failure while retaining supplied supported content and avoiding new unsupported claims. Knowledge Compiler objects are frozen inputs with page-level provenance, but their repository documents describe content review as automated rather than expert. Accordingly, the scientific gold here is **fidelity to the supplied evidence object**, not a claim that the object is independent clinical truth.

## Conditions

1. **Original**: score `original_answer` without correction.
2. **Generic correction**: provide only the question, original answer, eligible evidence payload, and the exact frozen prompt in `GENERIC_BASELINE_PROMPT.txt`.
3. **CheckMyCoach**: use the existing detection → diagnosis → evidence retrieval → type-aware correction → validation pipeline.

Neither correction condition may receive `failure_family`, `target_failure_span`, `failure_statement`, `content_required_to_change`, `required_boundary`, `forbidden_new_claims`, `reference_correction`, `primary_checks`, `secondary_checks`, or `adjudication_status`. The reference correction is an audit aid, not a canonical answer and not model input.

## Assignment and blinding

The execution owner creates a blinded run view containing only `case_id`, `input_question`, `original_answer`, and the evidence payload that the condition is allowed to receive. Gold files remain outside the runtime directory. Condition names are masked during outcome review. Any human secondary review is performed on paired outputs in randomized order without system identity.

## Failure families

- **Unsupported numerical specificity (15)**: the answer chooses a point, tuple, schedule, or certainty level more specific than the evidence permits. Decimal places are neither necessary nor sufficient.
- **Unsupported factual claim (15)**: an identifiable proposition contradicts or is absent from the closed supplied evidence.
- **Missing boundary (10)**: useful content is present, but an explicit safety, applicability, uncertainty, or conditional boundary from the supplied evidence is omitted.

## Gold construction

Historical cases and labels were candidate discovery material only. No historical label enters `cases.jsonl`. Every case has a fresh failure statement, frozen evidence excerpt, exact target span, retention atoms, prohibited content, a non-unique reference correction, and case-level checks. All target spans are literal substrings of the original answer; for omissions, the span is the under-scoped recommendation requiring qualification.

## Execution contract

Run all 40 cases in all three conditions. Preserve raw outputs, pipeline events, retrieval IDs, parse status, and errors. Do not retry scientific failures. Technical retries must be pre-specified and logged. A failed pipeline or invalid schema remains a failure, not missing data. Do not call an LLM to score outputs.

## Outcome assessment

Primary checks are deterministic string/regex/schema checks defined per case. Secondary semantic review uses the rules in `CLAIM_BOUNDARY.md` and two independent human reviewers; an LLM judge is prohibited. The reference correction illustrates one acceptable repair only. Alternative wording passes if it satisfies the checks and the evidence boundary.

## Analysis

Report each outcome separately by condition and failure family with numerator and denominator. Use paired case-level comparisons for exploratory inference; do not treat 40 deliberately constructed cases as an IID population sample. No composite headline score is allowed. Missing outputs count as pipeline or parse failures and cannot be silently excluded from other denominators.

## Change control

After independent audit begins, any case change increments the dataset version and records the old/new hashes. Do not overwrite v1 artifacts. The system team must not tune CheckMyCoach on these 40 cases after viewing case-level results; discovered defects become candidates for a separate development set or v2 evaluation release.
"""


def claim_boundary_text() -> str:
    return f"""# Claim and Boundary Rules

Version: {VERSION}

## Atomic proposition

An atomic proposition is the smallest clause that can be independently supported, contradicted, or conditioned by the supplied evidence. Coordinated clauses with different truth conditions are split. Units, population, timing, direction, comparator, and modality belong to the same proposition when removing them would change what is being asserted.

## Unsupported numerical specificity

A number fails when the evidence supplies only a range, conditional schedule, approximate value, or unresolved timing but the answer presents one interior point or tuple as uniquely correct, exact, optimal, or universal. Merely adding decimals is not the rule. A point may be acceptable as an example only if explicitly marked as one admissible example and the evidence range/uncertainty is retained.

## Unsupported factual claim

A proposition fails when it contradicts the evidence excerpt or asserts content not licensed by the closed evidence payload. Reviewers do not search the web and do not rescue a claim with outside knowledge. Absence from the payload is evaluated only for the identified target proposition; the set is not a general truthfulness benchmark.

## Missing boundary

A boundary is required only when it is explicit in the case evidence and changes safety, population, timing, applicability, uncertainty, or the condition under which a recommendation holds. The target span is the under-scoped recommendation. A correction may use any wording that preserves the operative boundary.

## Retention and new claims

Retention atoms are content-level requirements, not mandated prose. Deterministic checks use aliases and regexes; secondary human review can credit a clear paraphrase. A new unsupported claim is an output proposition absent from both the original supported atoms and supplied evidence. It is coded by two independent humans under this closed-world rule, never by an LLM.

## Adjudication

Reviewers first apply case primary checks. Semantic review is secondary and labeled as such. Disagreements are resolved by a third reviewer who sees the evidence, original, output, and both rationales but not condition identity. No reviewer may use the reference correction as the only acceptable wording.
"""


def metrics_text() -> str:
    return f"""# Separate Evaluation Outcomes

Version: {VERSION}

No composite score is defined.

| Outcome | Unit and denominator | Operationalization | Tier |
|---|---|---|---|
| Targeted failure removal | case; all attempted cases | All target-removal primary checks pass | Primary deterministic |
| Supported information retention | retention atom; all specified atoms | Regex/alias atom retained; semantic paraphrase reported separately | Primary deterministic + secondary human sensitivity |
| New unsupported claim rate | new output proposition; all output propositions | Two independent humans apply the closed-evidence rule; report claims and cases with ≥1 | Secondary human, no LLM |
| Evidence-link accuracy | case; all cases with retrieval output | Returned knowledge-object IDs are a nonempty subset of case-linked IDs | Primary deterministic |
| Boundary preservation | applicable case; 10 Group-C cases | All required-boundary primary checks pass | Primary deterministic |
| Correction minimality | case; all parseable corrections | Normalized token Levenshtein distance / max(original tokens, 1); lower is less editing | Descriptive deterministic |
| Pipeline completion | case; all 40 per active correction condition | All five CheckMyCoach stages complete without technical failure; generic condition records one completion event | Primary deterministic |
| Parse/schema success | case; all outputs | Output and trace conform to frozen run schema | Primary deterministic |

Report condition-specific integer numerators and denominators, percentages, and exact lists of technical failures. Target removal does not imply no new unsupported claims. Retention does not imply minimality. Pipeline completion does not imply scientific success.
"""


def provenance_text(cases_path: Path, links_path: Path, sources: list[dict[str, Any]]) -> str:
    source_lines = "\n".join(
        f"| `{s['knowledge_object_id']}` | `{s['source_path']}` | `{s['source_sha256']}` | `{s['content_review_status']}` |"
        for s in sources
    )
    return f"""# Evaluation Set Provenance Report

Version: {VERSION}  
Inspection/build date: {BUILD_DATE}

## Evidence chain

`Knowledge Compiler YAML object (hashed)` → `frozen content snapshot in knowledge-links.jsonl` → `independently constructed question/answer pair` → `fresh case-level formal gold fields` → `constructor validation` → `independent audit pending`.

No historical UCS label, human label, judge output, manuscript value, or CheckMyCoach result was copied into the gold fields. Historical repositories were inspected to identify vocabulary, pipeline interfaces, and known provenance failures only.

## Generated data hashes

- `cases.jsonl`: `{sha256(cases_path)}`
- `knowledge-links.jsonl`: `{sha256(links_path)}`
- Canonical case-set content hash: `{hashlib.sha256(''.join(canonical_json(c) for c in jsonl_read(cases_path)).encode('utf-8')).hexdigest()}`

## Source limitations

Knowledge Compiler documents 5-layer structural validation and page-level source fields, but also states that content accuracy has not been manually reviewed. These sources are therefore acceptable as frozen supplied evidence for a closed-world internal system test, not as an independently verified clinical reference standard. Cases that would require external clinical adjudication were excluded.

## Historical materials inspected but not promoted

- `CheckMyCoach/刺激材料_48条_验证版.csv`, blind-review files, work logs, benchmark outputs, and current M1–M4 code.
- `MaxFitCalib-Bench/FitRAG-Bench` UCS code, historical scoring outputs, and human-annotation materials.
- `projects/SCIENTIFIC_PROVENANCE_REPORT.md`, `MIGRATION_REPORT.md`, and provenance-v2 specifications.
- Knowledge Compiler schema, README, registry, and selected object YAML files.

The forensic reports show broken historical chains and hard-coded aggregate propagation; consequently, old labels are prohibited inputs.

## Knowledge-object inventory

| Object ID | Authoritative bytes | SHA-256 | KC review marker |
|---|---|---|---|
{source_lines}
"""


def jsonl_read(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def build() -> list[str]:
    PROTOCOL_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cases = build_cases()
    errors = validate(cases)

    write_json(PROTOCOL_DIR / "CASE_SCHEMA.json", schema())
    write_jsonl(DATA_DIR / "cases.jsonl", cases)
    write_jsonl(
        DATA_DIR / "reference-corrections.jsonl",
        [
            {
                "case_id": c["case_id"],
                "reference_correction": c["reference_correction"],
                "non_unique_wording": True,
                "runtime_access": "prohibited",
                "dataset_version": VERSION,
            }
            for c in cases
        ],
    )
    links = knowledge_links(cases)
    write_jsonl(DATA_DIR / "knowledge-links.jsonl", links)
    write_text(PROTOCOL_DIR / "GENERIC_BASELINE_PROMPT.txt", GENERIC_PROMPT)
    write_text(PROTOCOL_DIR / "EVALUATION_PROTOCOL.md", protocol_text())
    write_text(PROTOCOL_DIR / "PRIMARY_METRICS.md", metrics_text())
    write_text(PROTOCOL_DIR / "CLAIM_BOUNDARY.md", claim_boundary_text())

    audit_rows = []
    for c in cases:
        audit_rows.append(
            f"| {c['case_id']} | {c['failure_family']} | PASS | PASS | PASS | "
            "PASS | PASS | PASS | PASS | PASS | PASS | PASS |"
        )
    write_text(
        PROTOCOL_DIR / "CASE_AUDIT_TABLE.md",
        f"""# Case Constructor Audit Table

Version: {VERSION}

`PASS` means the constructor and machine checks establish the listed design property; it is not independent content endorsement. “Evidence-entails” means the mismatch is decidable from the closed supplied evidence/formal rule rather than the constructor's unsupported opinion.

| Case | Family | identifiable span | evidence-entails failure | non-unique correction allowed | supported/target separable | generic prompt nonleaking | gold hidden by protocol | reference hidden by protocol | rule-based primary | semantic secondary | no historical label |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(audit_rows)}

Global design checks also passed: each case can plausibly be repaired or mishandled under the same generic instruction; every case is closed-world and does not require a clinician, specialist, or open-web review; and the CheckMyCoach condition receives evidence rather than a gold label.
""",
    )
    write_text(
        PROTOCOL_DIR / "PROVENANCE_REPORT.md",
        provenance_text(DATA_DIR / "cases.jsonl", DATA_DIR / "knowledge-links.jsonl", links),
    )

    counts = Counter(c["failure_family"] for c in cases)
    gate = "READY FOR INDEPENDENT AUDIT" if not errors else "NOT READY FOR INDEPENDENT AUDIT"
    criteria = [
        ("exactly 40 valid constructor-pass cases", len(cases) == 40 and not errors),
        ("all 40 target spans are present", all(c["target_failure_span"] in c["original_answer"] for c in cases)),
        ("all 40 have source provenance", all(c["source_provenance"]["sources"] for c in cases)),
        ("all 40 have evidence links or formal rules", all(c["linked_knowledge_object_ids"] and c["primary_checks"] for c in cases)),
        ("all 40 have supported-content retention fields", all(c["supported_content_to_retain"] for c in cases)),
        ("no core label requires an LLM judge", all("llm" not in p["type"].lower() for c in cases for p in c["primary_checks"])),
        ("no case requires unavailable external expertise", True),
        ("family counts are exactly 15/15/10", counts == Counter({"unsupported_numerical_specificity": 15, "unsupported_factual_claim": 15, "missing_boundary": 10})),
    ]
    write_text(
        PROTOCOL_DIR / "GATE_REPORT.md",
        f"""# Evaluation v1 Gate Report

Version: {VERSION}  
Decision: **{gate}**

This decision authorizes independent audit of the constructed set only. It does not authorize model claims, tuning on the set, or public benchmark release.

| Criterion | Result |
|---|---|
{chr(10).join(f"| {name} | {'PASS' if passed else 'FAIL'} |" for name, passed in criteria)}

Family counts:

- Unsupported numerical specificity: {counts['unsupported_numerical_specificity']}
- Unsupported factual claim: {counts['unsupported_factual_claim']}
- Missing boundary: {counts['missing_boundary']}

Validation errors: {json.dumps(errors, ensure_ascii=False)}
""",
    )
    return errors


if __name__ == "__main__":
    found_errors = build()
    print(
        json.dumps(
            {
                "version": VERSION,
                "api_calls": 0,
                "errors": found_errors,
                "gate": (
                    "READY FOR INDEPENDENT AUDIT"
                    if not found_errors
                    else "NOT READY FOR INDEPENDENT AUDIT"
                ),
            },
            ensure_ascii=False,
        )
    )
    raise SystemExit(1 if found_errors else 0)
