from typing import Dict, List
from datetime import datetime
from pathlib import Path
from django.shortcuts import render, redirect, reverse
from django.http import HttpResponseBadRequest
from fragview.projects import Project
from fragview.projects import current_project
from fragview.forms import KillJobForm
from jobs import client


def _elapsed_time(start: datetime, end: datetime) -> Dict[str, int]:
    """
    calculate time elapsed from start to end time,
    returns elapsed time divided into hours, minutes and seconds
    """
    delta = end - start

    # let's use seconds precision
    seconds_delta = delta.seconds

    seconds = seconds_delta % 60
    minutes = (seconds_delta // 60) % 60
    hours = seconds_delta // 3600

    return dict(hours=hours, minutes=minutes, seconds=seconds)


def _get_jobs(project: Project) -> List[Dict]:
    def _run_time(start_time):
        if start_time is None:
            return None

        return _elapsed_time(start_time, now)

    now = datetime.now()

    #
    # convert Jobs table into a format that is more
    # convenient for presenting to the user
    #
    jobs = []
    for job in project.get_running_jobs():
        jobs.append(
            dict(
                id=job.id,
                name=job.description,
                stdout=Path(job.stdout).name,
                stderr=Path(job.stderr).name,
                run_time=_run_time(job.started),
            )
        )

    return jobs


def status(request):
    return render(
        request, "hpcstatus.html", {"jobs": _get_jobs(current_project(request))}
    )


def kill(request):
    form = KillJobForm(request.POST)

    if not form.is_valid():
        return HttpResponseBadRequest(f"{form.errors}")

    project = current_project(request)
    client.cancel_jobs(project.id, form.get_job_ids())

    return redirect(reverse("hpcstatus"))


def jobhistory(request):
    def _finished_jobs():
        for job in project.get_finished_jobs():
            stdout = Path(job.stdout).name
            stderr = Path(job.stderr).name
            yield stdout, job.finished, stdout, stderr

    project = current_project(request)
    return render(request, "jobhistory.html", {"logHistory": _finished_jobs()})
