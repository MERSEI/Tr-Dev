import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis, RunLog
from app.schemas.analysis import AnalysisResult


class AnalysisRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, job_id: uuid.UUID, result: AnalysisResult) -> Analysis:
        analysis = Analysis(
            id=uuid.uuid4(),
            job_id=job_id,
            result_json=result.model_dump(mode="json"),
            created_at=datetime.utcnow(),
        )
        self.session.add(analysis)
        await self.session.commit()
        await self.session.refresh(analysis)
        return analysis

    async def get_by_job(self, job_id: uuid.UUID) -> Analysis | None:
        result = await self.session.execute(
            select(Analysis)
            .where(Analysis.job_id == job_id)
            .order_by(Analysis.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def log_stage(
        self,
        job_id: uuid.UUID,
        stage: str,
        status: str,
        message: str | None = None,
    ) -> None:
        log = RunLog(
            id=uuid.uuid4(),
            job_id=job_id,
            stage=stage,
            status=status,
            message=message,
            created_at=datetime.utcnow(),
        )
        self.session.add(log)
        await self.session.commit()
