---
title: "TAUSIK 1.4 — отчёт о потенциальных дублях pytest"
subtitle: "Артефакт задачи v14-pytest-dedupe-audit (epic v14-test-philosophy)"
lang: ru
date: 2026-05-02
generator: scripts/audit_pytest_dedupe.py
---

# pytest dedupe audit (`tests/`)

> Регенерация: `PYTHONIOENCODING=utf-8 python scripts/audit_pytest_dedupe.py > docs/ru/research/tausik-1.4-pytest-dedupe-2026-05-02.md`.
> Группы упорядочены по убыванию размера. Это **отчёт для ревью**, не основание для авто-удаления.

164 group(s) of structurally identical test functions (total 480 tests). **Review only — do not auto-delete.**

## Group 1 (sig `d999534d6c2db06b`, 15 tests)
- `tests/test_hooks.py:37` — `TestBashFirewall.test_normal_command_allowed`
- `tests/test_hooks.py:46` — `TestBashFirewall.test_rm_rf_dot_blocked`
- `tests/test_hooks.py:50` — `TestBashFirewall.test_drop_table_blocked`
- `tests/test_hooks.py:57` — `TestBashFirewall.test_git_reset_hard_blocked`
- `tests/test_hooks.py:63` — `TestBashFirewall.test_git_push_force_blocked`
- `tests/test_hooks.py:78` — `TestBashFirewall.test_empty_command_allowed`
- `tests/test_hooks.py:98` — `TestBashFirewall.test_git_push_short_f_blocked`
- `tests/test_hooks.py:137` — `TestBashFirewall.test_git_clean_fd_blocked`
- `tests/test_hooks.py:144` — `TestBashFirewall.test_git_checkout_dot_blocked`
- `tests/test_hooks.py:190` — `TestGitPushGate.test_git_status_allowed`
- `tests/test_hooks.py:194` — `TestGitPushGate.test_git_commit_allowed`
- `tests/test_hooks.py:216` — `TestGitPushGate.test_chained_command_blocked`
- `tests/test_hooks.py:223` — `TestGitPushGate.test_absolute_path_git_blocked`
- `tests/test_hooks.py:285` — `TestAutoFormat.test_nonexistent_file_allowed`
- `tests/test_hooks.py:303` — `TestAutoFormat.test_empty_file_path_allowed`

## Group 2 (sig `514c35b28575e229`, 12 tests)
- `tests/test_audit_stale_docs.py:73` — `TestMirrorPartner.test_en_partner`
- `tests/test_audit_stale_docs.py:76` — `TestMirrorPartner.test_ru_partner`
- `tests/test_rag.py:29` — `TestDetectLanguage.test_python`
- `tests/test_rag.py:32` — `TestDetectLanguage.test_typescript`
- `tests/test_rag.py:35` — `TestDetectLanguage.test_go`
- `tests/test_rag.py:38` — `TestDetectLanguage.test_dockerfile`
- `tests/test_rag.py:41` — `TestDetectLanguage.test_makefile`
- `tests/test_rag.py:47` — `TestDetectLanguage.test_markdown`
- `tests/test_skill_manager.py:71` — `TestRepoNameFromUrl.test_https_url`
- `tests/test_skill_manager.py:74` — `TestRepoNameFromUrl.test_url_with_git_suffix`
- `tests/test_skill_manager.py:77` — `TestRepoNameFromUrl.test_trailing_slash`
- `tests/test_v13_hardening.py:46` — `TestSafeSingleLine.test_empty_string`

## Group 3 (sig `ce0bd5c98f81d28e`, 12 tests)
- `tests/test_brain_scrubbing.py:242` — `test_blocklist_all_cyrillic_homoglyphs_blocked`
- `tests/test_brain_scrubbing.py:251` — `test_blocklist_zero_width_bypass_blocked`
- `tests/test_brain_scrubbing.py:276` — `test_blocklist_double_url_encoded_bypass_blocked`
- `tests/test_brain_scrubbing.py:285` — `test_blocklist_html_numeric_entity_bypass_blocked`
- `tests/test_brain_scrubbing.py:302` — `test_blocklist_mixed_homoglyph_and_zero_width_blocked`
- `tests/test_brain_scrubbing.py:319` — `test_blocklist_greek_lowercase_alpha_blocked`
- `tests/test_brain_scrubbing.py:325` — `test_blocklist_cyrillic_lowercase_v_blocked`
- `tests/test_brain_scrubbing.py:341` — `test_blocklist_cyrillic_lowercase_k_blocked`
- `tests/test_brain_scrubbing.py:350` — `test_blocklist_greek_lowercase_nu_blocked`
- `tests/test_brain_scrubbing.py:356` — `test_blocklist_greek_lowercase_rho_blocked`
- `tests/test_brain_scrubbing.py:362` — `test_blocklist_combining_marks_stripped`
- `tests/test_brain_scrubbing.py:390` — `test_blocklist_case_insensitive_regression`

## Group 4 (sig `56ef61843572624f`, 9 tests)
- `tests/test_brain_scrubbing.py:102` — `test_public_url_with_private_pattern_passes`
- `tests/test_brain_scrubbing.py:136` — `test_project_name_case_insensitive`
- `tests/test_brain_scrubbing.py:220` — `test_unicode_content_with_russian_project_name_blocked`
- `tests/test_brain_scrubbing.py:260` — `test_blocklist_zero_width_joiner_bypass_blocked`
- `tests/test_brain_scrubbing.py:268` — `test_blocklist_url_encoded_bypass_blocked`
- `tests/test_brain_scrubbing.py:294` — `test_blocklist_html_named_entity_bypass_blocked`
- `tests/test_brain_scrubbing.py:311` — `test_blocklist_greek_homoglyph_blocked`
- `tests/test_brain_scrubbing.py:331` — `test_blocklist_cyrillic_lowercase_m_blocked`
- `tests/test_brain_scrubbing.py:336` — `test_blocklist_cyrillic_lowercase_t_blocked`

## Group 5 (sig `d02edd5159a93b69`, 9 tests)
- `tests/test_edge_cases.py:41` — `TestSlugValidation.test_slug_empty`
- `tests/test_edge_cases.py:45` — `TestSlugValidation.test_slug_starts_with_dash`
- `tests/test_edge_cases.py:49` — `TestSlugValidation.test_slug_uppercase`
- `tests/test_edge_cases.py:53` — `TestSlugValidation.test_slug_spaces`
- `tests/test_edge_cases.py:57` — `TestSlugValidation.test_slug_unicode`
- `tests/test_ide_utils.py:99` — `TestGetIdeConfig.test_unknown_ide_raises`
- `tests/test_plan_parser.py:72` — `TestParsePlan.test_no_tasks_raises`
- `tests/test_skill_manager.py:333` — `TestUrlValidation.test_ext_rejected`
- `tests/test_skill_manager.py:337` — `TestUrlValidation.test_file_rejected`

## Group 6 (sig `ade550098ecb2ada`, 9 tests)
- `tests/test_stack_go_rust.py:76` — `TestStackFiltering.test_go_test_skipped_for_python_files`
- `tests/test_stack_go_rust.py:90` — `TestStackFiltering.test_cargo_test_skipped_for_python_files`
- `tests/test_stack_go_rust.py:97` — `TestStackFiltering.test_cargo_test_runs_for_rust_files`
- `tests/test_stack_iac.py:153` — `TestCrossStackFiltering.test_pytest_skipped_on_dockerfile`
- `tests/test_stack_iac.py:160` — `TestCrossStackFiltering.test_pytest_skipped_on_terraform`
- `tests/test_stack_iac.py:167` — `TestCrossStackFiltering.test_ansible_lint_skipped_on_python`
- `tests/test_stack_iac.py:174` — `TestCrossStackFiltering.test_hadolint_runs_for_dockerfile`
- `tests/test_stack_iac.py:181` — `TestCrossStackFiltering.test_terraform_validate_runs_for_tf`
- `tests/test_stack_iac.py:188` — `TestCrossStackFiltering.test_kubeval_runs_for_k8s_manifest`

