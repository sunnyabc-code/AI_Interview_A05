-- 与 数据库表.md 对齐的示例数据（岗位：Java 后端 / Web 前端 / 测试；难度 easy；题库含技术/项目/场景/行为）
-- 执行前请确认 job_role / difficulty_config / role_interview_strategy / question_bank 表已存在。

INSERT INTO difficulty_config (difficulty_code, difficulty_name, answer_time_seconds, technical_chain_count, project_chain_count, scenario_chain_count, technical_max_followup_depth, project_max_followup_depth, scenario_max_followup_depth, created_at, updated_at)
VALUES ('easy', '入门', 120, 1, 1, 1, 2, 2, 2, NOW(), NOW())
ON DUPLICATE KEY UPDATE updated_at = NOW();

INSERT INTO difficulty_config (difficulty_code, difficulty_name, answer_time_seconds, technical_chain_count, project_chain_count, scenario_chain_count, technical_max_followup_depth, project_max_followup_depth, scenario_max_followup_depth, created_at, updated_at)
VALUES ('medium', '进阶', 120, 1, 1, 1, 2, 2, 2, NOW(), NOW())
ON DUPLICATE KEY UPDATE updated_at = NOW();

INSERT INTO difficulty_config (difficulty_code, difficulty_name, answer_time_seconds, technical_chain_count, project_chain_count, scenario_chain_count, technical_max_followup_depth, project_max_followup_depth, scenario_max_followup_depth, created_at, updated_at)
VALUES ('hard', '高压', 90, 2, 2, 2, 3, 3, 3, NOW(), NOW())
ON DUPLICATE KEY UPDATE updated_at = NOW();

