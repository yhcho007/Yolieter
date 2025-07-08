from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.jobstores.base import ConflictingIdError, JobLookupError
from apscheduler.util import maybe_ref
from sqlalchemy.dialects.oracle import FLOAT as ORACLE_FLOAT
from sqlalchemy import create_engine, MetaData, Table, Column, String, LargeBinary, select, delete, insert, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
import pickle
import logging

logger = logging.getLogger(__name__)

class OracleJobStore(SQLAlchemyJobStore):
    def __init__(self, url, tablename='apscheduler_jobs', engine=None, metadata=None, pickle_protocol=pickle.HIGHEST_PROTOCOL):
        self.pickle_protocol = pickle_protocol
        self.tablename = tablename

        self.engine = create_engine(url, pool_pre_ping=True) if engine is None else engine
        self.metadata = MetaData() if metadata is None else metadata

        # ✅ 여기에서 Oracle 호환 테이블 수동 생성
        self.jobs_table = Table(self.tablename, self.metadata,
            Column('id', String(191), primary_key=True),
            Column('next_run_time', ORACLE_FLOAT(53), index=True),  # <-- 핵심 수정
            Column('job_state', LargeBinary, nullable=False)
        )
        self.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def lookup_job(self, job_id):
        session = self.Session()
        try:
            job_state = session.execute(
                select(self.jobs_table.c.job_state).where(self.jobs_table.c.id == job_id)
            ).scalar()
            return self._reconstitute_job(job_state) if job_state else None
        finally:
            session.close()

    def get_due_jobs(self, now):
        session = self.Session()
        try:
            job_states = session.execute(
                select(self.jobs_table.c.job_state).where(self.jobs_table.c.next_run_time <= now.timestamp())
            ).scalars().all()
            return list(self._reconstitute_jobs(job_states))
        finally:
            session.close()

    def get_next_run_time(self):
        session = self.Session()
        try:
            return session.execute(
                select(self.jobs_table.c.next_run_time).order_by(self.jobs_table.c.next_run_time.asc()).limit(1)
            ).scalar()
        finally:
            session.close()

    def get_all_jobs(self):
        session = self.Session()
        try:
            job_states = session.execute(select(self.jobs_table.c.job_state)).scalars().all()
            return list(self._reconstitute_jobs(job_states))
        finally:
            session.close()

    def add_job(self, job):
        session = self.Session()
        try:
            job_state = self._serialize_job(job)
            session.execute(insert(self.jobs_table).values(id=job.id, next_run_time=job.next_run_time.timestamp() if job.next_run_time else None, job_state=job_state))
            session.commit()
        except IntegrityError:
            session.rollback()
            raise ConflictingIdError(job.id)
        finally:
            session.close()

    def update_job(self, job):
        session = self.Session()
        try:
            job_state = self._serialize_job(job)
            session.execute(
                update(self.jobs_table)
                .where(self.jobs_table.c.id == job.id)
                .values(next_run_time=job.next_run_time.timestamp() if job.next_run_time else None, job_state=job_state)
            )
            session.commit()
        finally:
            session.close()

    def remove_job(self, job_id):
        session = self.Session()
        try:
            result = session.execute(delete(self.jobs_table).where(self.jobs_table.c.id == job_id))
            if result.rowcount == 0:
                raise JobLookupError(job_id)
            session.commit()
        finally:
            session.close()

    def remove_all_jobs(self):
        session = self.Session()
        try:
            session.execute(delete(self.jobs_table))
            session.commit()
        finally:
            session.close()