## Group 7 (sig `8e84f639e892d000`, 8 tests)
- `tests/test_audit_orphan_files.py:57` — `TestExclusion.test_tests_excluded`
- `tests/test_audit_orphan_files.py:60` — `TestExclusion.test_pycache_excluded`
- `tests/test_audit_orphan_files.py:63` — `TestExclusion.test_hooks_excluded`
- `tests/test_audit_stale_docs.py:59` — `TestExclusion.test_research_excluded`
- `tests/test_audit_stale_docs.py:62` — `TestExclusion.test_generated_excluded`
- `tests/test_audit_stale_docs.py:65` — `TestExclusion.test_release_notes_excluded`
- `tests/test_audit_unused_python.py:59` — `TestExclusionHelpers.test_hooks_glob_excluded`
- `tests/test_audit_unused_python.py:62` — `TestExclusionHelpers.test_pycache_excluded`

## Group 8 (sig `c0b9e98470266a43`, 8 tests)
- `tests/test_hooks.py:90` — `TestBashFirewall.test_git_push_force_with_lease_blocked`
- `tests/test_hooks.py:105` — `TestBashFirewall.test_git_push_force_after_args_blocked`
- `tests/test_hooks.py:113` — `TestBashFirewall.test_echo_quoted_git_push_force_allowed`
- `tests/test_hooks.py:121` — `TestBashFirewall.test_word_with_git_prefix_allowed`
- `tests/test_hooks.py:129` — `TestBashFirewall.test_full_path_git_push_force_blocked`
- `tests/test_hooks.py:151` — `TestBashFirewall.test_git_checkout_branch_allowed`
- `tests/test_hooks.py:159` — `TestBashFirewall.test_git_with_c_flag_then_push_force_blocked`
- `tests/test_hooks.py:171` — `TestBashFirewall.test_git_push_at_line_start_blocked`

## Group 9 (sig `e855e79d38d2620f`, 7 tests)
- `tests/test_hooks_common.py:51` — `TestMarkerPresentAnchored.test_marker_inside_fenced_code_block_returns_false`
- `tests/test_hooks_common.py:55` — `TestMarkerPresentAnchored.test_marker_inside_multiline_fenced_block_returns_false`
- `tests/test_hooks_common.py:76` — `TestMarkerPresentAnchored.test_marker_as_part_of_sentence_returns_false`
- `tests/test_hooks_common.py:80` — `TestMarkerPresentAnchored.test_partial_line_match_returns_false`
- `tests/test_hooks_common.py:93` — `TestMarkerPresentAnchored.test_u2029_paragraph_separator_does_NOT_trigger_bypass`
- `tests/test_hooks_common.py:108` — `TestMarkerPresentAnchored.test_tilde_fence_with_language_tag_does_NOT_trigger_bypass`
- `tests/test_hooks_common.py:118` — `TestMarkerPresentAnchored.test_tab_indented_line_does_NOT_trigger_bypass`

## Group 10 (sig `606db32500eac993`, 6 tests)
- `tests/test_audit_orphan_files.py:75` — `TestCollectOrphans.test_imported_module_not_reported`
- `tests/test_audit_orphan_files.py:79` — `TestCollectOrphans.test_doc_referenced_standalone_not_reported`
- `tests/test_audit_orphan_files.py:84` — `TestCollectOrphans.test_hook_path_excluded_from_scan`
- `tests/test_audit_stale_docs.py:88` — `TestCollectStale.test_referenced_doc_not_reported`
- `tests/test_audit_stale_docs.py:92` — `TestCollectStale.test_mirror_partner_protected`
- `tests/test_audit_stale_docs.py:97` — `TestCollectStale.test_research_excluded`

## Group 11 (sig `47cd478bb552e9f5`, 6 tests)
- `tests/test_brain_fallback.py:28` — `test_classify_auth`
- `tests/test_brain_fallback.py:32` — `test_classify_not_found`
- `tests/test_brain_fallback.py:36` — `test_classify_rate_limit`
- `tests/test_brain_fallback.py:42` — `test_classify_server`
- `tests/test_brain_fallback.py:62` — `test_classify_unknown_notion_error`
- `tests/test_brain_fallback.py:66` — `test_classify_non_notion_error`

## Group 12 (sig `0d9c44d32a3f46a8`, 6 tests)
- `tests/test_gates.py:206` — `TestGateRunner.test_count_lines_nonexistent`
- `tests/test_session_cleanup_check.py:35` — `TestPureHelpers.test_review_count_header_only`
- `tests/test_session_cleanup_check.py:42` — `TestPureHelpers.test_review_count_none`
- `tests/test_session_cleanup_check.py:45` — `TestPureHelpers.test_session_overrun_below_threshold`
- `tests/test_session_cleanup_check.py:48` — `TestPureHelpers.test_session_overrun_at_threshold`
- `tests/test_session_cleanup_check.py:51` — `TestPureHelpers.test_session_overrun_no_match`

## Group 13 (sig `967fa6007ffd52ed`, 5 tests)
- `tests/test_bootstrap_generate.py:153` — `TestGenerateAgentsMd.test_header_mentions_agent`
- `tests/test_bootstrap_generate.py:183` — `TestGenerateCursorrules.test_header_mentions_cursor`
- `tests/test_bootstrap_generate.py:188` — `TestGenerateCursorrules.test_points_to_cursor_subdir`
- `tests/test_bootstrap_generate.py:214` — `TestGenerateQwenMd.test_header_mentions_qwen`
- `tests/test_bootstrap_generate.py:219` — `TestGenerateQwenMd.test_points_to_qwen_subdir`

## Group 14 (sig `6cd048592498de44`, 5 tests)
- `tests/test_hooks_common.py:46` — `TestMarkerPresentAnchored.test_substring_only_returns_false`
- `tests/test_hooks_common.py:86` — `TestMarkerPresentAnchored.test_u2028_line_separator_does_NOT_trigger_bypass`
- `tests/test_hooks_common.py:97` — `TestMarkerPresentAnchored.test_u0085_nel_does_NOT_trigger_bypass`
- `tests/test_hooks_common.py:102` — `TestMarkerPresentAnchored.test_tilde_fenced_block_does_NOT_trigger_bypass`
- `tests/test_hooks_common.py:112` — `TestMarkerPresentAnchored.test_four_space_indented_line_does_NOT_trigger_bypass`

## Group 15 (sig `feb65d2235cbcc5c`, 5 tests)
- `tests/test_project_mcp.py:37` — `TestStatus.test_status_empty`
- `tests/test_project_mcp.py:155` — `TestSession.test_session_start`
- `tests/test_project_mcp.py:175` — `TestSession.test_last_handoff_empty`
- `tests/test_project_mcp.py:220` — `TestHierarchy.test_roadmap_empty`
- `tests/test_project_mcp.py:286` — `TestMetricsAndEvents.test_unknown_tool`

## Group 16 (sig `3c79cfd9f2a33890`, 5 tests)
- `tests/test_project_mcp.py:75` — `TestTaskCRUD.test_task_list_filter_status`
- `tests/test_project_mcp.py:122` — `TestTaskCRUD.test_task_update_no_fields`
- `tests/test_project_mcp.py:240` — `TestKnowledge.test_memory_search_empty`
- `tests/test_project_mcp.py:255` — `TestKnowledge.test_search`
- `tests/test_project_mcp.py:259` — `TestKnowledge.test_search_empty`

## Group 17 (sig `b44bdf8b25683771`, 5 tests)
- `tests/test_skill_manager.py:583` — `TestCopySkillFilters.test_skips_claude_plugin`
- `tests/test_skill_manager.py:588` — `TestCopySkillFilters.test_skips_hooks`
- `tests/test_skill_manager.py:593` — `TestCopySkillFilters.test_skips_pycache`
- `tests/test_skill_manager.py:598` — `TestCopySkillFilters.test_skips_claude_md`
- `tests/test_skill_manager.py:603` — `TestCopySkillFilters.test_skips_gitmodules`

