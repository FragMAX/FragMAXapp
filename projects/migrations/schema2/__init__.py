from pathlib import Path
from datetime import datetime
from pony.orm import Database, db_session
from projects.migrations import ProjectDesc


def _create_jobs_tables(db: Database):
    db.execute(
        """CREATE TABLE IF NOT EXISTS "JobsSet" (
          "id" INTEGER PRIMARY KEY AUTOINCREMENT,
          "description" TEXT NOT NULL
        )"""
    ).close()

    db.execute(
        """CREATE TABLE IF NOT EXISTS "Job" (
          "id" INTEGER PRIMARY KEY AUTOINCREMENT,
          "jobs_set" INTEGER NOT NULL REFERENCES "JobsSet" ("id") ON DELETE CASCADE,
          "description" TEXT NOT NULL,
          "program" TEXT NOT NULL,
          "stdout" TEXT NOT NULL,
          "stderr" TEXT NOT NULL,
          "cpus" INTEGER NOT NULL,
          "run_on" TEXT NOT NULL,
          "started" DATETIME,
          "finished" DATETIME
        )"""
    ).close()

    db.execute("""CREATE INDEX "idx_job__jobs_set" ON "Job" ("jobs_set")""").close()

    db.execute(
        """CREATE TABLE IF NOT EXISTS "JobArgument" (
          "job" INTEGER NOT NULL REFERENCES "Job" ("id") ON DELETE CASCADE,
          "index" INTEGER NOT NULL,
          "value" TEXT NOT NULL,
          PRIMARY KEY ("job", "index")
        )"""
    ).close()

    db.execute(
        """CREATE TABLE IF NOT EXISTS "Job_Job" (
          "job" INTEGER NOT NULL REFERENCES "Job" ("id") ON DELETE CASCADE,
          "job_2" INTEGER NOT NULL REFERENCES "Job" ("id") ON DELETE CASCADE,
          PRIMARY KEY ("job", "job_2")
        )"""
    ).close()

    db.execute("""CREATE INDEX "idx_job_job" ON "Job_Job" ("job_2")""").close()


def _get_finished_jobs(logs_dir: Path):
    for file in logs_dir.glob("*_out.txt"):
        stat = file.stat()

        stdout = str(file)
        stderr = f"{stdout[:-7]}err.txt"
        timestamp = str(datetime.fromtimestamp(stat.st_mtime))

        yield stdout, timestamp, stderr


def _import_old_logs(db: Database, logs_dir: Path):
    db.execute("insert into JobsSet(id, description) values(1, 'migrated')").close()

    for stdout, timestamp, stderr in _get_finished_jobs(logs_dir):
        db.execute(
            "insert into Job('jobs_set', 'description', 'program', 'stdout', 'stderr', cpus, run_on, started, finished)"
            f" values(1, 'migrated', 'unknown', '{stdout}', '{stderr}', 0, 'hpc', '{timestamp}', '{timestamp}')"
        ).close()


@db_session
def migrate(db: Database, project_desc: ProjectDesc):
    """
    migrate project database from schema ver 2 to ver 3
    """

    logs_dir = Path(project_desc.project_dir, "logs")

    _create_jobs_tables(db)
    _import_old_logs(db, logs_dir)
