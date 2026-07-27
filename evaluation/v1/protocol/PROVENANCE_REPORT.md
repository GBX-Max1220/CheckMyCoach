# Evaluation Set Provenance Report

Version: 1.0.0  
Inspection/build date: 2026-07-27

## Evidence chain

`Knowledge Compiler YAML object (hashed)` → `frozen content snapshot in knowledge-links.jsonl` → `independently constructed question/answer pair` → `fresh case-level formal gold fields` → `constructor validation` → `independent audit pending`.

No historical UCS label, human label, judge output, manuscript value, or CheckMyCoach result was copied into the gold fields. Historical repositories were inspected to identify vocabulary, pipeline interfaces, and known provenance failures only.

## Generated data hashes

- `cases.jsonl`: `49bb577dd65051fc4a9d07dbb0e67cdaa8a3443129f2c3d485555b998b748ed3`
- `knowledge-links.jsonl`: `5577466bce1f71b32b3aef0a9279da235271a498530244409ef8d6e8748ecc67`
- Canonical case-set content hash: `77af4d508d7f6e9ac2b53c2795a000f8af75fa1a0327f90d30c66a32d98bf397`

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
| `concept.high_intensity_interval_training` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\Concept\concept.high_intensity_interval_training.yaml` | `fb6d0144f43ee5a1caaac4b71479391a06f746818e3c3474d1daf662bc31fbad` | `auto` |
| `concept.static_stretch` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\nsca-cscs\objects\Concept\concept.static_stretch.yaml` | `a4f2ff333b64f12288660c209ec8f927ebd32d6c790db0f0f4b5107a92de84dc` | `auto` |
| `procedure.one_rm_testing` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\Procedure\procedure.one_rm_testing.yaml` | `7f42d9aa805383a975965800bdf869cbe37e735b7d63b31be8143a8e728164e4` | `auto` |
| `recommendation.aerobic_exercise_duration` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\Recommendation\recommendation.aerobic_exercise_duration.yaml` | `f8d43040825de797a99741bfed9ca5045f1d2e3ca9d64e3277b15c47d79db2ec` | `auto` |
| `recommendation.avoid_alcohol_and_tobacco_during_cold_exposure` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\Recommendation\recommendation.avoid_alcohol_and_tobacco_during_cold_exposure.yaml` | `671434245d34d79a5d672056423c0f00fb74efa40985234f55a4f5a7fd0515ef` | `auto` |
| `recommendation.benefits_of_regular_physical_activity_for_diabetes` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\Recommendation\recommendation.benefits_of_regular_physical_activity_for_diabetes.yaml` | `e98e7cd23ee048d797d9df0da8021e6a3414b5ab166636d5b3a269569026ad54` | `auto` |
| `recommendation.clothing_considerations_for_exercise_in_cold` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\Recommendation\recommendation.clothing_considerations_for_exercise_in_cold.yaml` | `52bbe7c09ee21951f344d08af04dbcf0f4b47572a5e07f7a902b0282a72244b1` | `auto` |
| `recommendation.clothing_considerations_for_exercise_in_heat` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\Recommendation\recommendation.clothing_considerations_for_exercise_in_heat.yaml` | `d112fbcbad00d076f93307479e26f9f05dc784b9e9d8ac77e1d9383f37abd1ac` | `auto` |
| `recommendation.dynamic_stretching_before_activity` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\Recommendation\recommendation.dynamic_stretching_before_activity.yaml` | `a2438490a879406cd0df1c0c253c93fa027d611f0f6b5c69f69038da6266e9ea` | `auto` |
| `recommendation.individualized_hydration_weight_changes` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\nsca-cscs\objects\Recommendation\recommendation.individualized_hydration_weight_changes.yaml` | `d0acc951b579ee016ca84dda0d4198dbe67464e6d4d004963367cccf1fbfb45c` | `auto` |
| `recommendation.initial_training_intensity_volume_untrained_seniors` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\nsca-cscs\objects\Recommendation\recommendation.initial_training_intensity_volume_untrained_seniors.yaml` | `17bb34ff592fe4e587b70e1bde7498fb6123db4b38d9c2e9200dd924b1fcb834` | `auto` |
| `recommendation.postexercise_carbohydrate_and_protein` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\nsca-cscs\objects\Recommendation\recommendation.postexercise_carbohydrate_and_protein.yaml` | `2457240632c6d7058d797262f8637951916cb75884bb51925a1d4ae9b957ccc6` | `auto` |
| `recommendation.postexercise_protein_aerobic` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\nsca-cscs\objects\Recommendation\recommendation.postexercise_protein_aerobic.yaml` | `505378b4f71eab53c0a9a3ec7992ee7edc4ad8fcab5525d1eea210e6f263b722` | `auto` |
| `recommendation.power_training_load_healthy_older_adults` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\nsca-cscs\objects\Recommendation\recommendation.power_training_load_healthy_older_adults.yaml` | `836ad951127d4ea9f5c14e354d30071052b649a3ab113ecc0ec8e2b77752d934` | `auto` |
| `recommendation.precompetition_meal_timing` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\nsca-cscs\objects\Recommendation\recommendation.precompetition_meal_timing.yaml` | `5a893095054c56f950c22f079e8888a4afe4de0d6e3db6c0c327b3c9ba17c264` | `auto` |
| `recommendation.protein_per_meal_postcompetition` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\nsca-cscs\objects\Recommendation\recommendation.protein_per_meal_postcompetition.yaml` | `dd9690b4c6aa8248761848a8755dedfc410550ffa42e75b4924cc9458fad03c6` | `auto` |
| `recommendation.recovery_time_between_sessions_older_adults` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\nsca-cscs\objects\Recommendation\recommendation.recovery_time_between_sessions_older_adults.yaml` | `6ecb87ab25698c1b6aa15615dee00840ea2676e365541a83af42112bb5e46c8d` | `auto` |
| `recommendation.sports_drink_composition_hot_weather` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\nsca-cscs\objects\Recommendation\recommendation.sports_drink_composition_hot_weather.yaml` | `b00a961ac912d64d7ec8ee7d1ef5b4634c301fa67f8231fd8a30ba9e7191f4dd` | `auto` |
| `recommendation.static_stretch_duration` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\nsca-cscs\objects\Recommendation\recommendation.static_stretch_duration.yaml` | `0540e01cbdf661ba068d5ac99dd0ccb8fe9b4c9f01bae0c1204b27e62c6b7516` | `auto` |
| `recommendation.static_stretching_guidelines_and_precautions` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\nsca-cscs\objects\Recommendation\recommendation.static_stretching_guidelines_and_precautions.yaml` | `aaf29663277240a845df8f42d3bd9387c3f867c64daa9ca668e469aab695b116` | `auto` |
| `recommendation.test_sequencing_order` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\nsca-cscs\objects\Recommendation\recommendation.test_sequencing_order.yaml` | `d7be4ae50762f650ddedcddec9b1e5b750b0f91e1caa06b2e93ad0c3c8675814` | `auto` |
| `recommendation.warm_up_older_adults` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\nsca-cscs\objects\Recommendation\recommendation.warm_up_older_adults.yaml` | `df76e0c30f9651873bf0502d4747a7717e973ed86c1abb3d5fbcc7a2ac7f1444` | `auto` |
| `table_row.cardiorespiratory_frequency` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\TableRow\table_row.cardiorespiratory_frequency.yaml` | `a1c3eac62300c36789a0f74ed934c1cb9c613f56e74edc488271372942d7f30b` | `auto` |
| `table_row.cardiorespiratory_intensity` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\TableRow\table_row.cardiorespiratory_intensity.yaml` | `2e6f1f060fec0e02d8fea6a07d836179d50074d8e7858a9396b22d60cf05e6d4` | `auto` |
| `table_row.cardiorespiratory_volume` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\TableRow\table_row.cardiorespiratory_volume.yaml` | `e61634ba9baba4b5a9a93af8342f958f913ffeb9016f019636698f27c4404ba9` | `auto` |
| `threshold.aerobic_exercise_progression_rate_based_on_fitness_level` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\Threshold\threshold.aerobic_exercise_progression_rate_based_on_fitness_level.yaml` | `3c29d0f0bff0526cb513e6a95818b05b8b83147ffdc4bbeb52249e2f5171f587` | `auto` |
| `threshold.aerobic_intensity_mets` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\Threshold\threshold.aerobic_intensity_mets.yaml` | `4b4f29c17a0241afa802336b54b7571afa6da0fdff579aabe7fded234b467910` | `auto` |
| `threshold.age.older_adult` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\Threshold\threshold.age.older_adult.yaml` | `3b9e75372e8e4df0b211c3f3685094fd94b7c545a03419d644b9f1c71cf3e0d6` | `auto` |
| `threshold.altitude_acclimatization_2300m` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\Threshold\threshold.altitude_acclimatization_2300m.yaml` | `edd18b9d5ac06f0e2d502b2e26eb80a117bf2fa6303edb51127c49ead1a8c5bc` | `auto` |
| `threshold.altitude_acclimatization_4300m` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\Threshold\threshold.altitude_acclimatization_4300m.yaml` | `35f46be0bd107ac1ec0f92220ab100e7d44d99e568f7e6c39ca943739be14930` | `auto` |
| `threshold.resting_heart_rate` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\nsca-cscs\objects\Threshold\threshold.resting_heart_rate.yaml` | `427331ff69b478183e900fb4c079b6013cf63c6b23b47b7a0c0a6685ded1213e` | `auto` |
| `warning.ballistic_stretching` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\Warning\warning.ballistic_stretching.yaml` | `0ad1a16872057632a77307e6164d46b856334818fbd31e116ddeffb9403145f6` | `auto` |
| `warning.contraindication_for_exercise_in_extreme_cold` | `C:\Users\gbx12\projects\acsms12-manifest\sources\books\acsm12\objects\Warning\warning.contraindication_for_exercise_in_extreme_cold.yaml` | `80edaf4dde9e4fd924922a1832217c0b9abcc07a64dee36d79be355cc52b77ff` | `auto` |