## Group 18 (sig `e7ab049134bc4f3d`, 4 tests)
- `tests/test_audit_unused_python.py:55` — `TestExclusionHelpers.test_module_name`
- `tests/test_hooks_common.py:136` — `TestLastUserPromptText.test_missing_file_returns_empty`
- `tests/test_rag_edge.py:349` — `TestDetectEdge.test_no_extension`
- `tests/test_rag_edge.py:353` — `TestDetectEdge.test_compound_extension`

## Group 19 (sig `dbf7765fd93fc1d0`, 4 tests)
- `tests/test_brain_hook_utils.py:84` — `TestIsFresh.test_recent_within_ttl`
- `tests/test_brain_hook_utils.py:87` — `TestIsFresh.test_stale_beyond_ttl`
- `tests/test_brain_hook_utils.py:90` — `TestIsFresh.test_boundary_exactly_at_ttl`
- `tests/test_brain_hook_utils.py:94` — `TestIsFresh.test_zero_ttl_never_fresh`

## Group 20 (sig `b5cc8b90a41a12a0`, 4 tests)
- `tests/test_brain_schema.py:304` — `test_unique_notion_page_id`
- `tests/test_brain_schema.py:320` — `test_generalizable_check_constraint`
- `tests/test_brain_schema.py:336` — `test_confidence_check_constraint`
- `tests/test_brain_schema.py:352` — `test_severity_check_constraint`

## Group 21 (sig `6543bdaf264f06fd`, 4 tests)
- `tests/test_brain_scrubbing.py:58` — `test_relative_paths_pass`
- `tests/test_brain_scrubbing.py:63` — `test_url_path_not_flagged_as_filesystem`
- `tests/test_brain_scrubbing.py:110` — `test_private_url_without_patterns_passes`
- `tests/test_brain_scrubbing.py:215` — `test_unicode_content_cyrillic_clean`

## Group 22 (sig `da0ea30742d44e80`, 4 tests)
- `tests/test_edge_cases.py:61` — `TestSlugValidation.test_slug_single_char`
- `tests/test_edge_cases.py:64` — `TestSlugValidation.test_slug_with_numbers`
- `tests/test_skill_manager.py:327` — `TestUrlValidation.test_https_allowed`
- `tests/test_skill_manager.py:330` — `TestUrlValidation.test_ssh_allowed`

## Group 23 (sig `dc3a0fe8a945c267`, 4 tests)
- `tests/test_edge_cases.py:195` — `TestBoundaryOperations.test_session_end_without_start`
- `tests/test_senar.py:312` — `TestSessionDurationEnforcement.test_session_extend_no_session_raises`
- `tests/test_senar.py:364` — `TestExplorations.test_exploration_end_no_active`
- `tests/test_tausik_service.py:459` — `TestSessions.test_end_no_session`

## Group 24 (sig `d2bac9ba25cba6ea`, 4 tests)
- `tests/test_hooks.py:70` — `TestBashFirewall.test_skip_hooks_env`
- `tests/test_hooks.py:200` — `TestGitPushGate.test_skip_push_hook_env`
- `tests/test_hooks.py:208` — `TestGitPushGate.test_skip_hooks_no_longer_bypasses_push`
- `tests/test_hooks.py:295` — `TestAutoFormat.test_skip_hooks_env`

## Group 25 (sig `e3e0d8240eb4ae27`, 4 tests)
- `tests/test_model_routing.py:19` — `test_medium_maps_to_sonnet`
- `tests/test_model_routing.py:24` — `test_complex_maps_to_opus`
- `tests/test_model_routing.py:45` — `test_case_insensitive`
- `tests/test_model_routing.py:50` — `test_whitespace_tolerated`

## Group 26 (sig `a0a39b7cb5d9efcf`, 4 tests)
- `tests/test_qg0_dimensions.py:34` — `TestDimensionsScore.test_epic_also_counts_as_story_link`
- `tests/test_qg0_dimensions.py:39` — `TestDimensionsScore.test_evidence_plan_via_file_reference`
- `tests/test_qg0_dimensions.py:44` — `TestDimensionsScore.test_evidence_plan_via_memory_reference`
- `tests/test_qg0_dimensions.py:49` — `TestDimensionsScore.test_evidence_plan_vague_ac`

## Group 27 (sig `200cae476eabd105`, 4 tests)
- `tests/test_rag.py:67` — `TestGitignore.test_matches_dir`
- `tests/test_rag.py:70` — `TestGitignore.test_matches_nested`
- `tests/test_rag_edge.py:316` — `TestGitignoreEdge.test_double_star_pattern`
- `tests/test_rag_edge.py:319` — `TestGitignoreEdge.test_trailing_slash_dir`

## Group 28 (sig `3e83335cb242f138`, 4 tests)
- `tests/test_senar.py:423` — `TestChecklistTier.test_tier_simple_lightweight`
- `tests/test_senar.py:435` — `TestChecklistTier.test_tier_medium_standard`
- `tests/test_senar.py:447` — `TestChecklistTier.test_tier_auth_auto_high`
- `tests/test_senar.py:461` — `TestChecklistTier.test_tier_complex_critical`

## Group 29 (sig `76b6a3fbd3603f87`, 4 tests)
- `tests/test_service_verification.py:848` — `TestIsDeclaredConsistentWithGitDiff.test_under_declared_returns_false`
- `tests/test_service_verification.py:883` — `TestIsDeclaredConsistentWithGitDiff.test_no_changes_returns_true`
- `tests/test_service_verification.py:902` — `TestIsDeclaredConsistentWithGitDiff.test_partial_overlap_with_extra_changed_returns_false`
- `tests/test_service_verification.py:916` — `TestIsDeclaredConsistentWithGitDiff.test_backslash_declaration_normalizes_to_match`

## Group 30 (sig `f338a8c86269e456`, 4 tests)
- `tests/test_stack_php_js.py:73` — `TestStackFiltering.test_phpunit_skipped_for_python`
- `tests/test_stack_php_js.py:79` — `TestStackFiltering.test_phpunit_runs_for_php`
- `tests/test_stack_php_js.py:85` — `TestStackFiltering.test_js_test_skipped_for_go`
- `tests/test_stack_php_js.py:91` — `TestStackFiltering.test_js_test_runs_for_tsx`

## Group 31 (sig `a492dca6919d327c`, 4 tests)
- `tests/test_tausik_backend.py:232` — `TestStories.test_add_to_nonexistent_epic`
- `tests/test_tausik_backend.py:302` — `TestTasks.test_add_to_nonexistent_story`
- `tests/test_tausik_service.py:62` — `TestHierarchy.test_story_invalid_epic`
- `tests/test_tausik_service.py:498` — `TestKnowledge.test_memory_invalid_type`

## Group 32 (sig `0f24659a87548d29`, 3 tests)
- `tests/test_audit_orphan_files.py:66` — `TestExclusion.test_unrelated_path_not_excluded`
- `tests/test_audit_stale_docs.py:68` — `TestExclusion.test_unrelated_path_not_excluded`
- `tests/test_audit_unused_python.py:65` — `TestExclusionHelpers.test_unrelated_path_kept`

## Group 33 (sig `41ee8110381925ac`, 3 tests)
- `tests/test_audit_stale_docs.py:79` — `TestMirrorPartner.test_no_partner_for_root`
- `tests/test_brain_hook_utils.py:56` — `TestParseIsoToEpoch.test_empty_string_returns_none`
- `tests/test_rag.py:44` — `TestDetectLanguage.test_unknown`

## Group 34 (sig `10fe70ad9f4120d0`, 3 tests)
- `tests/test_audit_unused_python.py:94` — `TestCollectUnused.test_referenced_kept_clean`
- `tests/test_audit_unused_python.py:99` — `TestCollectUnused.test_private_helper_skipped`
- `tests/test_audit_unused_python.py:105` — `TestCollectUnused.test_hooks_excluded_by_glob`

