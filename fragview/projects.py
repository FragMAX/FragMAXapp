def project_xml_files(project):
    for shift_dir in project_shift_dirs(project):
        for file in glob.glob(f"{shift_dir}**/process/{project.protein}/**/**/fastdp/cn**/"
            f"ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml"):
            yield file
