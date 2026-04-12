"""面试题型编排：与 InterviewNextQuestionView 中下一题/结束判定共用。"""


def enabled_categories(interview):
    categories = []
    if interview.enable_technical_questions:
        categories.append("technical")
    if interview.enable_project_questions:
        categories.append("project")
    if interview.enable_scenario_questions:
        categories.append("scenario")
    return categories


def target_chain_count(interview, category_code):
    """
    各题型链数量来自 difficulty_config。面试已勾选某题型时，至少出题 1 条链，
    避免配置里误填 0 导致整类题型被跳过、面试提前结束并打分。
    """
    if not interview.difficulty_config:
        return 1

    config = interview.difficulty_config
    if category_code == "technical":
        raw = max(getattr(config, "technical_chain_count", 1), 0)
    elif category_code == "project":
        raw = max(getattr(config, "project_chain_count", 1), 0)
    elif category_code == "scenario":
        raw = max(getattr(config, "scenario_chain_count", 1), 0)
    else:
        raw = 0
    return max(raw, 1)


def max_questions_per_chain(interview, category_code):
    if not interview.difficulty_config:
        return 1

    config = interview.difficulty_config
    if category_code == "technical":
        return max(getattr(config, "technical_max_followup_depth", 1), 1)
    if category_code == "project":
        return max(getattr(config, "project_max_followup_depth", 1), 1)
    if category_code == "scenario":
        return max(getattr(config, "scenario_max_followup_depth", 1), 1)
    return 1


def interview_planned_question_total(interview):
    """与 _determine_next_slot 一致：本场应完成的题目总数（各题型链数 × 每链题数）。"""
    total = 0
    for category_code in enabled_categories(interview):
        total += target_chain_count(interview, category_code) * max_questions_per_chain(
            interview, category_code
        )
    return total


def interview_required_round_count_to_finish(interview):
    """结束并打分前至少应完成的轮次数：优先创建时 total_rounds，否则用编排计算值。"""
    stored = interview.total_rounds or 0
    computed = interview_planned_question_total(interview)
    if stored > 0:
        return stored
    return computed