## Group 35 (sig `273758ec2cfbfc22`, 3 tests)
- `tests/test_bootstrap_frontmatter.py:64` — `TestValidateFrontmatter.test_valid_context_inline`
- `tests/test_bootstrap_frontmatter.py:67` — `TestValidateFrontmatter.test_valid_context_fork`
- `tests/test_bootstrap_frontmatter.py:89` — `TestValidateFrontmatter.test_valid_paths`

## Group 36 (sig `eec5395ace6146f2`, 3 tests)
- `tests/test_bootstrap_frontmatter.py:70` — `TestValidateFrontmatter.test_invalid_context`
- `tests/test_bootstrap_frontmatter.py:79` — `TestValidateFrontmatter.test_invalid_effort`
- `tests/test_bootstrap_frontmatter.py:84` — `TestValidateFrontmatter.test_empty_paths_warning`

## Group 37 (sig `474339df785784d8`, 3 tests)
- `tests/test_bootstrap_generate.py:148` — `TestGenerateAgentsMd.test_contains_shared_hard_markers`
- `tests/test_bootstrap_generate.py:178` — `TestGenerateCursorrules.test_contains_shared_hard_markers`
- `tests/test_bootstrap_generate.py:209` — `TestGenerateQwenMd.test_contains_shared_hard_markers`

## Group 38 (sig `c59d37aca6717a82`, 3 tests)
- `tests/test_bootstrap_generate.py:158` — `TestGenerateAgentsMd.test_preserves_existing`
- `tests/test_bootstrap_generate.py:193` — `TestGenerateCursorrules.test_preserves_existing`
- `tests/test_bootstrap_generate.py:224` — `TestGenerateQwenMd.test_preserves_existing`

## Group 39 (sig `49593e70f60f71a4`, 3 tests)
- `tests/test_brain_classifier.py:71` — `test_src_file_marker_routes_local`
- `tests/test_brain_classifier.py:78` — `test_tausik_cmd_marker_routes_local`
- `tests/test_brain_classifier.py:85` — `test_slug_marker_routes_local_for_non_web_cache`

## Group 40 (sig `cad2e8bcfd6d62d6`, 3 tests)
- `tests/test_brain_mcp_handlers.py:119` — `test_brain_search_empty_query`
- `tests/test_brain_mcp_handlers.py:124` — `test_brain_get_missing_id`
- `tests/test_brain_mcp_handlers.py:129` — `test_brain_get_missing_category`

## Group 41 (sig `ba4b5ee0a46f6c2b`, 3 tests)
- `tests/test_brain_metrics.py:34` — `test_brain_event_record_validates_type`
- `tests/test_brain_storage_hardening.py:234` — `TestNfcProjectHash.test_empty_still_raises`
- `tests/test_service_stack_ops.py:31` — `TestStackShow.test_unknown_stack_raises_keyerror`

## Group 42 (sig `a78b76d38ee2d278`, 3 tests)
- `tests/test_brain_search.py:366` — `test_search_query_with_dash_does_not_crash`
- `tests/test_brain_search.py:377` — `test_search_query_with_inner_quotes_does_not_crash`
- `tests/test_brain_search.py:388` — `test_search_query_with_colon_does_not_crash`

## Group 43 (sig `a745229e4bc2bf99`, 3 tests)
- `tests/test_cq_client.py:33` — `TestEndpointValidation.test_file_scheme_raises`
- `tests/test_cq_client.py:37` — `TestEndpointValidation.test_ftp_scheme_raises`
- `tests/test_cq_client.py:41` — `TestEndpointValidation.test_empty_scheme_raises`

## Group 44 (sig `c5aba93122ca3aae`, 3 tests)
- `tests/test_edge_cases.py:140` — `TestFTS5EdgeCases.test_search_with_parens`
- `tests/test_edge_cases.py:144` — `TestFTS5EdgeCases.test_search_with_asterisk`
- `tests/test_edge_cases.py:148` — `TestFTS5EdgeCases.test_search_only_special_chars`

## Group 45 (sig `538d96b88b424ece`, 3 tests)
- `tests/test_hooks_common.py:27` — `TestMarkerPresentAnchored.test_exact_line_returns_true`
- `tests/test_hooks_common.py:32` — `TestMarkerPresentAnchored.test_line_with_leading_trailing_whitespace`
- `tests/test_hooks_common.py:37` — `TestMarkerPresentAnchored.test_case_insensitive`

## Group 46 (sig `71973bbff4e54098`, 3 tests)
- `tests/test_hooks_common.py:42` — `TestMarkerPresentAnchored.test_multiline_marker_on_its_own_line`
- `tests/test_hooks_common.py:59` — `TestMarkerPresentAnchored.test_marker_after_closing_fence_returns_true`
- `tests/test_hooks_common.py:63` — `TestMarkerPresentAnchored.test_marker_before_opening_fence_returns_true`

## Group 47 (sig `b8fb510eabd7ddb7`, 3 tests)
- `tests/test_hooks_common.py:67` — `TestMarkerPresentAnchored.test_empty_text_returns_false`
- `tests/test_hooks_common.py:70` — `TestMarkerPresentAnchored.test_empty_marker_returns_false`
- `tests/test_hooks_common.py:73` — `TestMarkerPresentAnchored.test_whitespace_only_marker_returns_false`

## Group 48 (sig `ac4fae7a5d559c12`, 3 tests)
- `tests/test_ide_utils.py:23` — `TestDetectIde.test_explicit_tausik_ide_env`
- `tests/test_ide_utils.py:27` — `TestDetectIde.test_explicit_tausik_ide_windsurf`
- `tests/test_ide_utils.py:36` — `TestDetectIde.test_cursor_env_detected`

## Group 49 (sig `5ff75ebdb79619d7`, 3 tests)
- `tests/test_ide_utils.py:61` — `TestDetectIde.test_project_dir_detection_cursor`
- `tests/test_ide_utils.py:65` — `TestDetectIde.test_project_dir_detection_windsurf`
- `tests/test_ide_utils.py:69` — `TestDetectIde.test_project_dir_detection_codex`

## Group 50 (sig `af1258b542fd52e2`, 3 tests)
- `tests/test_project_mcp.py:41` — `TestStatus.test_status_with_tasks`
- `tests/test_project_mcp.py:70` — `TestTaskCRUD.test_task_list`
- `tests/test_project_mcp.py:265` — `TestMetricsAndEvents.test_metrics`

## Group 51 (sig `0a27ba37b9eb6b28`, 3 tests)
- `tests/test_senar.py:78` — `TestQG0NegativeScenario.test_start_ac_with_negative_passes`
- `tests/test_senar.py:89` — `TestQG0NegativeScenario.test_start_ac_with_401_passes`
- `tests/test_senar.py:100` — `TestQG0NegativeScenario.test_start_ac_with_russian_negative_passes`

## Group 52 (sig `854310b833c56d9b`, 3 tests)
- `tests/test_senar.py:113` — `TestQG0NegativeScenario.test_start_ac_without_errors_phrase_fails`
- `tests/test_senar.py:125` — `TestQG0NegativeScenario.test_start_ac_no_failures_fails`
- `tests/test_senar.py:144` — `TestQG0NegativeScenario.test_start_ac_inline_numbered_fails`

## Group 53 (sig `e1a89a5c94634faf`, 3 tests)
- `tests/test_service_verification.py:255` — `TestIsSecuritySensitive.test_any_match_triggers`
- `tests/test_service_verification.py:259` — `TestIsSecuritySensitive.test_any_basename_match_triggers`
- `tests/test_service_verification.py:263` — `TestIsSecuritySensitive.test_any_extension_match_triggers`

## Group 54 (sig `d987a22557bd0432`, 3 tests)
- `tests/test_stack_info_cli.py:43` — `TestStackInfo.test_unknown_stack_raises_with_suggestion`
- `tests/test_tausik_service.py:47` — `TestHierarchy.test_epic_not_found`
- `tests/test_tausik_service.py:205` — `TestTaskLifecycle.test_show_not_found`

