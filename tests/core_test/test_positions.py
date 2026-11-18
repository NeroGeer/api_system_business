# """
# Fast, pure unit tests for the ordering invariant.
# Run: pytest
# """
# from dataclasses import dataclass
# from task_workflow.enums import StageType
# from task_workflow.service import StageManagementService
# from task_workflow.errors import InvalidWorkflowStructure
#
#
# @dataclass
# class FakeStage:
#     id: int
#     stage_type: StageType
#     position: int
#
#
# def test_open_middle_end_valid():
#     stages = [
#         FakeStage(10, StageType.OPEN, 0),
#         FakeStage(11, StageType.MIDDLE, 1),
#         FakeStage(12, StageType.MIDDLE, 2),
#         FakeStage(13, StageType.END, 3),
#     ]
#     StageManagementService.validate_structure(stages)
#
#
# def test_end_must_be_last():
#     stages = [
#         FakeStage(10, StageType.OPEN, 0),
#         FakeStage(13, StageType.END, 1),
#         FakeStage(11, StageType.MIDDLE, 2),
#     ]
#     try:
#         StageManagementService.validate_structure(stages)
#     except InvalidWorkflowStructure:
#         pass
#     else:
#         raise AssertionError("Expected invalid workflow")
#
#
# def test_one_thousand_middle_stages():
#     stages = [FakeStage(1, StageType.OPEN, 0)]
#     stages.extend(
#         FakeStage(i + 2, StageType.MIDDLE, i + 1)
#         for i in range(1000)
#     )
#     stages.append(FakeStage(2000, StageType.END, 1001))
#
#     StageManagementService.validate_structure(stages)
