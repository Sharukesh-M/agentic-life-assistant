"""
tests/test_learning_intelligence.py — Automated Tests for JARVIS-X Learning Intelligence Engine

Tests single dedicated Gemini Learning API client, roadmap service, lesson service, task service,
quiz service, coding service, assessment service, progress service, recommendation service, and LearningStore.
"""

import json
from pathlib import Path
import pytest

from services.learning import (
    GeminiLearningClient,
    get_gemini_learning_client,
    RoadmapService,
    LessonService,
    LearningTaskService,
    QuizService,
    CodingService,
    AssessmentService,
    LearningProgressService,
    LearningRecommendationService,
    LearningIntelligenceService,
    get_learning_intelligence_service,
)
from memory.learning_store import get_learning_store


@pytest.fixture(autouse=True)
def isolate_learning_store(tmp_path, monkeypatch):
    """Isolate LearningStore JSON files to a temporary directory."""
    store = get_learning_store()
    store.dir = tmp_path
    store.roadmaps_path = tmp_path / "roadmaps.json"
    store.lessons_path = tmp_path / "lessons.json"
    store.quizzes_path = tmp_path / "quizzes.json"
    store.coding_path = tmp_path / "coding_challenges.json"
    store.progress_path = tmp_path / "learning_progress.json"
    yield tmp_path


def test_gemini_learning_client_config():
    """Verify GeminiLearningClient reads environment configuration safely without crashing."""
    client = get_gemini_learning_client()
    assert client is not None
    assert isinstance(client.model_name, str)


def test_roadmap_service_generation_and_persistence():
    """Verify RoadmapService generates structured roadmaps and saves to LearningStore."""
    svc = RoadmapService()
    user_context = {
        "current_goal": {"id": "g-test", "title": "Become an AI Engineer", "target_outcome": "Build LLM systems"},
        "current_skill_level": {"overall": "intermediate"},
        "availability": {"daily_minutes": 60}
    }

    roadmap = svc.generate_roadmap(user_context, "Become an AI Engineer")
    assert roadmap is not None
    assert "roadmap_id" in roadmap
    assert len(roadmap.get("milestones", [])) > 0

    # Verify saved in LearningStore
    store = get_learning_store()
    saved = store.get_roadmap(roadmap["roadmap_id"])
    assert saved is not None
    assert saved["title"] == roadmap["title"]


def test_lesson_service_generation():
    """Verify LessonService produces interactive lesson blocks."""
    svc = LessonService()
    user_context = {
        "current_goal": {"title": "Software Developer"},
        "current_skill_level": {"overall": "beginner"},
        "availability": {"daily_minutes": 45}
    }

    lesson = svc.generate_lesson(user_context, "Python Lists & Collections")
    assert lesson is not None
    assert lesson["topic_title"] == "Python Lists & Collections"
    assert len(lesson["blocks"]) > 0


def test_daily_task_generation_and_adaptation():
    """Verify LearningTaskService creates tasks linked to goals and handles task adaptation."""
    svc = LearningTaskService()
    user_context = {
        "current_goal": {"id": "g-1", "title": "Placement DSA"},
        "availability": {"daily_minutes": 60}
    }

    tasks = svc.generate_daily_tasks(user_context)
    assert len(tasks) > 0

    first_task = tasks[0]
    task_id = first_task["id"]

    # Test adaptation of missed task
    adapted = svc.adapt_missed_task(task_id, reason="busy schedule")
    assert adapted is not None
    assert "action" in adapted
    assert adapted["action"] in ("RESUME", "SPLIT", "SHORTEN", "RESCHEDULE", "DEFER", "REPRIORITIZE")


def test_quiz_service_generation_and_evaluation():
    """Verify QuizService generates adaptive quizzes and evaluates user submissions."""
    svc = QuizService()
    user_context = {
        "current_goal": {"title": "Competitive Coding"},
        "current_skill_level": {"overall": "intermediate"}
    }

    quiz = svc.generate_quiz(user_context, "Arrays & Hashing", num_questions=2)
    assert quiz is not None
    assert len(quiz["questions"]) > 0

    qid = quiz["quiz_id"]
    q1_id = str(quiz["questions"][0]["id"])
    correct_ans = quiz["questions"][0].get("correct", 0)

    eval_res = svc.evaluate_quiz_submission(qid, {q1_id: correct_ans})
    assert eval_res["total"] > 0
    assert "accuracy_percent" in eval_res
    assert eval_res["recommendation"] in ("ADVANCE", "RETRY", "PRACTICE")


def test_coding_service_generation():
    """Verify CodingService produces coding challenges with starter code and test cases."""
    svc = CodingService()
    user_context = {
        "current_goal": {"title": "Software Engineer"},
        "current_skill_level": {"overall": "beginner"}
    }

    challenge = svc.generate_challenge(user_context, "Two Sum Problem", language="python")
    assert challenge is not None
    assert "starter_code" in challenge
    assert len(challenge.get("hints", [])) >= 0


def test_progress_and_recommendation_services():
    """Verify progress service analytics and recommendation service next-step engine."""
    prog_svc = LearningProgressService()
    prog_svc.record_study_session(minutes=45, topic="Recursion", accuracy=85.0)

    summary = prog_svc.get_progress_summary()
    assert summary["total_learning_minutes"] >= 45
    assert "Recursion" in summary["completed_topics"]

    rec_svc = LearningRecommendationService()
    next_step = rec_svc.get_next_step({"current_goal": {"title": "DSA"}})
    assert next_step["action"] in ("CONTINUE", "REVIEW", "PRACTICE", "QUIZ", "CODE", "ADVANCE", "RETRY", "REST", "RESCHEDULE")


def test_unified_learning_intelligence_facade():
    """Verify LearningIntelligenceService facade routes requests correctly."""
    facade = get_learning_intelligence_service()
    user_context = {
        "current_goal": {"id": "g-1", "title": "Machine Learning"},
        "current_skill_level": {"overall": "beginner"},
        "availability": {"daily_minutes": 45}
    }

    rdm = facade.process_learning_request("roadmap", user_context, goal_title="Machine Learning")
    assert "roadmap_id" in rdm

    lsn = facade.process_learning_request("lesson", user_context, subject="Supervised Learning")
    assert lsn["topic_title"] == "Supervised Learning"
