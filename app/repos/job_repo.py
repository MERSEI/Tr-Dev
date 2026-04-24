import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.schemas.job import JobCreate, JobStatusUpdate


class JobRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: JobCreate) -> Job:
        job = Job(
            id=uuid.uuid4(),
            input_handle=data.input_handle,
            chat_id=data.chat_id,
            message_id=data.message_id,
            status="pending",
            created_at=datetime.utcnow(),
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get(self, job_id: uuid.UUID) -> Job | None:
        result = await self.session.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def update_status(self, job_id: uuid.UUID, update: JobStatusUpdate) -> Job | None:
        job = await self.get(job_id)
        if job is None:
            return None
        job.status = update.status
        if update.error is not None:
            job.error = update.error
        if update.finished_at is not None:
            job.finished_at = update.finished_at
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_last_for_chat(self, chat_id: int) -> Job | None:
        result = await self.session.execute(
            select(Job)
            .where(Job.chat_id == chat_id, Job.status == "done")
            .order_by(Job.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
