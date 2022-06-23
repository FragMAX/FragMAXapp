from pathlib import Path


def get_dataset_frame_image(project, dataset, frame_num: int) -> Path:
    return Path(
        project.get_dataset_raw_dir(dataset),
        f"{dataset.crystal.id}_{dataset.run}_{frame_num:04d}.cbf",
    )
