from fragmax import sites


def _create_from_cbf(project):
    from worker.cbf import generate_meta_xml_files
    return list(generate_meta_xml_files(project))


def _copy_xmls_from_raw(project):
    from worker.xsdata import copy_collection_metadata_files
    from fragview.projects import project_xml_files

    xml_files = list(project_xml_files(project))
    copy_collection_metadata_files(project, xml_files)

    return xml_files


_META_SRC_FUNCS = {
    # we are using the generated XSData xml file from the 'raw' directory
    "XSDataXML": _copy_xmls_from_raw,
    # we are going to generate meta data xmls from CBF diffraction images
    "cbf": _create_from_cbf,
}


def _meta_files_setup_function():
    """
    pick meta file setup function for the configured meta data source
    """
    meta_src = sites.params().META_DATA_SOURCE

    if meta_src not in _META_SRC_FUNCS:
        raise Exception(f"Unexpectd META_DATA_SOURCE value '{meta_src}' specified")

    return _META_SRC_FUNCS[meta_src]


def create_meta_files(project):
    setup_function = _meta_files_setup_function()
    return setup_function(project)
