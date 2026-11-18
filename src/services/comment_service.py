import json

from src.exceptions import exceptions as c_exp
from src.database.database import RedisKeys
from src.logger.logger import logger
from src.models.model_tasks import Task, TaskComment
from src.scheme.schemas_task import CommentCreateSchema, CommentSchema
from src.scheme.schemas_team import TeamRole


class CommentService:
    def __init__(self, repo, context=None):
        self.repo = repo
        self.ctx = context

    async def validate_task(self, task_id: int):
        task = await self.repo.validate_task_id(task_id=task_id)
        if task is None:
            raise c_exp.TaskNotFoundError()
        return task

    async def comment_stmt(
        self, team_id: int, task_id: int, comment_id: int
    ):
        """
        Retrieves a specific comment ensuring it belongs to the given task and team.

        Returns:
            TaskComment: Found comment.

        Raises:
            HTTPException: If comment is not found.
        """

        comment = await self.repo.get()
        if comment is None:
            logger.warning(
                f"Comment not found: comment_id={comment_id}, task_id={task_id}, team_id={team_id}"
            )
            raise c_exp.CommentNotFoundError()

        logger.debug(f"Comment loaded: id={comment_id}")

        return comment

    async def get_task_comments(self):
        """
        Retrieves all comments for a task with Redis caching.

        Returns:
            list[CommentSchema]: List of task comments.
        """
        user_id = self.ctx.current_user.id
        redis = self.ctx.redis
        team_id = self.ctx.scope.team_id
        task_id = self.ctx.scope.task_id

        logger.debug(
            f"Fetching comments: user_id={user_id}, task_id={task_id}, team_id={team_id}"
        )

        await self.ctx.require_admin_or_team_role_or_executor(team_role={TeamRole.manager, TeamRole.employee})

        await self.repo.validate_task(task_id=task_id)

        key = RedisKeys.TASK_COMMENTS.format(task_id=task_id)
        cached = await redis.get(key)
        if cached:
            logger.debug(f"Cache hit for task comments: task_id={task_id}")
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                logger.warning(f"Invalid cache JSON for key={key}")
                await redis.delete(key)

        comments = await self.repo.get_comments(task_id=task_id, team_id=team_id)

        data = [CommentSchema.model_validate(c).model_dump(mode="json") for c in comments]

        await redis.set(key, json.dumps(data, ensure_ascii=False), ex=300)

        logger.info(f"Comments loaded from DB: task_id={task_id}, count={len(comments)}")

        return comments

    async def add_comments(
        self,
        data: CommentCreateSchema,
    ):
        """
        Adds a new comment to a task.

        Returns:
            TaskComment: Created comment.
        """

        user_id = self.ctx.current_user.id
        redis = self.ctx.redis
        task_id = self.ctx.scope.task_id

        logger.debug(f"Adding comment: user_id={user_id}, task_id={task_id}")

        await self.ctx.require_admin_or_team_role_or_executor(check_executor=True)

        await self.repo.validate_task(task_id=task_id)

        new_comment = TaskComment(
            task_id=task_id, user_id=user_id, text=data.text
        )

        await self.repo.create(comment=new_comment)

        key = RedisKeys.TASK_COMMENTS.format(task_id=task_id)
        await redis.delete(key)

        logger.info(f"Comment created: id={new_comment.id}, task_id={task_id}")

        return new_comment

    async def update_comments(
        self,
        data: CommentCreateSchema,
    ):
        """
        Updates a comment if user is owner or has admin/team manager rights.

        Returns:
            TaskComment: Updated comment.
        """

        user_id = self.ctx.current_user.id
        redis = self.ctx.redis
        team_id = self.ctx.scope.team_id
        task_id = self.ctx.scope.task_id
        comment_id = self.ctx.scope.comment_id

        comment = await self.comment_stmt(team_id=team_id, task_id=task_id, comment_id=comment_id)

        if not user_id == comment.user_id:
            logger.debug(
                f"Non-owner update attempt: user_id={user_id}, comment_id={comment_id}"
            )
            await self.ctx.require_admin_or_team_role_or_executor()

        comment.text = data.text

        await self.repo.update(comment=comment)

        key = RedisKeys.TASK_COMMENTS.format(task_id=task_id)
        await redis.delete(key)

        logger.info(f"Comment updated: id={comment_id}")

        return comment

    async def delete_comments(self):
        """
        Deletes a comment if user is owner or has admin/team manager rights.

        Returns:
            dict: Confirmation message.
        """

        user_id = self.ctx.current_user.id
        redis = self.ctx.redis
        team_id = self.ctx.scope.team_id
        task_id = self.ctx.scope.task_id
        comment_id = self.ctx.scope.comment_id

        comment = await self.comment_stmt(team_id=team_id, task_id=task_id, comment_id=comment_id)

        if not user_id == comment.user_id:
            logger.debug(
                f"Non-owner delete attempt: user_id={user_id}, comment_id={comment_id}"
            )

            await self.ctx.require_admin_or_team_role_or_executor()

        await self.repo.delete(comment=comment)

        key = RedisKeys.TASK_COMMENTS.format(task_id=task_id)
        await redis.delete(key)
        logger.info(f"Comment deleted: id={comment_id}")

        return {"detail": "Comment deleted"}