INSERT INTO job_role (code, name, description, is_active, created_at, updated_at) VALUES
('java_backend', 'Java 后端工程师', 'Spring、JVM、并发与中间件', 1, NOW(), NOW()),
('web_frontend', 'Web 前端工程师', 'Vue/React、工程化与性能', 1, NOW(), NOW()),
('test_engineer', '测试工程师', '用例设计、自动化与质量保障', 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE updated_at = NOW();

-- 策略权重（示例）：按岗位微调三方面占比
INSERT INTO role_interview_strategy (role_id, difficulty_code, technical_weight, project_weight, scenario_weight, technical_chain_strategy_json, project_chain_strategy_json, scenario_chain_strategy_json, rubric_version, prompt_version, created_at, updated_at)
SELECT id, 'easy', 0.40, 0.30, 0.30, '{}', '{}', '{}', 'v1', 'v1', NOW(), NOW() FROM job_role WHERE code = 'java_backend'
ON DUPLICATE KEY UPDATE updated_at = NOW();

INSERT INTO role_interview_strategy (role_id, difficulty_code, technical_weight, project_weight, scenario_weight, technical_chain_strategy_json, project_chain_strategy_json, scenario_chain_strategy_json, rubric_version, prompt_version, created_at, updated_at)
SELECT id, 'easy', 0.35, 0.30, 0.35, '{}', '{}', '{}', 'v1', 'v1', NOW(), NOW() FROM job_role WHERE code = 'web_frontend'
ON DUPLICATE KEY UPDATE updated_at = NOW();

INSERT INTO role_interview_strategy (role_id, difficulty_code, technical_weight, project_weight, scenario_weight, technical_chain_strategy_json, project_chain_strategy_json, scenario_chain_strategy_json, rubric_version, prompt_version, created_at, updated_at)
SELECT id, 'easy', 0.35, 0.25, 0.40, '{}', '{}', '{}', 'v1', 'v1', NOW(), NOW() FROM job_role WHERE code = 'test_engineer'
ON DUPLICATE KEY UPDATE updated_at = NOW();

-- 题库（每岗 technical / project / scenario + 行为题可归为 scenario 或单独扩展）
INSERT INTO question_bank (role_id, aspect_type, chain_anchor_type, chain_anchor_code, topic, subtopic, difficulty, question_text, key_points_json, ideal_answer, followup_hints_json, source_type, is_active, created_at, updated_at)
SELECT id, 'technical', 'knowledge_point', 'java_tech_1', 'Java 核心', '并发', 'easy',
'请说明 synchronized 与 ReentrantLock 的适用场景及可能带来的问题。', '[]', '', '[]', 'manual', 1, NOW(), NOW() FROM job_role WHERE code = 'java_backend';

INSERT INTO question_bank (role_id, aspect_type, chain_anchor_type, chain_anchor_code, topic, subtopic, difficulty, question_text, key_points_json, ideal_answer, followup_hints_json, source_type, is_active, created_at, updated_at)
SELECT id, 'project', 'project_probe', 'java_proj_1', '项目', '职责', 'easy',
'介绍一个你负责的 Java 项目：目标、你的职责、技术难点与量化结果。', '[]', '', '[]', 'manual', 1, NOW(), NOW() FROM job_role WHERE code = 'java_backend';

INSERT INTO question_bank (role_id, aspect_type, chain_anchor_type, chain_anchor_code, topic, subtopic, difficulty, question_text, key_points_json, ideal_answer, followup_hints_json, source_type, is_active, created_at, updated_at)
SELECT id, 'scenario', 'scenario_case', 'java_sc_1', '线上', '故障', 'easy',
'线上接口 RT 突然升高，你会如何排查？请给出步骤与工具。', '[]', '', '[]', 'manual', 1, NOW(), NOW() FROM job_role WHERE code = 'java_backend';

INSERT INTO question_bank (role_id, aspect_type, chain_anchor_type, chain_anchor_code, topic, subtopic, difficulty, question_text, key_points_json, ideal_answer, followup_hints_json, source_type, is_active, created_at, updated_at)
SELECT id, 'technical', 'knowledge_point', 'fe_tech_1', '前端', '框架', 'easy',
'请对比 Vue 与 React 在状态管理与渲染模型上的差异。', '[]', '', '[]', 'manual', 1, NOW(), NOW() FROM job_role WHERE code = 'web_frontend';

INSERT INTO question_bank (role_id, aspect_type, chain_anchor_type, chain_anchor_code, topic, subtopic, difficulty, question_text, key_points_json, ideal_answer, followup_hints_json, source_type, is_active, created_at, updated_at)
SELECT id, 'project', 'project_probe', 'fe_proj_1', '项目', '工程化', 'easy',
'描述一次前端性能优化：指标、手段与效果。', '[]', '', '[]', 'manual', 1, NOW(), NOW() FROM job_role WHERE code = 'web_frontend';

INSERT INTO question_bank (role_id, aspect_type, chain_anchor_type, chain_anchor_code, topic, subtopic, difficulty, question_text, key_points_json, ideal_answer, followup_hints_json, source_type, is_active, created_at, updated_at)
SELECT id, 'scenario', 'scenario_case', 'fe_sc_1', '协作', '需求', 'easy',
'产品需求频繁变更时，你如何保证交付质量？', '[]', '', '[]', 'manual', 1, NOW(), NOW() FROM job_role WHERE code = 'web_frontend';

INSERT INTO question_bank (role_id, aspect_type, chain_anchor_type, chain_anchor_code, topic, subtopic, difficulty, question_text, key_points_json, ideal_answer, followup_hints_json, source_type, is_active, created_at, updated_at)
SELECT id, 'technical', 'knowledge_point', 'qa_tech_1', '测试', '用例', 'easy',
'请说明等价类划分与边界值分析如何应用到接口测试。', '[]', '', '[]', 'manual', 1, NOW(), NOW() FROM job_role WHERE code = 'test_engineer';

INSERT INTO question_bank (role_id, aspect_type, chain_anchor_type, chain_anchor_code, topic, subtopic, difficulty, question_text, key_points_json, ideal_answer, followup_hints_json, source_type, is_active, created_at, updated_at)
SELECT id, 'project', 'project_probe', 'qa_proj_1', '质量', '流程', 'easy',
'介绍你参与过的测试流程改进：问题、动作与结果指标。', '[]', '', '[]', 'manual', 1, NOW(), NOW() FROM job_role WHERE code = 'test_engineer';

INSERT INTO question_bank (role_id, aspect_type, chain_anchor_type, chain_anchor_code, topic, subtopic, difficulty, question_text, key_points_json, ideal_answer, followup_hints_json, source_type, is_active, created_at, updated_at)
SELECT id, 'scenario', 'scenario_case', 'qa_sc_1', '行为', '沟通', 'easy',
'开发与测试对缺陷优先级有分歧时，你如何推动结论？', '[]', '', '[]', 'manual', 1, NOW(), NOW() FROM job_role WHERE code = 'test_engineer';

-- 知识库条目（RAG 预留）：knowledge_document / knowledge_item 可按需导入，此处略。
