from sqladmin import ModelView
from sqladmin.filters import ForeignKeyFilter

from src.models.model_tasks import Task, TaskComment
from src.models.model_team import Team


class TaskAdmin(ModelView, model=Task):
    name = "Task"
    name_plural = "Tasks"

    column_list = [
        Task.id,
        Task.description,
        Task.title,
        Task.team_id,
        Task.executor_user_id,
        Task.stage_id,
        Task.deadline,
        Task.close_date,
    ]

    column_searchable_list = [
        Task.stage_id,
        Task.description,
    ]

    column_filters = [
        ForeignKeyFilter(Task.team_id, Team.name),
    ]


class TaskCommentAdmin(ModelView, model=TaskComment):
    name = "Task Comment"
    name_plural = "Task Comments"

    column_list = [
        TaskComment.id,
        TaskComment.user_id,
        TaskComment.task_id,
        TaskComment.text,
        TaskComment.created_at,
    ]

    column_searchable_list = [
        TaskComment.text,
    ]

    def column_format(self, model, name):
        if name == "user_id":
            return f"User {model.task_id}"

        if name == "task_id":
            return f"Task {model.task_id}"
