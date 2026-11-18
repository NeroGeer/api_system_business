# from task_workflow.schemas import TransitionReplaceRequest
#
#
# def test_api_payload_uses_from_alias():
#     payload = TransitionReplaceRequest.model_validate({
#         "transitions": [
#             {"from": 1, "to": 2},
#             {"from": 2, "to": 1},
#         ]
#     })
#     assert payload.transitions[0].from_ == 1
#     assert payload.transitions[0].to == 2