## Group 55 (sig `0d3615c8fbd88974`, 3 tests)
- `tests/test_task_done_v2_matcher.py:20` — `test_v1_mcp_name_in_matcher`
- `tests/test_task_done_v2_matcher.py:24` — `test_v2_mcp_name_in_matcher`
- `tests/test_task_done_v2_matcher.py:28` — `test_v2_bare_name_in_matcher`

## Group 56 (sig `a924073872972d8d`, 3 tests)
- `tests/test_task_done_verify_hook.py:72` — `TestBashTaskDoneDetection.test_real_tausik_task_done_matches`
- `tests/test_task_done_verify_hook.py:77` — `TestBashTaskDoneDetection.test_echo_mentioning_task_done_does_not_match`
- `tests/test_task_done_verify_hook.py:82` — `TestBashTaskDoneDetection.test_grep_for_task_done_does_not_match`

## Group 57 (sig `41809bc46d2eca5b`, 3 tests)
- `tests/test_v131_blind_review.py:40` — `test_task_update_status_active_is_refused`
- `tests/test_v131_blind_review.py:47` — `test_task_update_status_blocked_is_refused`
- `tests/test_v131_blind_review.py:54` — `test_task_update_status_review_is_refused`

## Group 58 (sig `1a5c98ff938bc2c1`, 2 tests)
- `tests/test_adversarial_review_mode.py:16` — `TestCriticAgentFile.test_critic_mentions_three_weaknesses`
- `tests/test_adversarial_review_mode.py:29` — `TestCriticAgentFile.test_critic_says_no_fabrication`

## Group 59 (sig `01693d7dc7fabc14`, 2 tests)
- `tests/test_agent_units.py:117` — `TestTaskSetCallBudget.test_negative_rejected`
- `tests/test_agent_units.py:150` — `TestTaskSetCallActual.test_negative_rejected`

## Group 60 (sig `a9316158e0c26585`, 2 tests)
- `tests/test_agent_units.py:122` — `TestTaskSetCallBudget.test_unknown_slug_returns_false`
- `tests/test_agent_units.py:155` — `TestTaskSetCallActual.test_unknown_slug_returns_false`

## Group 61 (sig `aaf613cfc6ba7490`, 2 tests)
- `tests/test_agent_units_cli.py:80` — `TestServiceUpdate.test_update_budget_derives_tier`
- `tests/test_med_findings_fix.py:53` — `TestUpdateBudgetWins.test_budget_only_auto_derives`

## Group 62 (sig `0d610c22debfadb3`, 2 tests)
- `tests/test_agent_units_cli.py:203` — `TestCliParser.test_help_lists_call_budget`
- `tests/test_agent_units_cli.py:209` — `TestCliParser.test_help_update_lists_call_budget`

## Group 63 (sig `b9966551b37e3121`, 2 tests)
- `tests/test_audit_orphan_files.py:71` — `TestCollectOrphans.test_lonely_helper_reported`
- `tests/test_audit_stale_docs.py:84` — `TestCollectStale.test_lonely_reported`

## Group 64 (sig `2fdce8e4ac2b0c9d`, 2 tests)
- `tests/test_bootstrap_dryrun.py:19` — `TestBootstrapDryRun.test_dry_run_no_files_created`
- `tests/test_bootstrap_dryrun.py:89` — `TestBootstrapDryRun.test_dry_run_all_ides`

## Group 65 (sig `c7782f1404076805`, 2 tests)
- `tests/test_bootstrap_generate.py:117` — `TestGenerateClaudeMd.test_special_chars_in_project_name`
- `tests/test_bootstrap_generate.py:122` — `TestGenerateClaudeMd.test_empty_project_name`

## Group 66 (sig `ce128425a997d79a`, 2 tests)
- `tests/test_bootstrap_generate_mcp.py:57` — `test_skips_brain_when_server_missing`
- `tests/test_bootstrap_qwen.py:51` — `test_qwen_skips_brain_when_server_missing`

## Group 67 (sig `0ed241665854d11e`, 2 tests)
- `tests/test_bootstrap_hooks_parity.py:71` — `test_qwen_has_every_claude_hook`
- `tests/test_bootstrap_hooks_parity.py:82` — `test_qwen_does_not_invent_hooks`

## Group 68 (sig `54bf533932b3e573`, 2 tests)
- `tests/test_bootstrap_venv.py:24` — `TestCheckVersion.test_nonexistent_binary`
- `tests/test_bootstrap_venv.py:28` — `TestCheckVersion.test_invalid_command`

## Group 69 (sig `1ea41642df27b2e0`, 2 tests)
- `tests/test_brain_classifier.py:45` — `test_empty_content_routed_local`
- `tests/test_brain_classifier.py:197` — `test_clean_content_routes_brain`

## Group 70 (sig `91c90e3658e8d23b`, 2 tests)
- `tests/test_brain_classifier.py:107` — `test_web_cache_still_blocks_on_abs_path`
- `tests/test_brain_classifier.py:129` — `test_decision_category_keeps_slug_signal`

## Group 71 (sig `a7df1f9a8486b467`, 2 tests)
- `tests/test_brain_classifier.py:117` — `test_web_cache_still_blocks_on_src_file`
- `tests/test_brain_classifier.py:123` — `test_web_cache_still_blocks_on_tausik_cmd`

## Group 72 (sig `331554bcd0fa298e`, 2 tests)
- `tests/test_brain_config.py:207` — `test_compute_project_hash_length_and_charset`
- `tests/test_brain_mcp_write.py:140` — `test_content_hash_16_hex_chars`

## Group 73 (sig `06edb203bddd92d4`, 2 tests)
- `tests/test_brain_config.py:224` — `test_compute_project_hash_rejects_empty`
- `tests/test_brain_project_registry.py:44` — `test_canonical_name_empty_raises`

## Group 74 (sig `5e27e7503360be8d`, 2 tests)
- `tests/test_brain_hook_utils.py:45` — `TestParseIsoToEpoch.test_offset_form`
- `tests/test_brain_hook_utils.py:50` — `TestParseIsoToEpoch.test_naive_assumed_utc`

## Group 75 (sig `13cad52e1c9aad8e`, 2 tests)
- `tests/test_brain_hook_utils.py:103` — `TestIsFresh.test_unparseable_timestamp_is_stale`
- `tests/test_brain_hook_utils.py:106` — `TestIsFresh.test_empty_timestamp_is_stale`

## Group 76 (sig `ccec0c2ab1a5b34e`, 2 tests)
- `tests/test_brain_hook_utils.py:145` — `TestLookupExactUrl.test_empty_url_returns_none`
- `tests/test_vendor.py:81` — `TestLockFile.test_read_missing_returns_none`

## Group 77 (sig `d29c206cf3b87111`, 2 tests)
- `tests/test_brain_init.py:67` — `test_db_schema_unknown_raises`
- `tests/test_brain_notion_client.py:115` — `test_token_required`

## Group 78 (sig `426f4ea56bcf2973`, 2 tests)
- `tests/test_brain_init.py:620` — `TestCliIOPrompt.test_eof_raises_wizard_error`
- `tests/test_brain_init.py:629` — `TestCliIOPrompt.test_keyboard_interrupt_raises_wizard_error`

## Group 79 (sig `67e43891ad32779e`, 2 tests)
- `tests/test_brain_mcp_read.py:475` — `test_format_record_pattern_shows_confidence_badge`
- `tests/test_brain_mcp_read.py:548` — `test_format_record_preserves_cyrillic`

## Group 80 (sig `c40c89300dd92ddd`, 2 tests)
- `tests/test_brain_mcp_write.py:152` — `test_content_hash_rejects_non_string`
- `tests/test_brain_scrubbing.py:204` — `test_non_string_content_raises`

## Group 81 (sig `ccd1ff1187d9c044`, 2 tests)
- `tests/test_brain_mcp_write.py:663` — `test_handler_brain_store_pattern_happy`
- `tests/test_brain_mcp_write.py:676` — `test_handler_brain_store_gotcha_happy`

