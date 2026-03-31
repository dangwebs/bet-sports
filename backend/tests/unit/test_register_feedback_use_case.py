from src.application.dtos.dtos import BettingFeedbackRequestDTO
from src.application.use_cases.suggested_picks_use_case import RegisterFeedbackUseCase


class DummyLearningService:
    def __init__(self):
        self.registered = []

    def register_feedback(self, feedback):
        self.registered.append(feedback)

    def get_market_adjustment(self, market_type: str) -> float:
        return 0.75


def test_register_feedback_use_case_updates_learning_service():
    dummy = DummyLearningService()
    use_case = RegisterFeedbackUseCase(dummy)

    dto = BettingFeedbackRequestDTO(
        match_id="m1",
        market_type="corners_over",
        prediction="over25",
        actual_outcome="over25",
        was_correct=True,
        odds=2.0,
        stake=10.0,
    )

    resp = use_case.execute(dto)

    assert resp.success is True
    assert resp.market_type == "corners_over"
    assert isinstance(resp.new_confidence_adjustment, float)
    assert len(dummy.registered) == 1