## Group 82 (sig `ecb72cd194afb4ba`, 2 tests)
- `tests/test_brain_mcp_write.py:695` — `test_store_pattern_taxonomy_strict_requires_kind`
- `tests/test_brain_mcp_write.py:769` — `test_store_pattern_scope_strict_requires_key`

## Group 83 (sig `f19de746c8a9d84d`, 2 tests)
- `tests/test_brain_mcp_write.py:719` — `test_store_pattern_invalid_taxonomy_even_when_loose`
- `tests/test_brain_mcp_write.py:755` — `test_store_pattern_scope_empty_string_blocks`

## Group 84 (sig `cba2abacc28ac852`, 2 tests)
- `tests/test_brain_mcp_write.py:747` — `test_format_store_result_taxonomy_blocked`
- `tests/test_brain_mcp_write.py:791` — `test_format_store_result_card_schema_blocked`

## Group 85 (sig `b14eba0113a8b638`, 2 tests)
- `tests/test_brain_move.py:212` — `TestMoveToBrain.test_invalid_kind`
- `tests/test_brain_move.py:216` — `TestMoveToBrain.test_source_not_found`

## Group 86 (sig `5f4488278f6fd990`, 2 tests)
- `tests/test_brain_move.py:329` — `TestMoveToLocal.test_invalid_category`
- `tests/test_brain_move.py:335` — `TestMoveToLocal.test_not_found`

## Group 87 (sig `3167ce3979d3da04`, 2 tests)
- `tests/test_brain_notion_client.py:120` — `test_token_must_be_string`
- `tests/test_brain_project_registry.py:51` — `test_canonical_name_non_string_raises`

## Group 88 (sig `c879426434a3bd21`, 2 tests)
- `tests/test_brain_project_registry.py:56` — `test_load_registry_missing_returns_empty`
- `tests/test_brain_project_registry.py:153` — `test_all_project_names_empty`

## Group 89 (sig `f0d36bda3a0b40a3`, 2 tests)
- `tests/test_brain_project_registry.py:60` — `test_load_registry_malformed_returns_empty`
- `tests/test_brain_project_registry.py:65` — `test_load_registry_non_list_returns_empty`

## Group 90 (sig `b10c97193002f3da`, 2 tests)
- `tests/test_brain_scrubbing.py:18` — `test_clean_content_passes`
- `tests/test_brain_scrubbing.py:209` — `test_empty_content_passes`

## Group 91 (sig `b12ad7a18636c765`, 2 tests)
- `tests/test_brain_scrubbing.py:40` — `test_posix_users_path_blocked`
- `tests/test_brain_scrubbing.py:46` — `test_windows_drive_path_blocked`

## Group 92 (sig `8f7c2f290c549ef1`, 2 tests)
- `tests/test_brain_scrubbing.py:93` — `test_private_url_matches_configured_pattern`
- `tests/test_brain_scrubbing.py:127` — `test_project_name_exact_substring_blocked`

## Group 93 (sig `b300c4c33b727d3d`, 2 tests)
- `tests/test_brain_search.py:187` — `test_sanitize_wraps_in_quotes`
- `tests/test_brain_search.py:191` — `test_sanitize_escapes_embedded_quotes`

## Group 94 (sig `06286b5eeb8e02ec`, 2 tests)
- `tests/test_brain_search.py:431` — `test_apply_prefer_stack_ranking_boosts_matching_stack`
- `tests/test_brain_search.py:440` — `test_apply_prefer_stack_ranking_respects_stronger_bm25`

## Group 95 (sig `e533b296f9067243`, 2 tests)
- `tests/test_brain_search_proactive_hook.py:355` — `test_no_cache_hit_allows_fetch`
- `tests/test_brain_search_proactive_hook.py:476` — `test_empty_query_exits_zero`

## Group 96 (sig `2819a2e08d2b4b66`, 2 tests)
- `tests/test_cascade_delete.py:105` — `TestForeignKeyIntegrity.test_task_requires_valid_story`
- `tests/test_cascade_delete.py:109` — `TestForeignKeyIntegrity.test_story_requires_valid_epic`

## Group 97 (sig `85ba2a8cf1b1082f`, 2 tests)
- `tests/test_cascade_delete.py:118` — `TestForeignKeyIntegrity.test_task_story_id_references_stories`
- `tests/test_cascade_delete.py:127` — `TestForeignKeyIntegrity.test_story_epic_id_references_epics`

## Group 98 (sig `66496de30d2be460`, 2 tests)
- `tests/test_cq_client.py:25` — `TestEndpointValidation.test_http_endpoint_accepted`
- `tests/test_cq_client.py:29` — `TestEndpointValidation.test_https_endpoint_accepted`

## Group 99 (sig `ff914fbd7d04c310`, 2 tests)
- `tests/test_doc_extract.py:52` — `test_is_available_when_installed`
- `tests/test_doc_extract.py:57` — `test_is_available_when_missing`

## Group 100 (sig `ca7d3c690bd6fee1`, 2 tests)
- `tests/test_edge_cases.py:72` — `TestLengthValidation.test_title_max_length`
- `tests/test_edge_cases.py:79` — `TestLengthValidation.test_content_max`

## Group 101 (sig `0a96e9c633131254`, 2 tests)
- `tests/test_edge_cases.py:75` — `TestLengthValidation.test_title_over_max`
- `tests/test_edge_cases.py:82` — `TestLengthValidation.test_content_over_max`

## Group 102 (sig `23dcaee06e83a34e`, 2 tests)
- `tests/test_edge_cases.py:124` — `TestUnicode.test_unicode_search`
- `tests/test_tausik_service.py:502` — `TestKnowledge.test_memory_search`

## Group 103 (sig `966617296a43a592`, 2 tests)
- `tests/test_edge_cases.py:190` — `TestBoundaryOperations.test_session_double_start`
- `tests/test_tausik_service.py:454` — `TestSessions.test_double_start`

## Group 104 (sig `9823ffcec84f855e`, 2 tests)
- `tests/test_gate_stack_aware.py:72` — `TestGateApplies.test_python_gate_skipped_for_go_files`
- `tests/test_gate_stack_aware.py:78` — `TestGateApplies.test_mixed_files_match_any`

## Group 105 (sig `4ca6ac88e45588f6`, 2 tests)
- `tests/test_gates.py:255` — `TestGateRunner.test_format_results_pass`
- `tests/test_gates.py:263` — `TestGateRunner.test_format_results_fail`

## Group 106 (sig `719db6d66b2f3844`, 2 tests)
- `tests/test_gates.py:329` — `TestStackGates.test_auto_enable_for_go`
- `tests/test_gates.py:337` — `TestStackGates.test_auto_enable_for_rust`

## Group 107 (sig `0b2e273fc3e3a476`, 2 tests)
- `tests/test_gates.py:375` — `TestStackGates.test_react_enables_tsc_and_eslint`
- `tests/test_stack_go_rust.py:47` — `TestGateRegistration.test_in_stack_gate_map`

## Group 108 (sig `7252c7041fbc43e9`, 2 tests)
- `tests/test_gates.py:409` — `TestCustomGateValidation.test_shell_operators_without_files_allowed`
- `tests/test_gates.py:422` — `TestCustomGateValidation.test_path_prefix_stripped`

## Group 109 (sig `a2602e658380db63`, 2 tests)
- `tests/test_gates.py:654` — `TestDefaultGatesHaveFileExtensions.test_ruff_has_py_extension`
- `tests/test_gates.py:657` — `TestDefaultGatesHaveFileExtensions.test_mypy_has_py_extension`

## Group 110 (sig `d74497a7bbdc5348`, 2 tests)
- `tests/test_gates.py:680` — `TestResolveTestFilesForRelevant.test_basename_match`
- `tests/test_gates.py:748` — `TestResolveTestFilesForRelevant.test_windows_backslash_path_normalized`

## Group 111 (sig `10a8db25a05fedea`, 2 tests)
- `tests/test_graph_memory.py:213` — `TestGraphService.test_memory_link_nonexistent_node`
- `tests/test_graph_memory.py:218` — `TestGraphService.test_memory_link_self_loop`

## Group 112 (sig `b15f109ae6ef91e2`, 2 tests)
- `tests/test_graph_memory.py:243` — `TestGraphService.test_memory_unlink_nonexistent`
- `tests/test_tausik_service.py:507` — `TestKnowledge.test_memory_not_found`

## Group 113 (sig `845452c7cb04a80d`, 2 tests)
- `tests/test_hooks.py:41` — `TestBashFirewall.test_rm_rf_root_blocked`
- `tests/test_hooks.py:183` — `TestGitPushGate.test_git_push_blocked`

## Group 114 (sig `a910efc91c095945`, 2 tests)
- `tests/test_hooks.py:82` — `TestBashFirewall.test_no_stdin_allowed`
- `tests/test_hooks.py:291` — `TestAutoFormat.test_no_stdin_allowed`

## Group 115 (sig `a98e74d02eb1ca49`, 2 tests)
- `tests/test_hooks_common.py:192` — `TestLastUserPromptText.test_huge_transcript_uses_tail_read`
- `tests/test_hooks_common.py:231` — `TestLastUserPromptText.test_partial_first_line_after_seek_dropped`

## Group 116 (sig `7254a8eb1e1dbffc`, 2 tests)
- `tests/test_iac_bootstrap_detection.py:39` — `TestSignatureMatch.test_exact_filename_miss`
- `tests/test_iac_bootstrap_detection.py:62` — `TestSignatureMatch.test_glob_no_match`

## Group 117 (sig `f6a957a6ba271b4a`, 2 tests)
- `tests/test_iac_bootstrap_detection.py:77` — `TestDetectStacks.test_docker_only`
- `tests/test_iac_bootstrap_detection.py:90` — `TestDetectStacks.test_helm_via_chart_yaml`

## Group 118 (sig `2da4ec9635533a7b`, 2 tests)
- `tests/test_iac_bootstrap_detection.py:128` — `TestAutoEnable.test_terraform_auto_enables_terraform_validate`
- `tests/test_iac_bootstrap_detection.py:138` — `TestAutoEnable.test_docker_auto_enables_hadolint`

## Group 119 (sig `57e4cd2d46119414`, 2 tests)
- `tests/test_ide_utils.py:51` — `TestDetectIde.test_explicit_overrides_env`
- `tests/test_ide_utils.py:56` — `TestDetectIde.test_cursor_wins_over_windsurf`

## Group 120 (sig `7a2213d48d2f7d32`, 2 tests)
- `tests/test_ide_utils.py:85` — `TestGetIdeConfig.test_claude_config`
- `tests/test_ide_utils.py:90` — `TestGetIdeConfig.test_cursor_config`

## Group 121 (sig `70a3c6a98c996733`, 2 tests)
- `tests/test_ide_utils.py:111` — `TestPathHelpers.test_get_ide_dir`
- `tests/test_ide_utils.py:115` — `TestPathHelpers.test_get_ide_dir_codex`

## Group 122 (sig `04ecb970db11ef0f`, 2 tests)
- `tests/test_interview_skill.py:28` — `test_socratic_framing`
- `tests/test_interview_skill.py:33` — `test_stop_condition_present`

## Group 123 (sig `3074b4f54c833356`, 2 tests)
- `tests/test_keyword_detector_hook.py:191` — `TestSettingsGeneration.test_claude_settings_has_stop_hook`
- `tests/test_user_prompt_submit_hook.py:152` — `TestSettingsGeneration.test_claude_settings_has_userpromptsubmit`

## Group 124 (sig `2f9414e0cf418ad9`, 2 tests)
- `tests/test_keyword_detector_hook.py:204` — `TestSettingsGeneration.test_qwen_settings_has_stop_hook`
- `tests/test_user_prompt_submit_hook.py:167` — `TestSettingsGeneration.test_qwen_settings_has_userpromptsubmit`

## Group 125 (sig `48382eecc25b48e5`, 2 tests)
- `tests/test_mcp_project_server.py:87` — `test_cursor_project_server_chdir_is_in_main`
- `tests/test_mcp_project_server.py:117` — `test_project_server_minimal_text_reply_on_exception`

## Group 126 (sig `b1f1e97d2ff30a8a`, 2 tests)
- `tests/test_mcp_windows.py:71` — `TestGitHeadReading.test_empty_head_file`
- `tests/test_mcp_windows.py:80` — `TestGitHeadReading.test_invalid_short_hash`

## Group 127 (sig `3668a8b187c27a11`, 2 tests)
- `tests/test_mcp_windows.py:99` — `TestSafePath.test_traversal_blocked`
- `tests/test_mcp_windows.py:104` — `TestSafePath.test_windows_backslash_traversal`

## Group 128 (sig `0fe6471230cd2926`, 2 tests)
- `tests/test_mcp_windows.py:154` — `TestPathNormalization.test_chunk_file_empty_content`
- `tests/test_mcp_windows.py:159` — `TestPathNormalization.test_chunk_file_whitespace_only`

## Group 129 (sig `c5df64759e76ddca`, 2 tests)
- `tests/test_memory_block.py:29` — `TestMemoryBlockContent.test_empty_db_returns_empty_string`
- `tests/test_memory_compact.py:33` — `TestMemoryCompact.test_empty_db_returns_empty`

## Group 130 (sig `fc43dc97d87d4e8d`, 2 tests)
- `tests/test_memory_block.py:176` — `TestSkillsDocumentation.test_start_skill_mentions_memory_block`
- `tests/test_memory_block.py:183` — `TestSkillsDocumentation.test_checkpoint_skill_mentions_memory_block`

## Group 131 (sig `8059a498319b73f9`, 2 tests)
- `tests/test_memory_markers.py:100` — `TestEdgeCases.test_empty_text`
- `tests/test_memory_markers.py:103` — `TestEdgeCases.test_whitespace_only`

## Group 132 (sig `498301850c96baef`, 2 tests)
- `tests/test_memory_markers.py:135` — `TestTwoSegmentSlugs.test_two_seg_slug_with_src_file_kept`
- `tests/test_memory_markers.py:142` — `TestTwoSegmentSlugs.test_two_seg_slug_with_tausik_cmd_kept`

## Group 133 (sig `b347a712dbbdd606`, 2 tests)
- `tests/test_memory_posttool_audit_hook.py:280` — `TestSettingsGeneration.test_claude_settings_registers_audit`
- `tests/test_memory_pretool_block_hook.py:606` — `TestSettingsGeneration.test_claude_settings_registers_hook`

## Group 134 (sig `e5d602925978438e`, 2 tests)
- `tests/test_memory_posttool_audit_hook.py:300` — `TestSettingsGeneration.test_qwen_settings_registers_audit`
- `tests/test_memory_pretool_block_hook.py:626` — `TestSettingsGeneration.test_qwen_settings_registers_hook`

## Group 135 (sig `5332b812b7c77579`, 2 tests)
- `tests/test_memory_pretool_block_hook.py:141` — `TestBlocksMemoryWrites.test_blocks_agents_memory`
- `tests/test_memory_pretool_block_hook.py:156` — `TestBlocksMemoryWrites.test_blocks_deeply_nested_memory`

## Group 136 (sig `048d66275a555c03`, 2 tests)
- `tests/test_memory_pretool_block_hook.py:267` — `TestGracefulMalformed.test_malformed_json`
- `tests/test_memory_pretool_block_hook.py:285` — `TestGracefulMalformed.test_empty_stdin`

## Group 137 (sig `a972d60e23a1b486`, 2 tests)
- `tests/test_memory_pretool_block_hook.py:401` — `TestBypassMarker.test_marker_in_last_user_turn_as_string`
- `tests/test_memory_pretool_block_hook.py:454` — `TestBypassMarker.test_marker_case_insensitive`

## Group 138 (sig `6593c7d47f31627a`, 2 tests)
- `tests/test_migrations.py:130` — `TestMigrationV1ToV2.test_cascade_delete_works_after_migration`
- `tests/test_migrations.py:143` — `TestMigrationV1ToV2.test_story_cascade_deletes_tasks`

## Group 139 (sig `e63f8863aec25daf`, 2 tests)
- `tests/test_plan_parser.py:81` — `TestParsePlan.test_untitled_plan`
- `tests/test_plan_parser.py:91` — `TestParsePlan.test_no_context`

## Group 140 (sig `59ec57f501890a72`, 2 tests)
- `tests/test_project_mcp.py:116` — `TestTaskCRUD.test_task_update`
- `tests/test_project_mcp.py:244` — `TestKnowledge.test_decide`

## Group 141 (sig `ca7c81aa2f675453`, 2 tests)
- `tests/test_qg2_gates.py:295` — `TestQG0SecuritySurface.test_qg0_security_surface_warning`
- `tests/test_qg2_gates.py:336` — `TestQG0ScopeWarnings.test_qg0_scope_warning`

## Group 142 (sig `f554bd2a55c5bc4d`, 2 tests)
- `tests/test_rag_edge.py:35` — `TestSafePath.test_traversal_dotdot`
- `tests/test_rag_edge.py:39` — `TestSafePath.test_traversal_encoded`

## Group 143 (sig `64631c276dbd10f4`, 2 tests)
- `tests/test_rag_edge.py:232` — `TestStoreEdgeCases.test_search_empty_db`
- `tests/test_tausik_backend.py:388` — `TestTaskLogs.test_list_empty`

## Group 144 (sig `18274152e8616f38`, 2 tests)
- `tests/test_review_high_fixes.py:42` — `TestIacExecutablesWhitelisted.test_user_override_with_path_prefix_passes`
- `tests/test_review_high_fixes.py:73` — `TestShellChainBlocked.test_pipe_without_files_still_allowed`

## Group 145 (sig `32ceb3aa80220ec1`, 2 tests)
- `tests/test_senar.py:53` — `TestQG0ContextGate.test_start_with_goal_and_ac_passes`
- `tests/test_senar.py:350` — `TestExplorations.test_exploration_start`

## Group 146 (sig `3ee0bf0d4d92d164`, 2 tests)
- `tests/test_senar.py:136` — `TestQG0NegativeScenario.test_start_ac_russian_without_errors_fails`
- `tests/test_senar.py:170` — `TestQG0NegativeScenario.test_has_negative_scenario_unit_returns_true_for_real_scenario`

## Group 147 (sig `ae42bee352fe5f8c`, 2 tests)
- `tests/test_senar.py:578` — `TestNoKnowledgeRefusal.test_no_knowledge_allowed_for_simple`
- `tests/test_senar.py:583` — `TestNoKnowledgeRefusal.test_no_knowledge_allowed_for_medium`

## Group 148 (sig `8fde57b1a26d2fb7`, 2 tests)
- `tests/test_service_knowledge_decide.py:63` — `test_content_with_src_file_marker_routes_local`
- `tests/test_service_knowledge_decide.py:84` — `test_clean_content_brain_disabled_falls_back_local`

## Group 149 (sig `578192dc4b10b8f5`, 2 tests)
- `tests/test_service_knowledge_decide.py:70` — `test_content_with_abs_path_marker_routes_local`
- `tests/test_service_knowledge_decide.py:230` — `test_whitespace_only_routes_local`

## Group 150 (sig `a8292720cc8062b8`, 2 tests)
- `tests/test_service_roles.py:64` — `TestRoleCRUD.test_show_unknown_raises`
- `tests/test_service_roles.py:113` — `TestRoleDelete.test_delete_unknown_raises`

## Group 151 (sig `bea13f7f26161a86`, 2 tests)
- `tests/test_service_verification.py:301` — `TestRecordAndLookup.test_lookup_misses_on_no_runs`
- `tests/test_service_verification.py:424` — `TestRecordAndLookup.test_lookup_empty_slug_returns_none`

## Group 152 (sig `c0f04970a99d6e39`, 2 tests)
- `tests/test_service_verification.py:307` — `TestRecordAndLookup.test_lookup_misses_on_files_hash_mismatch`
- `tests/test_service_verification.py:322` — `TestRecordAndLookup.test_lookup_misses_on_command_mismatch`

## Group 153 (sig `017f372ce4900d24`, 2 tests)
- `tests/test_service_verification.py:432` — `TestIsCacheAllowed.test_safe_files_allow_cache`
- `tests/test_service_verification.py:435` — `TestIsCacheAllowed.test_security_files_disallow_cache`

## Group 154 (sig `3ab0801772d9da8b`, 2 tests)
- `tests/test_session_capacity.py:72` — `TestEnforcement.test_passes_under_budget`
- `tests/test_session_capacity.py:90` — `TestEnforcement.test_zero_budget_no_block`

## Group 155 (sig `62a4545671442ce7`, 2 tests)
- `tests/test_session_cleanup_check.py:24` — `TestPureHelpers.test_no_active_exploration_returns_false`
- `tests/test_session_cleanup_check.py:32` — `TestPureHelpers.test_empty_explore_output_returns_false`

## Group 156 (sig `f2ea870be28a0bb3`, 2 tests)
- `tests/test_skills_maturity.py:60` — `TestRoleProfiles.test_role_has_required_sections`
- `tests/test_skills_maturity.py:68` — `TestRoleProfiles.test_role_has_skill_modifiers`

## Group 157 (sig `93fdbc885088b805`, 2 tests)
- `tests/test_skills_maturity.py:317` — `TestBootstrapRolesStacks.test_copy_roles_function_exists`
- `tests/test_skills_maturity.py:323` — `TestBootstrapRolesStacks.test_copy_stacks_function_exists`

## Group 158 (sig `f214a0ee70038f10`, 2 tests)
- `tests/test_stack_go_rust.py:58` — `TestStackInfo.test_go_info_lists_test_runner`
- `tests/test_stack_php_js.py:58` — `TestStackInfo.test_php_info`

## Group 159 (sig `d8fd23eb7bc8530c`, 2 tests)
- `tests/test_stack_go_rust.py:64` — `TestStackInfo.test_rust_info_lists_test_runner`
- `tests/test_stack_php_js.py:64` — `TestStackInfo.test_typescript_info`

## Group 160 (sig `88a05154e635745c`, 2 tests)
- `tests/test_task_done_verify_hook.py:44` — `TestHeuristics.test_missing_test_numbers_fails_that_check`
- `tests/test_task_done_verify_hook.py:49` — `TestHeuristics.test_missing_lint_fails_that_check`

## Group 161 (sig `f0c3822546992b3e`, 2 tests)
- `tests/test_task_next_model_hint.py:48` — `TestIsTaskNextModelHintEnabled.test_true_when_set`
- `tests/test_task_next_model_hint.py:55` — `TestIsTaskNextModelHintEnabled.test_false_when_disabled`

## Group 162 (sig `bc63e6fe991c6ba5`, 2 tests)
- `tests/test_tausik_cli.py:353` — `TestRoadmap.test_roadmap_include_done`
- `tests/test_tausik_cli.py:409` — `TestExplore.test_explore_current`

## Group 163 (sig `4b857e60236f18c4`, 2 tests)
- `tests/test_tausik_cli.py:374` — `TestDeadEnd.test_dead_end`
- `tests/test_tausik_cli.py:403` — `TestExplore.test_explore_start`

## Group 164 (sig `cb2e5e45a267c99c`, 2 tests)
- `tests/test_user_prompt_submit_hook.py:89` — `TestIntentDetection.test_explain_prompt_does_not_nudge`
- `tests/test_user_prompt_submit_hook.py:95` — `TestIntentDetection.test_empty_prompt_does_not_nudge`

## Documented false positives

- Tests that share AST shape because they exercise different inputs but the same code path are **not bugs** — they are explicit coverage of edge cases. Review each group manually.
- Identifier names, string literals, and numeric values are erased during normalisation. So two tests with different fixtures and assertions but identical control flow will hash the same.
- Parametrize candidates: groups whose members differ only in a single literal can usually collapse into one parametrised test.

